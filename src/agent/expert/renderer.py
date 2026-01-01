"""Renderer for expert mode review output.

Generates clean markdown for confirmed findings and logs statistics to console.
"""

from ..formatter import format_review_content
from ..token_usage import TokenUsage
from .schemas import ExpertReviewResult, Severity


def render_expert_review(
    result: ExpertReviewResult,
    stage1_tokens: TokenUsage | None,
    stage2_tokens: TokenUsage | None,
    show_progress: bool = True,
) -> str:
    """Render expert review result as markdown and log statistics.

    Args:
        result: Complete expert review result
        stage1_tokens: TokenUsage from Stage 1 (primary review)
        stage2_tokens: TokenUsage from Stage 2 (validation)
        show_progress: Whether to log statistics to console

    Returns:
        Formatted markdown content (confirmed findings only)
    """
    # Build markdown content
    lines = []

    # Title
    lines.append(f"# Code Review: {result.summary.changes_title}")
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(result.summary.changes_description)
    lines.append("")

    # Findings section
    lines.append("## Findings")
    lines.append("")

    # Group confirmed findings by severity
    severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
    severity_labels = {
        Severity.CRITICAL: "Critical Issues",
        Severity.HIGH: "High Severity Issues",
        Severity.MEDIUM: "Medium Severity Issues",
        Severity.LOW: "Low Severity Issues",
    }

    has_findings = False
    for severity in severity_order:
        findings = result.confirmed_by_severity(severity)
        if not findings:
            continue

        has_findings = True
        count = len(findings)
        label = severity_labels[severity]

        lines.append(f"### {label} ({count} confirmed)")
        lines.append("")

        for finding in findings:
            lines.append(f"**{finding.title}**")
            lines.append("")

            # Locations
            if finding.location:
                if len(finding.location) == 1:
                    lines.append(f"- **Location**: {finding.location[0].format()}")
                else:
                    lines.append("- **Locations**:")
                    for loc in finding.location:
                        lines.append(f"  - {loc.format()}")
                lines.append("")

            # Description
            lines.append(f"- **Description**: {finding.description}")
            lines.append("")

            # Recommendation
            lines.append(f"- **Recommendation**: {finding.recommendation}")
            lines.append("")

    if not has_findings:
        lines.append("No confirmed issues found.")
        lines.append("")

    markdown_content = "\n".join(lines)

    # Format the markdown content
    markdown_content = format_review_content(markdown_content)

    # Log statistics to console (after markdown generation, per plan)
    if show_progress:
        _log_statistics_to_console(result, stage1_tokens, stage2_tokens)

    return markdown_content


def _log_statistics_to_console(
    result: ExpertReviewResult,
    stage1_tokens: TokenUsage | None,
    stage2_tokens: TokenUsage | None,
) -> None:
    """Log review statistics and filtered findings to console.

    Args:
        result: Complete expert review result
        stage1_tokens: TokenUsage from Stage 1
        stage2_tokens: TokenUsage from Stage 2
    """
    print()
    print("=" * 60)
    print("REVIEW STATISTICS")
    print("=" * 60)
    print()

    # Statistics
    print(f"Total findings identified: {result.total_findings}")
    print(
        f"Findings confirmed: {result.confirmed_findings} ({result.confirmation_rate:.1f}%)"
    )
    print(f"Findings filtered: {result.filtered_findings}")
    print()

    # Token Usage
    if stage1_tokens or stage2_tokens:
        print("TOKEN USAGE")
        print("-" * 60)

        if stage1_tokens:
            print(
                f"Stage 1 (Primary Review):  {stage1_tokens.input_tokens:>7,} input  "
                f"{stage1_tokens.output_tokens:>7,} output  "
                f"{stage1_tokens.total_tokens:>7,} total"
            )

        if stage2_tokens:
            print(
                f"Stage 2 (Validation):      {stage2_tokens.input_tokens:>7,} input  "
                f"{stage2_tokens.output_tokens:>7,} output  "
                f"{stage2_tokens.total_tokens:>7,} total"
            )

        if stage1_tokens and stage2_tokens:
            total = stage1_tokens + stage2_tokens
            print(
                f"Total:                     {total.input_tokens:>7,} input  "
                f"{total.output_tokens:>7,} output  "
                f"{total.total_tokens:>7,} total"
            )
        print()

    # Filtered Findings
    filtered = result.get_filtered_findings()
    if filtered:
        print("FILTERED FINDINGS")
        print("-" * 60)
        print()
        for finding in filtered:
            print(f"- **{finding.title}**")
            print(f"  Reason: {finding.validation_reason}")
            print()
    else:
        print("No findings were filtered.")
        print()

    print("=" * 60)
