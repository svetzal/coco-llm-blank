"""Docling conversion with per-page checkpoints and source provenance."""

import hashlib
import json
import tempfile
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

import pypdfium2 as pdfium


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(text)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def conversion_profile():
    return {
        "format": 1,
        "docling": version("docling"),
        "docling-core": version("docling-core"),
        "rapidocr": version("rapidocr"),
        "ocr": "rapidocr-onnx-full-page",
        "language": "en",
        "tables": True,
    }


@lru_cache(maxsize=1)
def converter():
    # Lazy imports keep guidance-only and cached runs independent of model startup.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = True
    options.ocr_options = RapidOcrOptions(
        backend="onnxruntime", mode=OcrMode.FULL_PAGE, lang=["en"]
    )
    options.do_table_structure = True
    options.enable_remote_services = False
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


def convert_page(source, number):
    from docling.datamodel.base_models import ConversionStatus

    result = converter().convert(source, page_range=(number, number))
    if result.status != ConversionStatus.SUCCESS:
        raise RuntimeError(f"Docling did not finish PDF page {number}: {result.status}")
    return {
        "markdown": result.document.export_to_markdown(),
        "document": result.document.export_to_dict(),
    }


def convert(resource, directory, page_range=None):
    source = directory / "source.pdf"
    with source.open("rb") as stream:
        actual_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual_digest != resource["sha256"]:
        raise ValueError("Source PDF checksum differs from the manifest")
    with pdfium.PdfDocument(source) as document:
        total = len(document)
    first, last = page_range or (1, total)
    if not 1 <= first <= last <= total:
        raise ValueError(f"Page range must be within 1..{total}")
    profile = conversion_profile()
    identity = {"sha256": actual_digest, "profile": profile}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    checkpoint_dir = directory / "docling-pages" / key
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    completed = {}
    for checkpoint in checkpoint_dir.glob("*.json"):
        record = json.loads(checkpoint.read_text())
        number = record["page"]
        if record["identity"] != identity or not 1 <= number <= total:
            raise ValueError(f"Invalid checkpoint: {checkpoint}")
        completed[number] = record
    try:
        for number in range(first, last + 1):
            if number in completed:
                print(f"  Reusing PDF page {number}/{total}", flush=True)
                continue
            print(f"  Docling PDF page {number}/{total}", flush=True)
            converted = convert_page(source, number)
            record = {"identity": identity, "page": number, **converted}
            atomic_text(checkpoint_dir / f"{number:05}.json", json.dumps(record) + "\n")
            completed[number] = record
    finally:
        # Even an interrupted run exposes only fully checkpointed pages.
        # If the first page fails, existing output remains untouched.
        if completed:
            sparse = [
                n for n, item in sorted(completed.items()) if len(item["markdown"].strip()) < 80
            ]
            status = f"{len(completed)}/{total} PDF pages converted with Docling; {len(sparse)} sparse pages"
            header = (
                f"# {resource['title']}\n\nSource: {resource['url']}\n\n"
                f"SHA-256: {actual_digest}\n\n{status}.\n\n"
                "PDF page numbers include covers. OCR is unverified. "
                "Consult the source PDF for pictures and ambiguous code.\n\n"
            )
            body = "\n".join(
                f"## PDF page {n}\n\n{item['markdown']}\n" for n, item in sorted(completed.items())
            )
            atomic_text(directory / "text.md", header + body)
            atomic_text(
                directory / "extraction.json",
                json.dumps(
                    {
                        **identity,
                        "pages": total,
                        "completed_pages": sorted(completed),
                        "sparse_pages": sparse,
                        "status": status,
                        "checkpoints": str(checkpoint_dir.relative_to(directory)),
                    },
                    indent=2,
                )
                + "\n",
            )
    return status
