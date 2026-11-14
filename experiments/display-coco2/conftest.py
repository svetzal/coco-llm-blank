"""Fresh private build shared within this scoped test session."""

import json
import sys
import uuid

import coco2
import pytest


@pytest.fixture(scope="session")
def reproduction():
    name = "spec-" + uuid.uuid4().hex[:12]
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sys, "argv", ["coco2.py", "--run-id", name])
        coco2.main()
    work, output = coco2.RESEARCH / name, coco2.OUTPUT / name
    return work, output, json.loads((output / "results.json").read_text())
