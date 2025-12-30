import argparse
import asyncio
import re
import subprocess
import sys
from pathlib import Path

from .agent.basic import run_review, summarize_review
from .agent.expert import run_expert_review
from .agent.tools.changed_files import FileChange, _changed_files_impl
from .config import MODEL_NAME, MODEL_PROVIDER


def get_current_branch(repo_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_repo_root(path: str | None = None) -> str:
    cmd = ["git", "rev-parse", "--show-toplevel"]
    if path:
        cmd = ["git", "-C", path, "rev-parse", "--show-toplevel"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-powered code review tool for git branches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Review Modes:
  basic   - Single comprehensive agent (faster, lower cost)
  expert  - Multiple specialized agents running in parallel (thorough, ~10x cost)
            Recommended with cheaper models (e.g., Claude Haiku) for cost balance

Expert Mode Agent Control:
  Use --no-* flags to disable specific agents in expert mode (all enabled by default)
        """,
    )
    parser.add_argument(
        "--repo-path", help="Path to git repository (default: current directory)"
    )
    parser.add_argument(
        "--target-branch",
        default="main",
        help="Target branch or commit hash to compare against (default: main)",
    )
    parser.add_argument(
        "--output",
        help="Output file path or directory (default: review_<branch_name>.md in current directory)",
    )
    parser.add_argument(
        "--instructions",
        help="Path to markdown file with additional instructions for the reviewer",
    )
    parser.add_argument(
        "--mode",
        choices=["basic", "expert"],
        default="basic",
        help="Review mode (see details below)",
    )
    parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Skip executive summary generation (faster, basic mode only)",
    )

    # Expert mode agent control flags
    expert_group = parser.add_argument_group("expert mode agent control")
    expert_group.add_argument(
        "--no-security",
        action="store_true",
        help="Disable security analysis agent (expert mode)",
    )
    expert_group.add_argument(
        "--no-code-quality",
        action="store_true",
        help="Disable code quality agent (expert mode)",
    )
    expert_group.add_argument(
        "--no-performance",
        action="store_true",
        help="Disable performance analysis agent (expert mode)",
    )
    expert_group.add_argument(
        "--no-architecture",
        action="store_true",
        help="Disable architecture review agent (expert mode)",
    )
    expert_group.add_argument(
        "--no-documentation",
        action="store_true",
        help="Disable documentation review agent (expert mode)",
    )
    expert_group.add_argument(
        "--no-error-handling",
        action="store_true",
        help="Disable error handling analysis agent (expert mode)",
    )
    expert_group.add_argument(
        "--no-business-logic",
        action="store_true",
        help="Disable business logic review agent (expert mode)",
    )
    expert_group.add_argument(
        "--no-testing",
        action="store_true",
        help="Disable testing review agent (expert mode)",
    )

    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate argument combinations and warn about misuse.

    Args:
        args: Parsed command-line arguments
    """
    # Check if --no-* flags are used without expert mode
    agent_flags = [
        args.no_security,
        args.no_code_quality,
        args.no_performance,
        args.no_architecture,
        args.no_documentation,
        args.no_error_handling,
        args.no_business_logic,
        args.no_testing,
    ]

    if any(agent_flags) and args.mode != "expert":
        print(
            "Warning: --no-* flags are only used in expert mode. They will be ignored in basic mode.",
            file=sys.stderr,
        )


def sanitize_branch_name(branch: str) -> str:
    return re.sub(r"[^\w\-.]", "_", branch)


def determine_output_file(output: str | None, branch: str) -> str:
    safe_branch_name = sanitize_branch_name(branch)
    default_filename = f"review_{safe_branch_name}.md"

    if not output:
        return default_filename

    # If output is a directory, append default filename
    output_path = Path(output)
    if output_path.is_dir():
        return str(output_path / default_filename)

    return output


def print_summary(
    repo_path: str, current_branch: str, target_branch: str, output_file: str
) -> None:
    print(f"Repository: {repo_path}")
    print(f"Current branch: {current_branch}")
    print(f"Target branch: {target_branch}")
    print(f"Output file: {output_file}")
    print()


def print_model_config(has_instructions: bool) -> None:
    print(f"Model provider: {MODEL_PROVIDER}")
    print(f"Model: {MODEL_NAME}")
    if has_instructions:
        print("Additional instructions: Yes")
    print()


def print_changed_files_summary(changed_files: list[FileChange]) -> None:
    print(f"Found {len(changed_files)} changed files:")
    for f in changed_files[:10]:
        print(f"  - {f.path} ({f.change_type})")
    if len(changed_files) > 10:
        print(f"  ... and {len(changed_files) - 10} more")
    print()


async def async_main() -> None:
    """Async main function that handles the review process."""
    args = parse_arguments()

    # Validate argument combinations
    validate_arguments(args)

    try:
        repo_path = get_repo_root(args.repo_path)
    except subprocess.CalledProcessError:
        if args.repo_path:
            print(f"Error: '{args.repo_path}' is not a git repository", file=sys.stderr)
        else:
            print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)

    try:
        current_branch = get_current_branch(repo_path)
    except subprocess.CalledProcessError as e:
        print(f"Error: Could not determine current branch: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    output_file = determine_output_file(args.output, current_branch)
    print_summary(repo_path, current_branch, args.target_branch, output_file)
    print_model_config(has_instructions=bool(args.instructions))

    try:
        changed_files = _changed_files_impl(repo_path, args.target_branch)
    except subprocess.CalledProcessError as e:
        print(f"Error: Could not get changed files: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    if not changed_files:
        print("No changes detected between current branch and target branch.")
        sys.exit(0)

    print_changed_files_summary(changed_files)

    print("Starting code review...")
    print()

    additional_instructions = None
    if args.instructions:
        try:
            additional_instructions = Path(args.instructions).read_text()
            print(f"Using instructions from: {args.instructions}")
            print()
        except Exception as e:
            print(f"Warning: Could not read instructions file: {e}", file=sys.stderr)

    # Run appropriate review mode
    if args.mode == "expert":
        # Expert mode: multiple specialized agents in parallel
        review_content, token_usage = await run_expert_review(
            repo_path,
            args.target_branch,
            changed_files,
            show_progress=True,
            additional_instructions=additional_instructions,
            no_security=args.no_security,
            no_code_quality=args.no_code_quality,
            no_performance=args.no_performance,
            no_architecture=args.no_architecture,
            no_documentation=args.no_documentation,
            no_error_handling=args.no_error_handling,
            no_business_logic=args.no_business_logic,
            no_testing=args.no_testing,
        )
        # Note: Summary agent incorporates additional instructions if provided
    else:
        # Basic mode: single comprehensive agent
        review_content, token_usage = await run_review(
            repo_path,
            args.target_branch,
            changed_files,
            mode=args.mode,
            additional_instructions=additional_instructions,
        )

        # Add executive summary if requested (basic mode only)
        if not args.skip_summary:
            review_content, summary_usage = await summarize_review(review_content)
            # Merge token usage
            if token_usage and summary_usage:
                token_usage = token_usage + summary_usage

    print()
    Path(output_file).write_text(review_content)
    print(f"✓ Review completed and saved to: {output_file}")

    if token_usage:
        print()
        token_usage.log_statistics()


def main() -> None:
    """Entry point that runs the async main function."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
