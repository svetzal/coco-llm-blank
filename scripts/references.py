"""Validate reference records and resume Docling conversion at page boundaries."""

import hashlib
import json
import tempfile
from functools import cached_property
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import pypdfium2 as pdfium
from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Resource(BaseModel):
    """One source PDF declared in the download manifest."""

    model_config = ConfigDict(frozen=True)
    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    url: str
    sha256: Sha256


class ConversionProfile(BaseModel):
    """The converter settings that determine whether a checkpoint is reusable."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)
    format: int = 1
    docling: str
    docling_core: str = Field(alias="docling-core")
    rapidocr: str
    ocr: str = "rapidocr-onnx-full-page"
    language: str = "en"
    tables: bool = True


class ConversionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256: Sha256
    profile: ConversionProfile

    def checkpoint_key(self) -> str:
        """Keep the original canonical JSON encoding for existing checkpoints."""
        serialized = json.dumps(self.model_dump(by_alias=True), sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


class ConvertedPage(BaseModel):
    model_config = ConfigDict(frozen=True)
    markdown: str
    document: dict[str, JsonValue]


class PageCheckpoint(ConvertedPage):
    identity: ConversionIdentity
    page: int = Field(ge=1)


class Extraction(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256: Sha256
    profile: ConversionProfile
    pages: int = Field(ge=1)
    completed_pages: list[int]
    sparse_pages: list[int]
    status: str
    checkpoints: str


class ConversionError(RuntimeError):
    """The document backend failed to produce a complete page."""


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_text(path: Path, text: str) -> None:
    """Replace text only after the complete new file has been written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def conversion_profile() -> ConversionProfile:
    return ConversionProfile(
        docling=version("docling"),
        docling_core=version("docling-core"),
        rapidocr=version("rapidocr"),
    )


class DoclingGateway:
    """Isolate PDF parsing and model execution from checkpoint behavior."""

    def profile(self) -> ConversionProfile:
        return conversion_profile()

    def page_count(self, source: Path) -> int:
        with pdfium.PdfDocument(source) as document:
            return len(document)

    @cached_property
    def converter(self) -> "DocumentConverter":
        # Cached and guidance-only runs do not initialize the model pipeline.
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions, RapidOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options = PdfPipelineOptions()
        options.do_ocr = True
        options.ocr_options = RapidOcrOptions(
            backend="onnxruntime",
            mode=OcrMode.FULL_PAGE,
            lang=["en"],
        )
        options.do_table_structure = True
        options.enable_remote_services = False
        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
        )

    def convert_page(self, source: Path, number: int) -> ConvertedPage:
        """Normalize model/backend failures into a conversion error for the CLI."""
        from docling.datamodel.base_models import ConversionStatus

        try:
            result = self.converter.convert(source, page_range=(number, number))
            if result.status != ConversionStatus.SUCCESS:
                raise ConversionError(f"Docling did not finish PDF page {number}: {result.status}")
            return ConvertedPage(
                markdown=result.document.export_to_markdown(),
                document=result.document.export_to_dict(),
            )
        except Exception as error:
            raise ConversionError(f"PDF page {number}: {error}") from error


class ReferenceStore:
    """Read and publish a book's local files without exposing partial checkpoints."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.source = directory / "source.pdf"

    def validate_source(self, resource: Resource) -> None:
        if digest(self.source) != resource.sha256:
            raise ValueError("Source PDF checksum differs from the manifest")

    def checkpoint_directory(self, identity: ConversionIdentity) -> Path:
        return self.directory / "docling-pages" / identity.checkpoint_key()

    def read_checkpoints(
        self,
        identity: ConversionIdentity,
        total: int,
    ) -> dict[int, PageCheckpoint]:
        completed = {}
        for path in self.checkpoint_directory(identity).glob("*.json"):
            record = PageCheckpoint.model_validate_json(path.read_text())
            if (
                record.identity != identity
                or record.page > total
                or path.stem != f"{record.page:05}"
            ):
                raise ValueError(f"Invalid checkpoint: {path}")
            completed[record.page] = record
        return completed

    def save_checkpoint(self, checkpoint: PageCheckpoint) -> None:
        path = self.checkpoint_directory(checkpoint.identity) / f"{checkpoint.page:05}.json"
        atomic_text(path, checkpoint.model_dump_json(by_alias=True) + "\n")

    def publish(
        self, resource: Resource, extraction: Extraction, pages: list[PageCheckpoint]
    ) -> None:
        atomic_text(self.directory / "text.md", reference_markdown(resource, extraction, pages))
        atomic_text(
            self.directory / "extraction.json",
            extraction.model_dump_json(indent=2, by_alias=True) + "\n",
        )


def summarize(
    identity: ConversionIdentity,
    total: int,
    completed: dict[int, PageCheckpoint],
) -> Extraction:
    sparse = [
        number for number, page in sorted(completed.items()) if len(page.markdown.strip()) < 80
    ]
    return Extraction(
        sha256=identity.sha256,
        profile=identity.profile,
        pages=total,
        completed_pages=sorted(completed),
        sparse_pages=sparse,
        status=f"{len(completed)}/{total} PDF pages converted with Docling; {len(sparse)} sparse pages",
        checkpoints=f"docling-pages/{identity.checkpoint_key()}",
    )


def reference_markdown(
    resource: Resource, extraction: Extraction, pages: list[PageCheckpoint]
) -> str:
    header = (
        f"# {resource.title}\n\nSource: {resource.url}\n\n"
        f"SHA-256: {resource.sha256}\n\n{extraction.status}.\n\n"
        "PDF page numbers include covers. OCR is unverified. "
        "Consult the source PDF for pictures and ambiguous code.\n\n"
    )
    body = "\n".join(f"## PDF page {page.page}\n\n{page.markdown}\n" for page in pages)
    return header + body


def convert(
    resource: Resource,
    directory: Path,
    page_range: tuple[int, int] | None = None,
    *,
    documents: DoclingGateway | None = None,
) -> str:
    """Convert missing pages, retaining complete checkpoints even after failure."""
    documents = documents or DoclingGateway()
    store = ReferenceStore(directory)
    store.validate_source(resource)
    total = documents.page_count(store.source)
    first, last = page_range or (1, total)
    if not 1 <= first <= last <= total:
        raise ValueError(f"Page range must be within 1..{total}")
    identity = ConversionIdentity(sha256=resource.sha256, profile=documents.profile())
    completed = store.read_checkpoints(identity, total)
    try:
        for number in range(first, last + 1):
            if number in completed:
                print(f"  Reusing PDF page {number}/{total}", flush=True)
                continue
            print(f"  Docling PDF page {number}/{total}", flush=True)
            page = documents.convert_page(store.source, number)
            checkpoint = PageCheckpoint(identity=identity, page=number, **page.model_dump())
            store.save_checkpoint(checkpoint)
            completed[number] = checkpoint
    finally:
        if completed:
            extraction = summarize(identity, total, completed)
            store.publish(resource, extraction, [completed[n] for n in sorted(completed)])
    return extraction.status
