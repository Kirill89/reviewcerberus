"""Tests for SAST installer."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.agent.sast.installer import (
    OPENGREP_VERSION,
    _get_binary_name,
    _get_cache_path,
    ensure_opengrep_binary,
)


def test_get_binary_name_linux_x86() -> None:
    with patch("src.agent.sast.installer.platform.system", return_value="Linux"), patch(
        "src.agent.sast.installer.platform.machine", return_value="x86_64"
    ):
        assert _get_binary_name() == "opengrep_manylinux_x86"


def test_get_binary_name_linux_aarch64() -> None:
    with patch("src.agent.sast.installer.platform.system", return_value="Linux"), patch(
        "src.agent.sast.installer.platform.machine", return_value="aarch64"
    ):
        assert _get_binary_name() == "opengrep_manylinux_aarch64"


def test_get_binary_name_macos_arm64() -> None:
    with patch(
        "src.agent.sast.installer.platform.system", return_value="Darwin"
    ), patch("src.agent.sast.installer.platform.machine", return_value="arm64"):
        assert _get_binary_name() == "opengrep_osx_arm64"


def test_get_binary_name_macos_x86() -> None:
    with patch(
        "src.agent.sast.installer.platform.system", return_value="Darwin"
    ), patch("src.agent.sast.installer.platform.machine", return_value="x86_64"):
        assert _get_binary_name() == "opengrep_osx_x86"


def test_get_binary_name_unsupported() -> None:
    with patch(
        "src.agent.sast.installer.platform.system", return_value="Windows"
    ), patch(
        "src.agent.sast.installer.platform.machine", return_value="AMD64"
    ), pytest.raises(
        RuntimeError, match="Unsupported platform"
    ):
        _get_binary_name()


def test_get_cache_path() -> None:
    path = _get_cache_path()
    assert f"opengrep-v{OPENGREP_VERSION}" in str(path)
    assert str(path).endswith("/opengrep")


def test_ensure_env_var_override(tmp_path: Path) -> None:
    """Test that OPENGREP_BINARY_PATH env var takes priority."""
    binary = tmp_path / "opengrep"
    binary.touch()

    with patch.dict("os.environ", {"OPENGREP_BINARY_PATH": str(binary)}):
        result = ensure_opengrep_binary()
        assert result == str(binary)


def test_ensure_env_var_missing_file() -> None:
    """Test that missing OPENGREP_BINARY_PATH file raises error."""
    with patch.dict(
        "os.environ", {"OPENGREP_BINARY_PATH": "/nonexistent/opengrep"}
    ), pytest.raises(RuntimeError, match="does not exist"):
        ensure_opengrep_binary()


def test_ensure_cached_binary(tmp_path: Path) -> None:
    """Test that cached binary is found."""
    cached = tmp_path / "opengrep"
    cached.touch()

    with patch.dict("os.environ", {}, clear=False), patch(
        "src.agent.sast.installer.os.environ.get", return_value=None
    ), patch("src.agent.sast.installer._get_cache_path", return_value=cached):
        result = ensure_opengrep_binary()
        assert result == str(cached)
