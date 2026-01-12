import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from .agent.formatting import format_review_content, render_structured_output
from .agent.git_utils import (
    FileChange,
    get_changed_files,
    get_current_branch,
    get_repo_root,
)
from .agent.runner import run_review
from .agent.schema import PrimaryReviewOutput
from .agent.verification import VerifiedReviewOutput, run_verification
from .config import MODEL_NAME, MODEL_PROVIDER


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-powered code review tool for git branches"
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
        "--verify",
        action="store_true",
        help="[Experimental] Enable Chain of Verification (CoVe) to reduce false positives",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output review as JSON instead of markdown",
    )
    return parser.parse_args()


def sanitize_branch_name(branch: str) -> str:
    return re.sub(r"[^\w\-.]", "_", branch)


def determine_output_file(output: str | None, branch: str, json_output: bool) -> str:
    safe_branch_name = sanitize_branch_name(branch)
    extension = "json" if json_output else "md"
    default_filename = f"review_{safe_branch_name}.{extension}"

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


def main() -> None:
    args = parse_arguments()

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

    output_file = determine_output_file(args.output, current_branch, args.json)
    print_summary(repo_path, current_branch, args.target_branch, output_file)
    print_model_config(has_instructions=bool(args.instructions))

    try:
        changed_files = get_changed_files(repo_path, args.target_branch)
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

    review_result = run_review(
        repo_path=repo_path,
        target_branch=args.target_branch,
        changed_files=changed_files,
        additional_instructions=additional_instructions,
    )

    # Optionally run verification
    final_output: PrimaryReviewOutput | VerifiedReviewOutput
    total_token_usage = review_result.token_usage

    if args.verify and review_result.output.issues:
        print()
        final_output, verify_token_usage = run_verification(
            primary_output=review_result.output,
            system_prompt=review_result.system_prompt,
            user_message=review_result.user_message,
            file_context=review_result.file_context,
            repo_path=repo_path,
        )
        if verify_token_usage and total_token_usage:
            total_token_usage = total_token_usage + verify_token_usage
    else:
        final_output = review_result.output

    # Render output
    print()
    if args.json:
        review_content = json.dumps(final_output.model_dump(), indent=2)
    else:
        review_content = render_structured_output(final_output)
        review_content = format_review_content(review_content)

    Path(output_file).write_text(review_content)
    print(f"✓ Review completed and saved to: {output_file}")

    if total_token_usage:
        print()
        total_token_usage.print()


if __name__ == "__main__":
    main()
