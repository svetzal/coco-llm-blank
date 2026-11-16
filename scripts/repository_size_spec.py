"""Each tracked file stays within the committed per-file size limit."""

import subprocess
from pathlib import Path

import pytest
from repository_size import TrackedFile, size_problems, tracked_files

ROOT = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    git(tmp_path, "init", "--quiet")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/with space.md").write_bytes(b"x" * 7)
    (tmp_path / "kept.txt").write_bytes(b"x" * 3)
    (tmp_path / "deleted.txt").write_bytes(b"x" * 5)
    git(tmp_path, "add", ".")
    (tmp_path / "deleted.txt").unlink()
    (tmp_path / "untracked.txt").write_bytes(b"x" * 11)
    return tmp_path


class DescribeTheRepository:
    def should_keep_each_file_within_the_limit(self) -> None:
        problems = size_problems(tracked_files(ROOT))

        assert problems == [], "\n".join(problems)


class DescribeTrackedFiles:
    def should_measure_tracked_working_tree_files_with_spaces_in_their_paths(
        self, checkout: Path
    ) -> None:
        files = tracked_files(checkout)

        assert sorted(files, key=lambda file: file.path) == [
            TrackedFile(path="docs/with space.md", size=7),
            TrackedFile(path="kept.txt", size=3),
        ]


class DescribeSizeProblems:
    def should_accept_files_at_the_limit_whatever_their_total(self) -> None:
        files = [TrackedFile(path=f"file{n}", size=60) for n in range(100)]

        assert size_problems(files, max_file=60) == []

    def should_name_each_file_over_the_single_file_limit(self) -> None:
        files = [
            TrackedFile(path="small", size=10),
            TrackedFile(path="big one", size=101),
            TrackedFile(path="bigger", size=150),
        ]

        problems = size_problems(files, max_file=100)

        assert problems[0] == (
            "2 tracked file(s) exceed the limit of 100 bytes per file (MAX_FILE_BYTES): "
            "bigger (150 bytes), big one (101 bytes)."
        )
        assert "deliberate decision" in problems[-1]
        assert "scripts/repository_size.py" in problems[-1]
        assert len(problems) == 2

    def should_exempt_the_lockfile(self) -> None:
        files = [TrackedFile(path="uv.lock", size=5_000), TrackedFile(path="a", size=10)]

        assert size_problems(files, max_file=100) == []

    def should_measure_a_nested_lockfile_like_any_other_file(self) -> None:
        files = [TrackedFile(path="examples/uv.lock", size=500)]

        assert size_problems(files, max_file=100) != []
