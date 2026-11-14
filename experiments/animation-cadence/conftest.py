"""One real private build and case matrix for boundary tests."""

import json
import sys
import uuid

import cadence
import pytest


@pytest.fixture(scope="session")
def reproduction():
    name = "spec-" + uuid.uuid4().hex[:12]
    with pytest.MonkeyPatch.context() as context:
        context.setattr(sys, "argv", ["cadence.py", "--run-id", name])
        cadence.main()
    work = cadence.ROOT / "local/research/animation-cadence" / name
    out = cadence.ROOT / "build/animation-cadence" / name
    return work, out, json.loads((out / "results.json").read_text())
