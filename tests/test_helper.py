import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator
from unittest.mock import Mock

from src.agent.schema import Context


@contextmanager
def create_test_repo() -> Generator[Path, None, None]:
    repo_path = Path(tempfile.mkdtemp())

    def git(*args: Any) -> None:
        subprocess.run(
            ["git", "-C", str(repo_path)] + list(args), check=True, capture_output=True
        )

    try:
        git("init", "-b", "main")
        git("config", "user.name", "Test User")
        git("config", "user.email", "test@example.com")

        (repo_path / "file1.py").write_text("def hello():\n    print('hello')\n")
        (repo_path / "file2.py").write_text("def world():\n    print('world')\n")
        git("add", ".")
        git("commit", "-m", "Initial commit")

        git("checkout", "-b", "feature")
        (repo_path / "file1.py").write_text(
            "def hello():\n    print('hello world')\n    return True\n"
        )
        (repo_path / "file3.py").write_text("def new_func():\n    pass\n")
        git("add", ".")
        git("commit", "-m", "Add feature")

        yield repo_path
    finally:
        shutil.rmtree(repo_path, ignore_errors=True)


def create_mock_runtime(repo_path: str, target_branch: str = "main") -> Mock:
    context = Context(
        repo_path=repo_path, target_branch=target_branch, changed_files=[]
    )
    runtime = Mock()
    runtime.context = context
    runtime.tool_call_id = "test"
    return runtime
