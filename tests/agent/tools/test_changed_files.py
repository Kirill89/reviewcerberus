import subprocess

from src.agent.tools.changed_files import _changed_files_impl
from tests.test_helper import create_test_repo


def test_changed_files() -> None:
    with create_test_repo() as repo_path:
        result = _changed_files_impl(str(repo_path), "main")

        assert isinstance(result, list)
        assert len(result) == 2

        file1 = next(f for f in result if f.path == "file1.py")
        assert file1.change_type == "modified"
        assert file1.additions > 0
        assert file1.deletions > 0

        file3 = next(f for f in result if f.path == "file3.py")
        assert file3.change_type == "added"
        assert file3.additions > 0
        assert file3.deletions == 0


def test_changed_files_with_binary() -> None:
    """Test that binary files are handled correctly (git outputs '-' for numstat)."""
    with create_test_repo() as repo_path:
        # Create a binary file (simple PNG header bytes)
        binary_file = repo_path / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

        # Also modify a text file to verify mixed changes work
        (repo_path / "file1.py").write_text(
            "def hello():\n    print('modified again')\n    return 42\n"
        )

        # Commit the changes
        subprocess.run(
            ["git", "-C", str(repo_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", "Add binary file"],
            check=True,
            capture_output=True,
        )

        # Test the function
        result = _changed_files_impl(str(repo_path), "main")

        assert isinstance(result, list)
        assert (
            len(result) == 3
        )  # file1.py (modified), file3.py (added), image.png (added)

        # Check text file has proper stats
        file1 = next(f for f in result if f.path == "file1.py")
        assert file1.change_type == "modified"
        assert file1.additions > 0
        assert file1.deletions > 0

        # Check binary file has 0 additions/deletions (git can't compute line changes)
        binary = next(f for f in result if f.path == "image.png")
        assert binary.change_type == "added"
        assert binary.additions == 0
        assert binary.deletions == 0
