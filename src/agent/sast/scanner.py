"""OpenGrep SAST scanner — runs opengrep and trims output for LLM consumption."""

import json
import subprocess
from typing import Any

from .installer import ensure_opengrep_binary


def _trim_findings(raw_json: str) -> tuple[str, int]:
    """Trim opengrep JSON output to only fields the LLM needs.

    Args:
        raw_json: Raw JSON string from opengrep

    Returns:
        Tuple of (trimmed JSON string, finding count)
    """
    data = json.loads(raw_json)
    results = data.get("results", [])

    trimmed: list[dict[str, Any]] = []
    for r in results:
        finding: dict[str, Any] = {
            "check_id": r.get("check_id"),
            "path": r.get("path"),
            "start_line": r.get("start", {}).get("line"),
            "end_line": r.get("end", {}).get("line"),
            "message": r.get("extra", {}).get("message"),
            "severity": r.get("extra", {}).get("severity"),
            "lines": r.get("extra", {}).get("lines"),
        }
        trimmed.append(finding)

    return json.dumps(trimmed, indent=2), len(trimmed)


def run_sast_scan(repo_path: str, target_branch: str) -> str | None:
    """Run OpenGrep SAST scan and return trimmed findings for LLM consumption.

    Args:
        repo_path: Path to the git repository
        target_branch: Target branch for baseline comparison

    Returns:
        Trimmed JSON string of findings, or None if no findings
    """
    binary = ensure_opengrep_binary()

    result = subprocess.run(
        [
            binary,
            "scan",
            "--config",
            "auto",
            "--json",
            "--baseline-commit",
            target_branch,
            ".",
        ],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    trimmed_json, count = _trim_findings(result.stdout)

    if count == 0:
        return None

    return trimmed_json
