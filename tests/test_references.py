import hashlib
import json

import numpy as np
import pytest
import references
from PIL import Image, ImageDraw, ImageFont
from test_setup import bootstrap, pdf_bytes


@pytest.fixture
def book(tmp_path):
    (tmp_path / "source.pdf").write_bytes(pdf_bytes())
    return {
        "id": "fixture",
        "title": "Original reference",
        "url": "https://example.test/book.pdf",
        "sha256": hashlib.sha256(pdf_bytes()).hexdigest(),
    }, tmp_path


def test_resume_preserves_pages_and_records_partial_failure(book, monkeypatch):
    resource, directory = book

    def interrupted(source, number):
        if number == 2:
            raise RuntimeError("model unavailable")
        return {"markdown": "# First page\n\nOriginal text.", "document": {}}

    monkeypatch.setattr(references, "convert_page", interrupted)
    with pytest.raises(RuntimeError, match="model unavailable"):
        references.convert(resource, directory)
    assert json.loads((directory / "extraction.json").read_text())["completed_pages"] == [1]
    first_checkpoint = next((directory / "docling-pages").rglob("00001.json"))
    before = first_checkpoint.stat().st_mtime_ns

    def resumed(source, number):
        assert number == 2, "a completed page must not require the model again"
        return {"markdown": "# Second page\n\nMore original text.", "document": {}}

    monkeypatch.setattr(references, "convert_page", resumed)
    references.convert(resource, directory)
    text = (directory / "text.md").read_text()
    assert "First page" in text and "Second page" in text
    assert first_checkpoint.stat().st_mtime_ns == before
    assert json.loads((directory / "extraction.json").read_text())["completed_pages"] == [1, 2]
    references.convert(resource, directory, page_range=(1, 1))
    assert (directory / "text.md").read_text() == text


def test_version_change_does_not_reuse_stale_conversion(book, monkeypatch):
    resource, directory = book
    monkeypatch.setattr(references, "convert_page", lambda *_: {"markdown": "old", "document": {}})
    references.convert(resource, directory, (1, 1))
    monkeypatch.setattr(references, "conversion_profile", lambda: {"format": "changed"})
    monkeypatch.setattr(references, "convert_page", lambda *_: {"markdown": "new", "document": {}})
    references.convert(resource, directory, (1, 1))
    assert "new" in (directory / "text.md").read_text()
    assert len(list((directory / "docling-pages").iterdir())) == 2


def test_first_failure_preserves_output_and_invalid_ranges_do_not_convert(book, monkeypatch):
    resource, directory = book
    (directory / "text.md").write_text("existing output")

    def failed(*_):
        raise RuntimeError("conversion failed")

    monkeypatch.setattr(references, "convert_page", failed)
    with pytest.raises(RuntimeError):
        references.convert(resource, directory)
    assert (directory / "text.md").read_text() == "existing output"
    with pytest.raises(ValueError, match="Page range"):
        references.convert(resource, directory, (1, 99))
    (directory / "source.pdf").write_bytes(b"damaged")
    with pytest.raises(ValueError, match="checksum"):
        references.convert(resource, directory)
    assert (directory / "text.md").read_text() == "existing output"


@pytest.mark.integration
def test_docling_reads_an_original_scanned_page_and_keeps_provenance(tmp_path):
    # NumPy and Pillow create a real image-only PDF, exercising the same OCR
    # boundary as archive scans without including anyone else's material.
    image = Image.fromarray(np.full((1100, 850, 3), 255, dtype=np.uint8))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=28)
    draw.text((60, 80), "COCO REFERENCE TEST", font=font, fill="black")
    draw.text((60, 150), "A register holds a value.", font=font, fill="black")
    source = tmp_path / "source.pdf"
    Image.new("RGB", image.size, "white").save(
        source, "PDF", resolution=100, save_all=True, append_images=[image]
    )
    resource = {
        "id": "scan",
        "title": "Original scan",
        "url": "https://colorcomputerarchive.com/repo/test-scan.pdf",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    (tmp_path / "resources.json").write_text(json.dumps([resource]))
    (tmp_path / "local/references/scan").mkdir(parents=True)
    source.rename(tmp_path / "local/references/scan/source.pdf")
    assert bootstrap.main(["--target", "coco2", "--pages", "2:2"], tmp_path) == 0
    assert "1/2 PDF pages converted with Docling" in (tmp_path / "local/INDEX.md").read_text()
    tmp_path = tmp_path / "local/references/scan"
    text = (tmp_path / "text.md").read_text()
    assert "COCO REFERENCE TEST" in text
    assert "A register holds a value." in text
    assert "## PDF page 2" in text
    checkpoint = json.loads(next((tmp_path / "docling-pages").rglob("00002.json")).read_text())
    assert checkpoint["document"]["texts"]
    assert checkpoint["document"]["texts"][0]["prov"][0]["page_no"] == 2
