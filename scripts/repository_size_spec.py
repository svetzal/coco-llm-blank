"""The tracked tree stays within its committed size limits."""

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
    def should_fit_within_its_size_limits(self) -> None:
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
    def should_accept_files_at_the_limits(self) -> None:
        files = [TrackedFile(path="a", size=60), TrackedFile(path="b", size=40)]

        assert size_problems(files, max_total=100, max_file=60) == []

    def should_name_the_total_the_limit_and_the_largest_files_when_the_total_is_over(
        self,
    ) -> None:
        files = [TrackedFile(path=f"file{n}", size=n * 1_000) for n in range(1, 8)]

        problems = size_problems(files, max_total=27_999, max_file=10_000)

        assert problems[0] == (
            "The tracked files total 28,000 bytes, over the limit of 27,999 bytes "
            "(MAX_TOTAL_BYTES). Largest files: file7 (7,000 bytes), file6 (6,000 bytes), "
            "file5 (5,000 bytes), file4 (4,000 bytes), file3 (3,000 bytes)."
        )
        assert "deliberate decision" in problems[-1]
        assert "scripts/repository_size.py" in problems[-1]
        assert len(problems) == 2

    def should_name_each_file_over_the_single_file_limit(self) -> None:
        files = [
            TrackedFile(path="small", size=10),
            TrackedFile(path="big one", size=101),
            TrackedFile(path="bigger", size=150),
        ]

        problems = size_problems(files, max_total=1_000, max_file=100)

        assert problems[0] == (
            "2 tracked file(s) exceed the limit of 100 bytes per file (MAX_FILE_BYTES): "
            "bigger (150 bytes), big one (101 bytes)."
        )
        assert "deliberate decision" in problems[-1]
        assert len(problems) == 2

    def should_report_both_limits_when_both_are_exceeded(self) -> None:
        files = [TrackedFile(path="huge", size=500)]

        problems = size_problems(files, max_total=100, max_file=100)

        assert len(problems) == 3
        assert "(MAX_TOTAL_BYTES)" in problems[0]
        assert "(MAX_FILE_BYTES)" in problems[1]

    def should_exempt_the_lockfile_from_both_limits(self) -> None:
        files = [TrackedFile(path="uv.lock", size=5_000), TrackedFile(path="a", size=10)]

        assert size_problems(files, max_total=100, max_file=100) == []

    def should_measure_a_nested_lockfile_like_any_other_file(self) -> None:
        files = [TrackedFile(path="examples/uv.lock", size=500)]

        assert size_problems(files, max_total=1_000, max_file=100) != []
