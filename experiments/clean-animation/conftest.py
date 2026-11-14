"""Run the whole real matrix once, with a private source build."""

import json
import sys
import uuid

import clean
import pytest


@pytest.fixture(scope="session")
def reproduction():
    name = "spec-" + uuid.uuid4().hex[:12]
    with pytest.MonkeyPatch.context() as context:
        context.setattr(sys, "argv", ["clean.py", "--run-id", name])
        clean.main()
    out = clean.ROOT / "build/clean-animation" / name
    work = clean.ROOT / "local/research/clean-animation" / name
    return work, out, json.loads((out / "results.json").read_text())
