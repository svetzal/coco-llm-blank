"""Isolated evidence from real assembly and bounded headless executions."""

import uuid
from pathlib import Path

import pytest
import validate


@pytest.fixture(scope="session")
def evidence():
    output = validate.ROOT / "build/game-state-coco3" / ("spec-" + uuid.uuid4().hex[:12])
    return validate.check(output)


@pytest.fixture
def good_capture(evidence):
    return Path(evidence["runs"][0]["snapshot"]).read_bytes()
