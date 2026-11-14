"""Keep all generated emulator and coverage evidence isolated from other tasks."""

import uuid

import loading
import pytest


@pytest.fixture(scope="session")
def evidence():
    output = loading.ROOT / "build/asset-loading" / ("spec-" + uuid.uuid4().hex[:12])
    return output, loading.check(output)


@pytest.fixture
def inputs(tmp_path):
    source, bundle = tmp_path / "source.json", tmp_path / "bundle.json"
    source.write_bytes(loading.SOURCE.read_bytes())
    loading.prepare.publish(source, bundle)
    return source, bundle
