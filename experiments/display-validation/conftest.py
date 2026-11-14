"""Real private rebuild, shared only within one experiment test session."""

import json
import sys
import uuid

import pytest
import reproduce


@pytest.fixture(scope="session")
def reproduction():
    name = "spec-" + uuid.uuid4().hex[:12]
    with pytest.MonkeyPatch.context() as context:
        context.setattr(sys, "argv", ["reproduce.py", "--run-id", name])
        reproduce.main()
    output = reproduce.OUTPUT / name
    return reproduce.RESEARCH / name, output, json.loads((output / "results.json").read_text())
