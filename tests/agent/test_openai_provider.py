import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import SecretStr

from src.agent.providers import openai as provider
from src.agent.schema import PrimaryReviewOutput
from tests.test_helper import create_test_repo

pytestmark = pytest.mark.filterwarnings(
    "error:Pydantic serializer warnings:UserWarning"
)


@pytest.fixture(autouse=True)
def codex_file(tmp_path: Any, monkeypatch: Any) -> None:
    path = tmp_path / "auth.json"
    path.write_text(
        json.dumps({"tokens": {"access_token": "test-token", "account_id": "account"}})
    )
    monkeypatch.setenv("OPENAI_AUTH_FILE", str(path))


def event(kind: str, **data: Any) -> str:
    return f"event: {kind}\ndata: {json.dumps({'type': kind, **data})}\n\n"


def stream_response(output: dict[str, Any], status: str = "completed") -> str:
    response = {
        "id": "resp_test",
        "created_at": 1,
        "object": "response",
        "model": "gpt-6-astra",
        "status": status,
        "output": [output],
        "error": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    result = event(
        "response.created", response={**response, "output": [], "status": "in_progress"}
    )
    if output["type"] == "function_call":
        result += event(
            "response.output_item.added",
            output_index=0,
            item={**output, "arguments": ""},
        )
        result += event(
            "response.function_call_arguments.delta",
            output_index=0,
            item_id=output["id"],
            delta=output["arguments"],
        )
    else:
        result += event(
            "response.output_text.delta",
            output_index=0,
            content_index=0,
            item_id=output["id"],
            delta=output["content"][0]["text"],
        )
    if status == "disconnected":
        return result  # EOF after a delta, without a terminal response event.
    return result + event(f"response.{status}", response=response)


def tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function_call",
        "id": "fc_test",
        "call_id": "call_test",
        "name": name,
        "arguments": json.dumps(arguments),
    }


def model_with_transport(
    handler: Callable[[httpx.Request], httpx.Response],
    monkeypatch: pytest.MonkeyPatch,
    api_key: bool = False,
) -> provider.ChatOpenAI:
    monkeypatch.setattr(
        provider, "OPENAI_API_KEY", SecretStr("api-key" if api_key else "")
    )
    monkeypatch.setattr(
        httpx.HTTPTransport, "handle_request", lambda self, request: handler(request)
    )

    async def async_handle(self: Any, request: httpx.Request) -> httpx.Response:
        return handler(request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_handle)
    return provider.create_openai_model("gpt-6-astra", 100)


def test_review_tool_round_trip_and_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.agent.agent import create_review_agent

    requests: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/backend-api/codex/responses"
        assert request.headers["authorization"] == "Bearer test-token"
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["model"] == "gpt-6-astra"
        assert payload["stream"] is True and payload["store"] is False
        assert (
            "max_output_tokens" not in payload and "previous_response_id" not in payload
        )
        assert payload["instructions"]
        assert all(item.get("role") != "system" for item in payload["input"])
        names = [tool["name"] for tool in payload["tools"]]
        if len(requests) == 1:
            assert "list_files" in names
            output = tool_call("list_files", {"directory": "."})
        else:
            tool_result = next(
                item
                for item in payload["input"]
                if item.get("type") == "function_call_output"
            )
            assert "file1.py" in tool_result["output"]
            assert "Error" not in tool_result["output"]
            assert any(
                item.get("type") == "function_call_output" for item in payload["input"]
            )
            output = tool_call(
                "PrimaryReviewOutput", {"description": "Reviewed", "issues": []}
            )
        return httpx.Response(
            200,
            text=stream_response(output),
            headers={"content-type": "text/event-stream"},
        )

    model = model_with_transport(handle, monkeypatch)
    with create_test_repo() as repo, patch("src.agent.agent.model", model):
        agent, _ = create_review_agent(str(repo))
        result = agent.invoke(
            {"messages": [HumanMessage(content="Review this diff")]},
            config={"configurable": {"thread_id": "openai-test"}},
        )
    assert result["structured_response"] == PrimaryReviewOutput(
        description="Reviewed", issues=[]
    )
    assert len(requests) == 2


@pytest.mark.parametrize("status", ["failed", "incomplete", "disconnected"])
@pytest.mark.parametrize("api_key", [False, True])
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_partial_stream_is_not_a_success(
    status: str, asynchronous: bool, api_key: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = {
        "type": "message",
        "id": "msg_test",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": "partial", "annotations": []}],
    }
    body = stream_response(output, status)
    model = model_with_transport(
        lambda _: httpx.Response(
            200, text=body, headers={"content-type": "text/event-stream"}
        ),
        monkeypatch,
        api_key=api_key,
    )
    with pytest.raises(ValueError, match="incomplete|did not complete"):
        if asynchronous:
            await model.ainvoke("review")
        else:
            model.invoke("review")


def test_tool_choice_and_full_history(monkeypatch: pytest.MonkeyPatch) -> None:
    model = model_with_transport(lambda _: httpx.Response(500), monkeypatch)
    payload = model._get_request_payload(
        [
            SystemMessage(content="review"),
            HumanMessage(content="diff"),
            AIMessage(
                content="", tool_calls=[{"name": "read", "args": {}, "id": "call_1"}]
            ),
            ToolMessage(content="code", tool_call_id="call_1"),
        ],
        tools=[
            {
                "type": "function",
                "function": {"name": "read", "parameters": {"type": "object"}},
            }
        ],
        tool_choice={"type": "function", "function": {"name": "read"}},
    )
    assert payload["tool_choice"] == {
        "type": "function",
        "name": "read",
    }
    assert payload["instructions"] == "review"
    assert len(payload["input"]) == 3


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_mounted_codex_file_authenticates_requests(
    tmp_path: Any, monkeypatch: Any, asynchronous: bool
) -> None:
    path = tmp_path / "auth.json"
    monkeypatch.setenv("OPENAI_AUTH_FILE", str(path))
    monkeypatch.setattr(provider, "OPENAI_API_KEY", SecretStr(""))
    model = provider.create_openai_model("gpt-6-astra", 100)
    seen = []

    def handle(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://chatgpt.com/backend-api/codex/responses"
        seen.append(
            (request.headers["authorization"], request.headers["chatgpt-account-id"])
        )
        body = json.loads(request.content)
        assert body["instructions"]
        assert "extra_headers" not in body
        output = {
            "type": "message",
            "id": "msg_test",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "reviewed", "annotations": []}],
        }
        return httpx.Response(
            200,
            text=stream_response(output),
            headers={"content-type": "text/event-stream"},
        )

    monkeypatch.setattr(
        httpx.HTTPTransport, "handle_request", lambda self, request: handle(request)
    )

    async def async_handle(self: Any, request: httpx.Request) -> httpx.Response:
        return handle(request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_handle)
    for token, account in [("first", "account-1"), ("renewed", "account-2")]:
        path.write_text(
            json.dumps({"tokens": {"access_token": token, "account_id": account}})
        )
        if asynchronous:
            await model.ainvoke("review")
        else:
            model.invoke("review")
    assert seen == [("Bearer first", "account-1"), ("Bearer renewed", "account-2")]


def test_api_key_bypasses_missing_codex_file(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("OPENAI_AUTH_FILE", str(tmp_path / "missing.json"))
    monkeypatch.setattr(provider, "OPENAI_API_KEY", SecretStr("api-key"))
    model = provider.create_openai_model("gpt-6-astra", 100)
    assert str(model.root_client.base_url) == "https://api.openai.com/v1/"
    assert type(model) is provider.ChatOpenAI
    assert (
        model._get_request_payload([HumanMessage(content="review")])[
            "max_output_tokens"
        ]
        == 100
    )

    def handle(self: Any, request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["authorization"] == "Bearer api-key"
        assert "chatgpt-account-id" not in request.headers
        assert json.loads(request.content)["max_output_tokens"] == 100
        output = {
            "type": "message",
            "id": "msg_test",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "reviewed", "annotations": []}],
        }
        return httpx.Response(
            200,
            text=stream_response(output),
            headers={"content-type": "text/event-stream"},
        )

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    assert model.invoke("review").response_metadata["status"] == "completed"

    from src.agent.verification import agent

    monkeypatch.setattr(agent, "MODEL_PROVIDER", "openai")
    assert isinstance(agent.get_verification_model(), provider.ChatOpenAI)


@pytest.mark.parametrize("api_key", [False, True])
@pytest.mark.parametrize(
    "status", ["completed", "failed", "incomplete", "disconnected"]
)
def test_cli_only_writes_completed_reviews(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api_key: bool, status: str
) -> None:
    from src import main as cli
    from src.agent import agent

    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["authorization"] == (
            "Bearer api-key" if api_key else "Bearer test-token"
        )
        return httpx.Response(
            200,
            text=stream_response(
                tool_call(
                    "PrimaryReviewOutput", {"description": "Reviewed", "issues": []}
                ),
                status,
            ),
            headers={"content-type": "text/event-stream"},
        )

    model = model_with_transport(handle, monkeypatch, api_key=api_key)
    monkeypatch.setattr(agent, "model", model)
    monkeypatch.setattr(cli, "MODEL_PROVIDER", "openai")
    monkeypatch.setattr(cli, "OPENAI_API_KEY", provider.OPENAI_API_KEY)
    if api_key:
        # Explicit keys must work even when the mounted file is absent.
        monkeypatch.setenv("OPENAI_AUTH_FILE", str(tmp_path / "missing.json"))
    else:
        provider.credential_path().chmod(0o400)
    report = tmp_path / "review.json"
    with create_test_repo() as repo:
        monkeypatch.setattr(
            "sys.argv",
            [
                "reviewcerberus",
                "--repo-path",
                str(repo),
                "--target-branch",
                "main",
                "--json",
                "--output",
                str(report),
            ],
        )
        if status == "completed":
            cli.main()
            assert json.loads(report.read_text()) == {
                "description": "Reviewed",
                "issues": [],
            }
        else:
            with pytest.raises(ValueError, match="incomplete|did not complete"):
                cli.main()
            assert not report.exists()
    assert len(requests) == 1
