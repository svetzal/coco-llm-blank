"""A size limit for each git-tracked file, so that a large file is a deliberate decision.

The root suite checks this limit in CI. To raise it, edit its constant here in a
commit that says why.
"""

import subprocess
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

MAX_FILE_BYTES = 100_000
EXEMPT_PATHS = frozenset({"uv.lock"})


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
    max_file: int = MAX_FILE_BYTES,
) -> list[str]:
    """Describe the tracked files over the per-file limit. An empty list means they fit."""
    oversized = sorted(
        (file for file in files if file.path not in EXEMPT_PATHS and file.size > max_file),
        key=lambda file: (-file.size, file.path),
    )
    if not oversized:
        return []
    found = (
        f"{len(oversized)} tracked file(s) exceed the limit of {max_file:,} bytes per file "
        f"(MAX_FILE_BYTES): {_listing(oversized)}."
    )
    advice = (
        "Raising the limit is a deliberate decision: edit its constant in "
        "scripts/repository_size.py in a commit that says why."
    )
    return [found, advice]


def _listing(files: Iterable[TrackedFile]) -> str:
    return ", ".join(f"{file.path} ({file.size:,} bytes)" for file in files)
