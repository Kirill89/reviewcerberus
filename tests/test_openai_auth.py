import json
from pathlib import Path
from typing import Any

import pytest

from src.agent.providers import openai as auth


@pytest.fixture(autouse=True)
def isolate_auth(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.delenv("OPENAI_AUTH_FILE", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))


def test_path_precedence(tmp_path: Path, monkeypatch: Any) -> None:
    assert auth.credential_path() == tmp_path / "auth.json"
    monkeypatch.setenv("OPENAI_AUTH_FILE", "/.codex/auth.json")
    assert auth.credential_path() == Path("/.codex/auth.json")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("OPENAI_AUTH_FILE", "~/custom.json")
    assert auth.credential_path() == tmp_path / "home/custom.json"
    monkeypatch.delenv("OPENAI_AUTH_FILE")
    monkeypatch.delenv("CODEX_HOME")
    assert auth.credential_path() == tmp_path / "home/.codex/auth.json"


def test_read_only_codex_file(tmp_path: Path) -> None:
    path = auth.credential_path()
    path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "OPENAI_API_KEY": None,
                "tokens": {
                    "access_token": "secret",
                    "refresh_token": "refresh",
                    "account_id": "account",
                },
                "last_refresh": "2026-11-15T00:00:00Z",
            }
        )
    )
    path.chmod(0o400)
    before = path.read_bytes()
    credentials = auth.load_credentials()
    assert credentials.access_token == "secret"
    assert credentials.account_id == "account"
    assert "secret" not in repr(credentials)
    auth.load_credentials()
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "contents",
    [
        "not JSON secret",
        "[]",
        "null",
        "{}",
        '{"tokens": null}',
        '{"tokens": {"access_token": 123}}',
        '{"tokens": {"access_token": ""}}',
        '{"tokens": {"access_token": "secret", "account_id": []}}',
        '{"auth_mode": "apikey", "OPENAI_API_KEY": "secret"}',
    ],
)
def test_invalid_credentials_fail_without_exposing_secrets(contents: str) -> None:
    auth.credential_path().write_text(contents)
    with pytest.raises(ValueError) as error:
        auth.load_credentials()
    assert "secret" not in str(error.value)


def test_missing_file_never_starts_browser() -> None:
    with pytest.raises(ValueError, match="Sign in with Codex on the host"):
        auth.load_credentials()


def test_permission_error_is_actionable(monkeypatch: Any) -> None:
    def denied(*args: Any, **kwargs: Any) -> str:
        raise PermissionError("private contents")

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(ValueError, match="Cannot read Codex credentials") as error:
        auth.load_credentials()
    assert "private contents" not in str(error.value)
