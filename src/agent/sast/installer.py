"""OpenGrep binary installer with platform detection and caching."""

import os
import platform
import stat
import urllib.request
from pathlib import Path

OPENGREP_VERSION = "1.16.0"

PLATFORM_BINARIES = {
    ("Linux", "x86_64"): "opengrep_manylinux_x86",
    ("Linux", "aarch64"): "opengrep_manylinux_aarch64",
    ("Darwin", "x86_64"): "opengrep_osx_x86",
    ("Darwin", "arm64"): "opengrep_osx_arm64",
}


def _get_binary_name() -> str:
    """Get the platform-specific binary name."""
    key = (platform.system(), platform.machine())
    binary_name = PLATFORM_BINARIES.get(key)
    if not binary_name:
        raise RuntimeError(
            f"Unsupported platform: {key[0]} {key[1]}. "
            f"Supported: {', '.join(f'{s} {m}' for s, m in PLATFORM_BINARIES)}"
        )
    return binary_name


def _get_cache_path() -> Path:
    """Get the cache path for the opengrep binary."""
    return (
        Path.home()
        / ".cache"
        / "reviewcerberus"
        / f"opengrep-v{OPENGREP_VERSION}"
        / "opengrep"
    )


def _download_binary(cache_path: Path) -> None:
    """Download the opengrep binary from GitHub releases."""
    binary_name = _get_binary_name()
    url = (
        f"https://github.com/opengrep/opengrep/releases/download/"
        f"v{OPENGREP_VERSION}/{binary_name}"
    )

    print(f"Downloading opengrep v{OPENGREP_VERSION} ({binary_name})...")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, cache_path)
    cache_path.chmod(cache_path.stat().st_mode | stat.S_IEXEC)

    print(f"Cached at: {cache_path}")


def ensure_opengrep_binary() -> str:
    """Ensure the opengrep binary is available and return its path.

    Lookup order:
    1. OPENGREP_BINARY_PATH env var (manual override)
    2. Cached binary at ~/.cache/reviewcerberus/opengrep-v{VERSION}/opengrep
    3. Download from GitHub releases

    Returns:
        Path to the opengrep binary
    """
    # 1. Environment variable override
    env_path = os.environ.get("OPENGREP_BINARY_PATH")
    if env_path:
        if not Path(env_path).is_file():
            raise RuntimeError(
                f"OPENGREP_BINARY_PATH set to '{env_path}' but file does not exist"
            )
        return env_path

    # 2. Cached binary (version-pinned)
    cache_path = _get_cache_path()
    if cache_path.is_file():
        return str(cache_path)

    # 3. Download
    _download_binary(cache_path)
    return str(cache_path)


if __name__ == "__main__":
    path = ensure_opengrep_binary()
    print(f"OpenGrep binary: {path}")
