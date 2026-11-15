"""Size limits for the git-tracked tree, so that growth is a deliberate decision.

The root suite checks these limits in CI. To raise a limit, edit its constant
here in a commit that says why.
"""

import subprocess
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

MAX_TOTAL_BYTES = 1_200_000
MAX_FILE_BYTES = 100_000
EXEMPT_PATHS = frozenset({"uv.lock"})
LARGEST_FILES_SHOWN = 5


class TrackedFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    size: int


def tracked_files(root: Path) -> list[TrackedFile]:
    """Return the working-tree size of each git-tracked file that still exists."""
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    ).stdout.decode()
    paths = (root / name for name in listing.split("\0") if name)
    return [
        TrackedFile(path=path.relative_to(root).as_posix(), size=path.stat().st_size)
        for path in paths
        if path.is_file()
    ]


def size_problems(
    files: Iterable[TrackedFile],
    *,
    max_total: int = MAX_TOTAL_BYTES,
    max_file: int = MAX_FILE_BYTES,
) -> list[str]:
    """Describe each limit that the tracked files exceed. An empty list means they fit."""
    measured = sorted(
        (file for file in files if file.path not in EXEMPT_PATHS),
        key=lambda file: (-file.size, file.path),
    )
    total = sum(file.size for file in measured)
    problems = []
    if total > max_total:
        problems.append(
            f"The tracked files total {total:,} bytes, over the limit of {max_total:,} bytes "
            f"(MAX_TOTAL_BYTES). Largest files: {_listing(measured[:LARGEST_FILES_SHOWN])}."
        )
    if oversized := [file for file in measured if file.size > max_file]:
        problems.append(
            f"{len(oversized)} tracked file(s) exceed the limit of {max_file:,} bytes per file "
            f"(MAX_FILE_BYTES): {_listing(oversized)}."
        )
    if problems:
        problems.append(
            "Raising a limit is a deliberate decision: edit its constant in "
            "scripts/repository_size.py in a commit that says why."
        )
    return problems


def _listing(files: Iterable[TrackedFile]) -> str:
    return ", ".join(f"{file.path} ({file.size:,} bytes)" for file in files)
