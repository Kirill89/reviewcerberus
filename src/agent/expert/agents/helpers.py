"""Helper functions for agent operations."""

from ..schemas import SpecializedAgentOutput


def add_ids_to_findings(
    agent_outputs: dict[str, SpecializedAgentOutput],
) -> dict[str, dict]:
    """Add unique IDs to all issues and notes in agent outputs.

    Args:
        agent_outputs: Dictionary of agent findings without IDs

    Returns:
        Dictionary with same structure but all issues and notes have unique IDs assigned
    """
    findings_with_ids = {}
    for agent_name, output in agent_outputs.items():
        output_dict = output.model_dump()

        # Add IDs to issues
        for idx, issue in enumerate(output_dict.get("issues", [])):
            issue["id"] = f"{agent_name}_issue_{idx}"

        # Add IDs to notes
        for idx, note in enumerate(output_dict.get("notes", [])):
            note["id"] = f"{agent_name}_note_{idx}"

        findings_with_ids[agent_name] = output_dict

    return findings_with_ids


def strip_confidence_scores(findings_with_ids: dict[str, dict]) -> dict[str, dict]:
    """Remove confidence scores from findings to avoid biasing verification.

    Args:
        findings_with_ids: Dictionary of agent findings with IDs

    Returns:
        Dictionary with same structure but confidence_score fields removed from all issues
    """
    stripped = {}
    for agent_name, findings_dict in findings_with_ids.items():
        # Deep copy to avoid modifying the original
        findings_copy = {
            "issues": [issue.copy() for issue in findings_dict.get("issues", [])],
            "notes": findings_dict.get("notes", []).copy(),
        }

        # Remove confidence_score from each issue
        for issue in findings_copy["issues"]:
            issue.pop("confidence_score", None)

        stripped[agent_name] = findings_copy

    return stripped


def filter_findings_by_ids(
    findings_with_ids: dict[str, dict],
    accepted_issue_ids: list[str],
    accepted_note_ids: list[str],
) -> dict[str, SpecializedAgentOutput]:
    """Filter findings to only include accepted IDs.

    Args:
        findings_with_ids: Dictionary of agent findings with IDs
        accepted_issue_ids: List of issue IDs that passed verification
        accepted_note_ids: List of note IDs that passed verification

    Returns:
        Dictionary mapping agent names to SpecializedAgentOutput with only accepted findings
    """
    accepted_issue_ids_set = set(accepted_issue_ids)
    accepted_note_ids_set = set(accepted_note_ids)

    filtered_outputs = {}
    for agent_name, findings_dict in findings_with_ids.items():
        # Filter issues
        filtered_issues = [
            issue
            for issue in findings_dict.get("issues", [])
            if issue.get("id") in accepted_issue_ids_set
        ]

        # Filter notes
        filtered_notes = [
            note
            for note in findings_dict.get("notes", [])
            if note.get("id") in accepted_note_ids_set
        ]

        # Create SpecializedAgentOutput from filtered data
        filtered_outputs[agent_name] = SpecializedAgentOutput(
            issues=filtered_issues, notes=filtered_notes
        )

    return filtered_outputs
