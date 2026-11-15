"""OpenAI models using an API key or a read-only Codex login."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import ChatGeneration, LLMResult
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.codex import _ChatOpenAICodex

from ...config import OPENAI_API_KEY


def credential_path() -> Path:
    """An explicit file wins over CODEX_HOME and the usual ~/.codex location."""
    override = os.environ.get("OPENAI_AUTH_FILE")
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser() / "auth.json"


@dataclass(frozen=True)
class CodexCredentials:
    access_token: str = field(repr=False)
    account_id: str | None = None


def load_credentials() -> CodexCredentials:
    """Reload on every request so host-side credential updates take effect."""
    path = credential_path()
    help_text = "Sign in with Codex on the host and mount its auth.json read-only."
    try:
        saved = json.loads(path.read_text())
    except OSError:
        raise ValueError(
            f"Cannot read Codex credentials at {path}. {help_text}"
        ) from None
    except ValueError:
        raise ValueError(f"Invalid Codex auth.json at {path}. {help_text}") from None
    if not isinstance(saved, dict):
        raise ValueError(f"Invalid Codex auth.json at {path}. {help_text}")
    if saved.get("auth_mode") not in (None, "chatgpt", "chatgptAuthTokens"):
        raise ValueError(
            "Codex auth.json must contain a ChatGPT login. "
            "For API billing, set OPENAI_API_KEY instead."
        )
    tokens = saved.get("tokens")
    if not isinstance(tokens, dict):
        raise ValueError(f"No ChatGPT tokens in {path}. {help_text}")
    token = tokens.get("access_token")
    if (
        not isinstance(token, str)
        or not token
        or any(not 33 <= ord(char) <= 126 for char in token)
    ):
        raise ValueError(f"No ChatGPT access token in {path}. {help_text}")
    account_id = tokens.get("account_id")
    if account_id is not None and (
        not isinstance(account_id, str)
        or not account_id
        or any(not 33 <= ord(char) <= 126 for char in account_id)
    ):
        raise ValueError(f"Invalid ChatGPT account ID in {path}. {help_text}")
    return CodexCredentials(token, account_id)


class CodexTokenProvider:
    """Read-only token source for LangChain's Codex integration."""

    def get_token(self) -> CodexCredentials:
        return load_credentials()

    async def aget_token(self) -> CodexCredentials:
        return await asyncio.to_thread(self.get_token)

    def get_access_token(self) -> str:
        return self.get_token().access_token

    async def aget_access_token(self) -> str:
        return (await self.aget_token()).access_token


class RequireCompleteResponse(BaseCallbackHandler):
    """Do not let a truncated response become a successful review."""

    raise_error = True

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for generations in response.generations:
            for generation in generations:
                if not isinstance(generation, ChatGeneration) or (
                    generation.message.response_metadata.get("status") != "completed"
                ):
                    raise ValueError("OpenAI stream did not complete")


def create_openai_model(model_name: str, max_tokens: int) -> ChatOpenAI:
    options: dict[str, Any] = {
        "model": model_name,
        "use_responses_api": True,
        "use_previous_response_id": False,
        "output_version": "responses/v1",
        "streaming": True,
        "store": False,
        "include": ["reasoning.encrypted_content"],
        "timeout": 180.0,
        "callbacks": [RequireCompleteResponse()],
    }
    if OPENAI_API_KEY.get_secret_value():
        return ChatOpenAI(
            api_key=OPENAI_API_KEY,
            max_completion_tokens=max_tokens,
            **options,
        )
    return _ChatOpenAICodex(
        token_provider=CodexTokenProvider(),
        **options,
    )
