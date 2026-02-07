"""Tests for SAST scanner."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.agent.sast.scanner import _trim_findings, run_sast_scan

# Sample opengrep JSON output (realistic structure)
SAMPLE_OPENGREP_OUTPUT = {
    "version": "1.16.0",
    "results": [
        {
            "check_id": "python.lang.security.audit.eval-detected.eval-detected",
            "path": "vuln.py",
            "start": {"line": 5, "col": 1, "offset": 50},
            "end": {"line": 5, "col": 20, "offset": 70},
            "extra": {
                "message": "Detected the use of eval(). This can be dangerous.",
                "severity": "WARNING",
                "lines": "eval(user_input)",
                "metadata": {"cwe": ["CWE-95"]},
                "fingerprint": "abc123",
                "metavars": {},
                "is_ignored": False,
                "validation_state": "NO_VALIDATOR",
                "engine_kind": "OSS",
            },
        },
        {
            "check_id": "python.lang.security.audit.subprocess-shell-true",
            "path": "app.py",
            "start": {"line": 12, "col": 1, "offset": 200},
            "end": {"line": 12, "col": 40, "offset": 240},
            "extra": {
                "message": "subprocess call with shell=True identified.",
                "severity": "ERROR",
                "lines": "subprocess.call(cmd, shell=True)",
                "metadata": {"cwe": ["CWE-78"]},
                "fingerprint": "def456",
                "metavars": {},
                "is_ignored": False,
                "validation_state": "NO_VALIDATOR",
                "engine_kind": "OSS",
            },
        },
    ],
    "errors": [],
    "paths": {"scanned": ["vuln.py", "app.py"]},
    "interfile_languages_used": [],
    "skipped_rules": [],
}


def test_trim_findings_keeps_relevant_fields() -> None:
    """Test that trimming keeps only the fields the LLM needs."""
    raw = json.dumps(SAMPLE_OPENGREP_OUTPUT)
    trimmed_json, count = _trim_findings(raw)

    assert count == 2
    findings = json.loads(trimmed_json)
    assert len(findings) == 2

    # Check first finding has correct fields
    f = findings[0]
    assert f["check_id"] == "python.lang.security.audit.eval-detected.eval-detected"
    assert f["path"] == "vuln.py"
    assert f["start_line"] == 5
    assert f["end_line"] == 5
    assert "eval()" in f["message"]
    assert f["severity"] == "WARNING"
    assert f["lines"] == "eval(user_input)"

    # Check dropped fields are not present
    assert "metadata" not in f
    assert "fingerprint" not in f
    assert "metavars" not in f
    assert "is_ignored" not in f
    assert "validation_state" not in f
    assert "engine_kind" not in f


def test_trim_findings_drops_top_level_fields() -> None:
    """Test that top-level fields like version, errors, paths are dropped."""
    raw = json.dumps(SAMPLE_OPENGREP_OUTPUT)
    trimmed_json, _ = _trim_findings(raw)

    # The output is a list, not a dict with version/errors/paths
    findings = json.loads(trimmed_json)
    assert isinstance(findings, list)


def test_trim_findings_empty_results() -> None:
    """Test trimming with no findings."""
    raw = json.dumps({"results": [], "version": "1.16.0"})
    trimmed_json, count = _trim_findings(raw)

    assert count == 0
    assert json.loads(trimmed_json) == []


def test_run_sast_scan_with_findings() -> None:
    """Test run_sast_scan returns trimmed findings."""
    mock_result = MagicMock()
    mock_result.stdout = json.dumps(SAMPLE_OPENGREP_OUTPUT)

    with patch(
        "src.agent.sast.scanner.ensure_opengrep_binary",
        return_value="/usr/local/bin/opengrep",
    ), patch("src.agent.sast.scanner.subprocess.run", return_value=mock_result):
        result = run_sast_scan("/test/repo", "main")

    assert result is not None
    assert result.count == 2
    findings = json.loads(result.findings)
    assert len(findings) == 2


def test_run_sast_scan_no_findings() -> None:
    """Test run_sast_scan returns None when no findings."""
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({"results": []})

    with patch(
        "src.agent.sast.scanner.ensure_opengrep_binary",
        return_value="/usr/local/bin/opengrep",
    ), patch("src.agent.sast.scanner.subprocess.run", return_value=mock_result):
        result = run_sast_scan("/test/repo", "main")

    assert result is None


def test_run_sast_scan_error() -> None:
    """Test run_sast_scan wraps subprocess errors with stderr."""
    err = subprocess.CalledProcessError(2, "opengrep")
    err.stderr = "invalid config"

    with patch(
        "src.agent.sast.scanner.ensure_opengrep_binary",
        return_value="/usr/local/bin/opengrep",
    ), patch(
        "src.agent.sast.scanner.subprocess.run",
        side_effect=err,
    ), pytest.raises(
        RuntimeError, match="OpenGrep scan failed.*invalid config"
    ):
        run_sast_scan("/test/repo", "main")


def test_run_sast_scan_passes_correct_args() -> None:
    """Test that run_sast_scan passes correct arguments to subprocess."""
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({"results": []})

    with patch(
        "src.agent.sast.scanner.ensure_opengrep_binary",
        return_value="/usr/bin/opengrep",
    ), patch(
        "src.agent.sast.scanner.subprocess.run", return_value=mock_result
    ) as mock_run:
        run_sast_scan("/my/repo", "develop")

    mock_run.assert_called_once_with(
        [
            "/usr/bin/opengrep",
            "scan",
            "--config",
            "auto",
            "--json",
            "--baseline-commit",
            "develop",
            ".",
        ],
        cwd="/my/repo",
        capture_output=True,
        text=True,
        check=True,
    )
