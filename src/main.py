import argparse
import re
import subprocess
import sys
from pathlib import Path

from .agent.runner import run_review
from .agent.schema import Context
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
        "--mode",
        choices=["full", "summary"],
        default="full",
        help="Review mode: full (comprehensive review) or summary (high-level overview)",
    )
    return parser.parse_args()


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

    context = Context(
        repo_path=repo_path,
        target_branch=args.target_branch,
        changed_files=changed_files,
    )

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

    review_content, token_usage = run_review(
        context, mode=args.mode, additional_instructions=additional_instructions
    )

    print()
    Path(output_file).write_text(review_content)
    print(f"✓ Review completed and saved to: {output_file}")

    if token_usage:
        print()
        print("Token Usage:")
        print(f"  Input tokens:  {token_usage['total_input_tokens']:,}")
        print(f"  Output tokens: {token_usage['output_tokens']:,}")
        print(f"  Total tokens:  {token_usage['total_tokens']:,}")


if __name__ == "__main__":
    main()
