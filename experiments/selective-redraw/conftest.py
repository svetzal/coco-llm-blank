"""A real bounded emulator run for this experiment's specifications."""

import uuid

import pytest
import selective_redraw as renderer


@pytest.fixture(scope="session")
def evidence():
    output = renderer.ROOT / "build/selective-redraw" / ("spec-" + uuid.uuid4().hex[:12])
    return renderer.check(output)
