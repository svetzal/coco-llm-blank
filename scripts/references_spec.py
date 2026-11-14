"""Executable behavior for resumable local references."""

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import setup
from PIL import Image, ImageDraw, ImageFont
from references import (
    ConversionError,
    ConversionProfile,
    ConvertedPage,
    DoclingGateway,
    Resource,
    conversion_profile,
    convert,
)


@pytest.fixture
def document_gateway() -> Mock:
    gateway = Mock(spec=DoclingGateway)
    gateway.page_count.return_value = 2
    gateway.profile.return_value = conversion_profile()
    return gateway


class DescribeReferenceConversion:
    def should_reuse_the_original_checkpoint_wire_format(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        # Captured v1 format and canonical key from the pre-refactor converter.
        profile = {
            "format": 1,
            "docling": "2.150.0",
            "docling-core": "2.107.0",
            "rapidocr": "3.10.0",
            "ocr": "rapidocr-onnx-full-page",
            "language": "en",
            "tables": True,
        }
        key = "6f6cd40c208f838ed6a9d273359e52e1f031eef0087d1cec8890038abba9351f"
        directory = book / "docling-pages" / key
        directory.mkdir(parents=True)
        checkpoint = directory / "00001.json"
        original = json.dumps(
            {
                "identity": {"sha256": resource.sha256, "profile": profile},
                "page": 1,
                "markdown": "Previously converted page",
                "document": {},
            }
        )
        checkpoint.write_text(original)
        document_gateway.profile.return_value = ConversionProfile.model_validate(profile)
        document_gateway.convert_page.side_effect = ConversionError("model offline")

        convert(resource, book, (1, 1), documents=document_gateway)

        assert "Previously converted page" in (book / "text.md").read_text()
        assert checkpoint.read_text() == original
        assert (
            json.loads((book / "extraction.json").read_text())["checkpoints"]
            == f"docling-pages/{key}"
        )

    def should_resume_successful_pages_after_a_model_failure(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        first = ConvertedPage(markdown="# First page\n\nOriginal text.", document={})
        second = ConvertedPage(markdown="# Second page\n\nMore text.", document={})
        document_gateway.convert_page.side_effect = [first, ConversionError("model unavailable")]

        with pytest.raises(ConversionError, match="model unavailable"):
            convert(resource, book, documents=document_gateway)

        assert json.loads((book / "extraction.json").read_text())["completed_pages"] == [1]
        checkpoint = next((book / "docling-pages").rglob("00001.json"))
        saved = checkpoint.read_bytes()
        document_gateway.convert_page.side_effect = [second]

        convert(resource, book, documents=document_gateway)

        text = (book / "text.md").read_text()
        assert "First page" in text and "Second page" in text
        assert checkpoint.read_bytes() == saved
        assert json.loads((book / "extraction.json").read_text())["completed_pages"] == [1, 2]
        document_gateway.convert_page.side_effect = ConversionError("model offline")

        convert(resource, book, page_range=(1, 1), documents=document_gateway)

        assert (book / "text.md").read_text() == text

    def should_start_fresh_when_the_converter_profile_changes(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        document_gateway.convert_page.return_value = ConvertedPage(markdown="old", document={})
        convert(resource, book, (1, 1), documents=document_gateway)
        document_gateway.profile.return_value = conversion_profile().model_copy(
            update={"docling": "next"}
        )
        document_gateway.convert_page.return_value = ConvertedPage(markdown="new", document={})

        convert(resource, book, (1, 1), documents=document_gateway)

        assert "new" in (book / "text.md").read_text()
        assert len(list((book / "docling-pages").iterdir())) == 2

    def should_preserve_existing_output_when_the_first_page_fails(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        (book / "text.md").write_text("existing output")
        document_gateway.convert_page.side_effect = ConversionError("conversion failed")

        with pytest.raises(ConversionError):
            convert(resource, book, documents=document_gateway)

        assert (book / "text.md").read_text() == "existing output"

    @pytest.mark.parametrize("page_range", [(0, 1), (2, 1), (1, 99)])
    def should_reject_out_of_bounds_page_ranges(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
        page_range: tuple[int, int],
    ) -> None:
        with pytest.raises(ValueError, match="Page range"):
            convert(resource, book, page_range, documents=document_gateway)

        assert not (book / "text.md").exists()

    def should_reject_a_damaged_source(self, resource: Resource, book: Path) -> None:
        (book / "source.pdf").write_bytes(b"damaged")

        with pytest.raises(ValueError, match="checksum"):
            convert(resource, book)

        assert not (book / "text.md").exists()

    @pytest.mark.parametrize("damage", ["identity", "page", "filename"])
    def should_reject_invalid_checkpoints(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
        damage: str,
    ) -> None:
        document_gateway.convert_page.return_value = ConvertedPage(markdown="original", document={})
        convert(resource, book, (1, 1), documents=document_gateway)
        checkpoint = next((book / "docling-pages").rglob("00001.json"))
        record = json.loads(checkpoint.read_text())
        if damage == "identity":
            record["identity"]["sha256"] = "0" * 64
        elif damage == "page":
            record["page"] = 99
        else:
            checkpoint.rename(checkpoint.with_name("00002.json"))
            checkpoint = checkpoint.with_name("00002.json")
        checkpoint.write_text(json.dumps(record))
        saved = (book / "text.md").read_bytes()

        with pytest.raises(ValueError, match="Invalid checkpoint"):
            convert(resource, book, documents=document_gateway)

        assert (book / "text.md").read_bytes() == saved

    @pytest.mark.integration
    def should_report_a_real_pdf_backend_failure(self, tmp_path: Path) -> None:
        source = tmp_path / "broken.pdf"
        source.write_bytes(b"%PDF-broken")

        with pytest.raises(ConversionError, match="PDF page 1"):
            DoclingGateway().convert_page(source, 1)

    @pytest.mark.integration
    def should_convert_a_scanned_pdf_through_setup_and_keep_original_page_numbers(
        self,
        tmp_path: Path,
    ) -> None:
        image = Image.fromarray(np.full((1100, 850, 3), 255, dtype=np.uint8))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=28)
        draw.text((60, 80), "COCO REFERENCE TEST", font=font, fill="black")
        draw.text((60, 150), "A register holds a value.", font=font, fill="black")
        directory = tmp_path / "local/references/scan"
        directory.mkdir(parents=True)
        source = directory / "source.pdf"
        Image.new("RGB", image.size, "white").save(
            source,
            "PDF",
            resolution=100,
            save_all=True,
            append_images=[image],
        )
        resource = Resource(
            id="scan",
            title="Original scan",
            url="https://colorcomputerarchive.com/repo/test-scan.pdf",
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        (tmp_path / "resources.json").write_text(json.dumps([resource.model_dump()]))

        result = setup.main(["--target", "coco2", "--pages", "2:2"], tmp_path)

        assert result == 0
        assert "1/2 PDF pages converted with Docling" in (tmp_path / "local/INDEX.md").read_text()
        text = (directory / "text.md").read_text()
        assert "COCO REFERENCE TEST" in text
        assert "A register holds a value." in text
        assert "## PDF page 2" in text
        checkpoint = json.loads(next((directory / "docling-pages").rglob("00002.json")).read_text())
        assert checkpoint["document"]["texts"][0]["prov"][0]["page_no"] == 2
