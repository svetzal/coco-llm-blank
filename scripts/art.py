"""Generate concept art for CoCo games with the OpenAI image API.

Two kinds of JSON file describe the art:

- A visual system contract, one per game: the target machine and mode, the
  palette and its rules, line and shape rules, subject language, background and
  typography policy, a composition policy for each graphic role, quality rules,
  keywords and approved style samples.
- Image specs. Each one names its contract with "Contract" (a path relative to
  the spec file), its graphic "Role", and what to draw. A set spec lists "Items"
  (and optionally "Variants") and makes one image for each item, or for each
  item and variant.

The contract and the layers merge in order, contract first:

- A later scalar or list replaces the earlier value. Lists are not concatenated.
- Objects merge key by key, recursively.
- A key that ends in "+", such as "must+", appends its list to the earlier list
  of the same name. Use it to add constraints or samples without repeating them.

Paths in "Contract", "ApprovedSamples[].file" and "Items[].reference" are
relative to the file that contains them.

Commands:

- compose: merge the contract and layers and write the resolved specification.
- prompt: print the exact prompts. It does not call the API and costs nothing.
- generate: plan the images. With --spend it calls the API, which costs money
  on the owner's OpenAI account. It writes each PNG, a JSON record beside it,
  and a line in manifest.jsonl. Existing images are skipped unless --force.
- schema: print the JSON Schema of a resolved specification.

The API key comes from the OPENAI_API_KEY environment variable.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import string
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from openai import OpenAI, OpenAIError
from PIL import Image
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    PositiveFloat,
    PositiveInt,
    Tag,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

MODELS = {"sunburst": "gpt-image-2.5-sunburst", "flare": "gpt-image-2.5-flare"}
DEFAULT_MODEL = "sunburst"
TRANSPARENT = "transparent"
QUALITIES = ("auto", "low", "medium", "high", "xhigh", "max")
SIZE_PATTERN = r"^(auto|[1-9][0-9]*x[1-9][0-9]*)$"
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
HEX_PATTERN = r"^#[0-9A-Fa-f]{6}$"
APPEND = "+"
MINIMUM_FEATURE_PIXELS = 3
KEY_VARIABLE = "OPENAI_API_KEY"
MANIFEST = "manifest.jsonl"
PLANNED = 2
# Limits from the installed openai package's images.edit documentation.
MAXIMUM_REFERENCES = 16
MAXIMUM_PROMPT = 32000
REFERENCE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")

PREAMBLE = """\
Create one image for a {machine} game. The whole image will be reduced to a \
{width}x{height} grid of target pixels ({mode}). On the display, each target pixel \
is {pixel_aspect}:1, width to height.
Use only these {count} colours, each as flat areas: {colours}. Do not use gradients, \
dithering, anti-aliasing, texture or any other colour.
Make every important shape at least {feature} target pixels across: at least \
{feature_width:.1f}% of the image width and {feature_height:.1f}% of the image height. \
Leave out detail smaller than that.
Follow the JSON specification below exactly. The Context section explains why the \
image exists. Do not draw anything from it. Do not draw text, letters or numbers \
unless the specification explicitly asks for them."""

BACKGROUND = "The background is {background}."

TRANSPARENT_BACKGROUND = """\
The background must be fully transparent. Give the subject crisp, hard edges, with no \
semi-transparent glow, shadow or fringe, and leave generous padding around the subject."""

REFERENCE_INTRO = "The reference images are given in this order:"
SAMPLE_REFERENCE = (
    "{number}. An approved style sample. Match its style ({use}), but use only the listed colours."
)
SUBJECT_REFERENCE = (
    "{number}. The subject. Keep its appearance, proportions, colours and features "
    "exactly as shown."
)
REFERENCE_RULE = (
    "Take the pose, view and composition from the specification, not from the reference images."
)

Role = Literal[
    "screen",
    "background",
    "sprite",
    "sprite-sheet",
    "tile",
    "tile-set",
    "title",
    "icon",
    "concept",
]


# --- The specification -------------------------------------------------------


class Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class OpenSection(BaseModel):
    """A section that accepts extra keys, so authors can add detail."""

    model_config = ConfigDict(frozen=True, extra="allow")


class Colour(Section):
    name: str = Field(min_length=1)
    hex: str = Field(pattern=HEX_PATTERN)
    use: str | None = None

    def describe(self) -> str:
        return f"{self.name} ({self.hex.upper()})"


class Palette(Section):
    """The colours the art may use, and rules for using them."""

    colours: list[Colour] = Field(min_length=1)
    rules: list[str] = []


class Grid(Section):
    width: PositiveInt
    height: PositiveInt


class Target(Section):
    """What the art will be reduced to."""

    machine: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    grid: Grid
    pixel_aspect: PositiveFloat = Field(description="Width / height of one target pixel.")
    background: str = Field(description='The name or hex of one palette colour, or "transparent".')


def find_colour(colours: Sequence[Colour], wanted: str) -> Colour | None:
    """The colour with this name or hex. Hex comparison ignores case."""
    for colour in colours:
        if wanted == colour.name or wanted.lower() == colour.hex.lower():
            return colour
    return None


class Typography(Section):
    default: str = "No words, letters, numbers or pseudo-text."
    allowed: str | None = None


class Sample(Section):
    """An approved image that anchors the style. It is sent as a reference image."""

    file: Path
    use: str = Field(min_length=1)


class Cells(Section):
    columns: PositiveInt
    rows: PositiveInt


class Canvas(Section):
    size: str = Field(default="auto", pattern=SIZE_PATTERN, description="e.g. 1024x1024")
    cells: Cells | None = None
    margin: str | None = None


class Subject(OpenSection):
    """One thing to draw."""

    name: str = Field(min_length=1)
    description: str | None = None


class Item(Subject):
    """One subject of a set spec, with its file name slug and optional reference."""

    slug: str = Field(pattern=SLUG_PATTERN)
    reference: Path | None = None


class Variant(OpenSection):
    """A second dimension of a set, such as an emotion, pose or frame."""

    slug: str = Field(pattern=SLUG_PATTERN)
    name: str = Field(min_length=1)
    description: str | None = None


class Output(Section):
    pattern: str | None = Field(
        default=None, description="Default {slug}.png, or {slug}-{variant}.png with Variants."
    )


class Constraints(Section):
    must: list[str] = []
    must_not: list[str] = []


ONE_SUBJECT = "object"
SUBJECT_LIST = "list"


def _subject_shape(value: object) -> str:
    return SUBJECT_LIST if isinstance(value, list) else ONE_SUBJECT


Subjects = Annotated[
    Annotated[Subject, Tag(ONE_SUBJECT)] | Annotated[list[Subject], Tag(SUBJECT_LIST)],
    Discriminator(_subject_shape),
]


def _unique_slugs(entries: Sequence[Item] | Sequence[Variant]) -> None:
    slugs = [entry.slug for entry in entries]
    if repeated := sorted({slug for slug in slugs if slugs.count(slug) > 1}):
        raise ValueError(f"slugs must be unique; repeated: {', '.join(repeated)}")


class Spec(Section):
    """A resolved specification: the contract with one image or set spec merged on top."""

    name: str | None = Field(default=None, alias="Name")
    visual_language: OpenSection = Field(default=OpenSection(), alias="VisualLanguage")
    palette: Palette = Field(alias="Palette")
    target: Target = Field(alias="Target")
    line_and_shape: OpenSection = Field(default=OpenSection(), alias="LineAndShape")
    subject_language: OpenSection = Field(default=OpenSection(), alias="SubjectLanguage")
    background_policy: OpenSection = Field(default=OpenSection(), alias="BackgroundPolicy")
    typography: Typography = Field(default=Typography(), alias="TypographyPolicy")
    composition_policy: dict[Role, str] = Field(default={}, alias="CompositionPolicy")
    quality_rules: list[str] = Field(default=[], alias="QualityRules")
    keywords: list[str] = Field(default=[], alias="PromptKeywords")
    negative_keywords: list[str] = Field(default=[], alias="NegativeKeywords")
    samples: list[Sample] = Field(default=[], alias="ApprovedSamples")
    role: Role = Field(alias="Role", description="Selects the CompositionPolicy entry.")
    canvas: Canvas = Field(default=Canvas(), alias="Canvas")
    style: OpenSection = Field(default=OpenSection(), alias="Style")
    subject: Subjects | None = Field(
        default=None,
        alias="Subject",
        description="One subject, or a list with one per cell in reading order.",
    )
    items: list[Item] | None = Field(default=None, alias="Items", min_length=1)
    variants: list[Variant] | None = Field(default=None, alias="Variants", min_length=1)
    output: Output = Field(default=Output(), alias="Output")
    composition: OpenSection = Field(default=OpenSection(), alias="Composition")
    constraints: Constraints = Field(default=Constraints(), alias="Constraints")
    context: OpenSection = Field(default=OpenSection(), alias="Context")

    @field_validator("target")
    @classmethod
    def _background_is_a_colour(cls, value: Target, info: ValidationInfo) -> Target:
        palette = info.data.get("palette")
        if value.background == TRANSPARENT:
            return value
        if palette and find_colour(palette.colours, value.background) is None:
            raise ValueError(f"background '{value.background}' is not a palette colour")
        return value

    @field_validator("subject")
    @classmethod
    def _fits_the_cells(cls, value: Subject | list[Subject] | None, info: ValidationInfo):
        canvas = info.data.get("canvas")
        if isinstance(value, list) and canvas is not None and canvas.cells is not None:
            available = canvas.cells.columns * canvas.cells.rows
            if len(value) > available:
                raise ValueError(f"{len(value)} subjects do not fit in {available} cells")
        return value

    @field_validator("items")
    @classmethod
    def _items_replace_the_subject(cls, value: list[Item] | None, info: ValidationInfo):
        if value is not None:
            if info.data.get("subject") is not None:
                raise ValueError("use Subject for one image or Items for a set, not both")
            _unique_slugs(value)
        return value

    @field_validator("variants")
    @classmethod
    def _variants_need_items(cls, value: list[Variant] | None, info: ValidationInfo):
        if value is not None:
            if info.data.get("items") is None:
                raise ValueError("Variants need Items")
            _unique_slugs(value)
        return value

    @field_validator("output")
    @classmethod
    def _pattern_names_each_image(cls, value: Output, info: ValidationInfo) -> Output:
        if value.pattern is not None:
            check_pattern(value.pattern, with_variants=info.data.get("variants") is not None)
        return value

    @model_validator(mode="after")
    def _has_something_to_draw(self) -> "Spec":
        if self.subject is None and self.items is None:
            raise ValueError("a spec needs Subject (one image) or Items (a set)")
        return self

    def document(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    @property
    def transparent(self) -> bool:
        return self.target.background == TRANSPARENT

    def background(self) -> str:
        """The requested background: "transparent" or the palette colour."""
        if self.transparent:
            return TRANSPARENT
        found = find_colour(self.palette.colours, self.target.background)
        assert found is not None  # The validator guarantees it.
        return found.describe()

    def pattern(self) -> str:
        default = "{slug}-{variant}.png" if self.variants else "{slug}.png"
        return self.output.pattern or default


def check_pattern(pattern: str, *, with_variants: bool) -> None:
    """The pattern must give each image its own .png name."""
    fields = {field for _, field, _, _ in string.Formatter().parse(pattern) if field is not None}
    wanted = {"slug", "variant"} if with_variants else {"slug"}
    if fields != wanted:
        raise ValueError(f"pattern must use exactly {{{'}, {'.join(sorted(wanted))}}}")
    if not pattern.endswith(".png"):
        raise ValueError("pattern must end with .png")


# --- Layers ------------------------------------------------------------------


class SpecError(Exception):
    """A layer or the resolved specification is not usable."""


Origins = dict[tuple[str, ...], str]


def merge(base: dict, layer: dict, source: str, origins: Origins, path=()) -> dict:
    """Merge one layer onto base and record which layer set each key."""
    result = dict(base)
    for key, value in layer.items():
        if key.endswith(APPEND):
            name = key.removesuffix(APPEND)
            result[name] = _appended(result.get(name, []), value, source, path + (key,))
            origins[path + (name,)] = source
        elif isinstance(value, dict):
            earlier = result.get(key)
            earlier = earlier if isinstance(earlier, dict) else {}
            origins[path + (key,)] = source
            result[key] = merge(earlier, value, source, origins, path + (key,))
        else:
            result[key] = value
            origins[path + (key,)] = source
    return result


def _appended(earlier: object, value: object, source: str, path: tuple[str, ...]) -> list:
    if not isinstance(value, list):
        raise SpecError(f"{source}: {_dotted(path)}: the value to append must be a list")
    if not isinstance(earlier, list):
        raise SpecError(f"{source}: {_dotted(path)}: the earlier value is not a list")
    return [*earlier, *value]


def resolve(layers: Sequence[tuple[str, dict]]) -> Spec:
    """Merge the named layers in order and validate the result."""
    merged: dict = {}
    origins: Origins = {}
    for source, layer in layers:
        merged = merge(merged, layer, source, origins)
    merged.pop("Contract", None)
    try:
        return Spec.model_validate(merged)
    except ValidationError as error:
        raise SpecError(_explain(error, origins)) from None


def _explain(error: ValidationError, origins: Origins) -> str:
    lines = []
    for problem in error.errors():
        path = _location(problem["loc"])
        lines.append(f"{_origin(path, origins)}: {_dotted(path)}: {problem['msg']}")
    return "\n".join(lines)


def _location(loc: tuple) -> tuple[str, ...]:
    """The key path, without the subject shape tag that Pydantic adds."""
    parts = tuple(str(part) for part in loc)
    if parts[:1] == ("Subject",) and parts[1:2] in ((ONE_SUBJECT,), (SUBJECT_LIST,)):
        parts = parts[:1] + parts[2:]
    return parts


def _origin(path: tuple[str, ...], origins: Origins) -> str:
    for length in range(len(path), 0, -1):
        if path[:length] in origins:
            return origins[path[:length]]
    return "(no layer)"


def _dotted(path: tuple[str, ...]) -> str:
    return ".".join(path) or "(top level)"


ANCHORED_LISTS = (
    ("ApprovedSamples", "file"),
    ("ApprovedSamples+", "file"),
    ("Items", "reference"),
    ("Items+", "reference"),
)


def anchor_paths(layer: dict, directory: Path) -> dict:
    """The layer with its file paths made relative to the current directory."""
    result = dict(layer)
    if isinstance(result.get("Contract"), str):
        result["Contract"] = os.path.normpath(directory / result["Contract"])
    for key, field in ANCHORED_LISTS:
        if isinstance(result.get(key), list):
            result[key] = [_anchored(entry, field, directory) for entry in result[key]]
    return result


def _anchored(entry: object, field: str, directory: Path) -> object:
    if isinstance(entry, dict) and isinstance(entry.get(field), str):
        return entry | {field: os.path.normpath(directory / entry[field])}
    return entry


def load_layer(path: Path) -> tuple[str, dict]:
    """Read one layer file and name it by its path."""
    try:
        layer = json.loads(path.read_text())
    except OSError as error:
        raise SpecError(f"{path}: cannot read: {error.strerror}") from None
    except json.JSONDecodeError as error:
        raise SpecError(f"{path}: not valid JSON: {error}") from None
    if not isinstance(layer, dict):
        raise SpecError(f"{path}: a layer must be a JSON object")
    return str(path), anchor_paths(layer, path.parent)


class Loaded(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: Spec
    contract: Path | None
    layers: list[Path]


def contract_path(layers: Sequence[tuple[str, dict]]) -> Path | None:
    """The contract that the last layer to name one names."""
    found = None
    for source, layer in layers:
        if "Contract" in layer:
            if not isinstance(layer["Contract"], str):
                raise SpecError(f"{source}: Contract: must be a path to a contract file")
            found = Path(layer["Contract"])
    return found


def load(paths: Sequence[Path]) -> Loaded:
    """The contract, then the layers, merged and validated."""
    layers = [load_layer(path) for path in paths]
    contract = contract_path(layers)
    base = [load_layer(contract)] if contract else []
    return Loaded(spec=resolve(base + layers), contract=contract, layers=list(paths))


# --- Images and prompts ------------------------------------------------------


class PlannedImage(BaseModel):
    """One image to make, with everything its prompt and references need."""

    model_config = ConfigDict(frozen=True)

    path: Path
    slug: str
    variant: str | None = None
    document: dict
    samples: list[Sample]
    subject_references: list[Path]

    @property
    def references(self) -> list[Path]:
        return [sample.file for sample in self.samples] + self.subject_references

    def names(self) -> set[str]:
        return {self.slug, self.path.stem} | ({self.variant} if self.variant else set())


PROMPT_EXCLUDED = ("ApprovedSamples", "Items", "Variants", "Output")


def image_document(spec: Spec, item: Item | None = None, variant: Variant | None = None) -> dict:
    """What the prompt shows for one image: one subject, and only the role's policy."""
    document = spec.document()
    for key in PROMPT_EXCLUDED:
        document.pop(key, None)
    policy = spec.composition_policy.get(spec.role)
    document["CompositionPolicy"] = {spec.role: policy} if policy else {}
    if item is not None:
        document["Subject"] = item.model_dump(
            mode="json", exclude={"slug", "reference"}, exclude_none=True
        )
    if variant is not None:
        document["Variant"] = variant.model_dump(mode="json", exclude={"slug"}, exclude_none=True)
    return _in_order(document)


def _in_order(document: dict) -> dict:
    """Sections in the model's order, Variant after Subject, without empty sections."""
    order = [field.alias for field in Spec.model_fields.values()]
    order.insert(order.index("Subject") + 1, "Variant")
    return {key: document[key] for key in order if document.get(key) not in (None, {}, [])}


def plan_images(spec: Spec, out: Path, references: Sequence[Path] = ()) -> list[PlannedImage]:
    """Each image a spec describes. out is a .png file, or a directory for a set."""
    if spec.items is None:
        if out.suffix.lower() != ".png":
            raise SpecError(f"{out}: a single-image spec needs a .png output file")
        return [_single(spec, out, references)]
    if out.suffix.lower() == ".png":
        raise SpecError(f"{out}: a set spec needs an output directory, not a .png file")
    return [
        _set_image(spec, out, item, variant, references)
        for item in spec.items
        for variant in spec.variants or [None]
    ]


def _single(spec: Spec, out: Path, references: Sequence[Path]) -> PlannedImage:
    return PlannedImage(
        path=out,
        slug=out.stem,
        document=image_document(spec),
        samples=spec.samples,
        subject_references=list(references),
    )


def _set_image(
    spec: Spec, out: Path, item: Item, variant: Variant | None, references: Sequence[Path]
) -> PlannedImage:
    name = spec.pattern().format(slug=item.slug, variant=variant.slug if variant else "")
    return PlannedImage(
        path=out / name,
        slug=item.slug,
        variant=variant.slug if variant else None,
        document=image_document(spec, item, variant),
        samples=spec.samples,
        subject_references=([item.reference] if item.reference else []) + list(references),
    )


def select(images: Sequence[PlannedImage], only: Sequence[str]) -> list[PlannedImage]:
    """The images whose item slug, variant slug or file name is in only."""
    if not only:
        return list(images)
    chosen = [image for image in images if image.names() & set(only)]
    if not chosen:
        raise SpecError(f"--only {' '.join(only)} matches no image in the spec")
    return chosen


def preamble(spec: Spec) -> str:
    target, grid = spec.target, spec.target.grid
    return PREAMBLE.format(
        machine=target.machine,
        mode=target.mode,
        width=grid.width,
        height=grid.height,
        pixel_aspect=f"{target.pixel_aspect:g}",
        count=len(spec.palette.colours),
        colours=", ".join(colour.describe() for colour in spec.palette.colours),
        feature=MINIMUM_FEATURE_PIXELS,
        feature_width=100 * MINIMUM_FEATURE_PIXELS / grid.width,
        feature_height=100 * MINIMUM_FEATURE_PIXELS / grid.height,
    )


def background_rule(spec: Spec) -> str:
    if spec.transparent:
        return TRANSPARENT_BACKGROUND
    return BACKGROUND.format(background=spec.background())


def reference_rules(image: PlannedImage) -> str | None:
    if not image.references:
        return None
    lines = [REFERENCE_INTRO]
    lines += [
        SAMPLE_REFERENCE.format(number=number, use=sample.use)
        for number, sample in enumerate(image.samples, 1)
    ]
    first_subject = len(image.samples) + 1
    lines += [
        SUBJECT_REFERENCE.format(number=number)
        for number in range(first_subject, first_subject + len(image.subject_references))
    ]
    lines.append(REFERENCE_RULE)
    return "\n".join(lines)


def build_prompt(spec: Spec, image: PlannedImage) -> str:
    """The instructions, then a blank line, then the image's JSON specification."""
    head = "\n".join([preamble(spec), background_rule(spec)])
    parts = [head, reference_rules(image), json.dumps(image.document, indent=2)]
    return "\n\n".join(part for part in parts if part)


# --- The image service gateway -----------------------------------------------


class GeneratedImage(BaseModel):
    model_config = ConfigDict(frozen=True)

    png: bytes
    revised_prompt: str | None = None


class ImageServiceError(Exception):
    """The image API refused or failed a request."""


def background_arguments(transparent: bool) -> dict[str, str]:
    """The API arguments that ask for a transparent PNG."""
    return {"background": TRANSPARENT, "output_format": "png"} if transparent else {}


class ImageService:
    """A thin gateway to the OpenAI image API."""

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)

    def generate(
        self, *, model: str, prompt: str, size: str, quality: str, transparent: bool
    ) -> GeneratedImage:
        return self._call(
            self._client.images.generate,
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
            **background_arguments(transparent),
        )

    def edit(
        self,
        *,
        model: str,
        prompt: str,
        size: str,
        quality: str,
        transparent: bool,
        references: Sequence[Path],
    ) -> GeneratedImage:
        with ExitStack() as stack:
            images = [stack.enter_context(path.open("rb")) for path in references]
            return self._call(
                self._client.images.edit,
                model=model,
                image=images,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
                **background_arguments(transparent),
            )

    @staticmethod
    def _call(method: Callable, **arguments: object) -> GeneratedImage:
        try:
            response = method(**arguments)
        except OpenAIError as error:
            raise ImageServiceError(str(error)) from error
        if not response.data or not response.data[0].b64_json:
            raise ImageServiceError("The API returned no image data.")
        image = response.data[0]
        return GeneratedImage(
            png=base64.b64decode(image.b64_json), revised_prompt=image.revised_prompt
        )


# --- Generation --------------------------------------------------------------


class Job(BaseModel):
    """One planned API call, checked before any money is spent."""

    model_config = ConfigDict(frozen=True)

    image: PlannedImage
    prompt: str
    exists: bool


class Batch(BaseModel):
    model_config = ConfigDict(frozen=True)

    loaded: Loaded
    jobs: list[Job]
    model: str
    size: str
    quality: str
    hashes: dict[str, str]

    @property
    def transparent(self) -> bool:
        return self.loaded.spec.transparent

    def to_make(self, force: bool) -> list[Job]:
        return [job for job in self.jobs if force or not job.exists]


def check_job(job: Job) -> None:
    count = len(job.image.references)
    if count > MAXIMUM_REFERENCES:
        raise SpecError(
            f"{job.image.path}: {count} reference images; the API accepts at most "
            f"{MAXIMUM_REFERENCES}. Remove approved samples or references."
        )
    if len(job.prompt) > MAXIMUM_PROMPT:
        raise SpecError(
            f"{job.image.path}: the prompt has {len(job.prompt)} characters; "
            f"the API accepts at most {MAXIMUM_PROMPT}."
        )
    for path in job.image.references:
        if path.suffix.lower() not in REFERENCE_SUFFIXES:
            raise SpecError(f"{path}: a reference image must be PNG, JPEG or WebP")


def hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise SpecError(f"{path}: cannot read the reference image: {error.strerror}") from None


def resolve_model(name: str) -> str:
    """The full model id for an alias such as "sunburst"; other names pass through."""
    return MODELS.get(name, name)


def png_has_alpha(data: bytes) -> bool:
    """Whether the PNG bytes decode to an image with an alpha channel."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            return "A" in image.getbands() or "transparency" in image.info
    except OSError:
        return False


def plan(arguments: argparse.Namespace) -> Batch:
    """Check everything that can be checked before any money is spent."""
    loaded = load(arguments.layers)
    images = select(plan_images(loaded.spec, arguments.out, arguments.reference), arguments.only)
    jobs = [
        Job(image=image, prompt=build_prompt(loaded.spec, image), exists=image.path.exists())
        for image in images
    ]
    for job in jobs:
        check_job(job)
    references = {path for job in jobs for path in job.image.references}
    return Batch(
        loaded=loaded,
        jobs=jobs,
        model=resolve_model(arguments.model),
        size=arguments.size or loaded.spec.canvas.size,
        quality=arguments.quality,
        hashes={str(path): hash_file(path) for path in sorted(references)},
    )


def describe_plan(batch: Batch, force: bool) -> str:
    lines = [
        f"Model: {batch.model}",
        f"Size: {batch.size}",
        f"Quality: {batch.quality}",
        f"Background: {batch.loaded.spec.background()}",
    ]
    for job in batch.jobs:
        state = "skip (exists)" if job.exists and not force else "make"
        lines.append(
            f"{state}: {job.image.path} "
            f"({len(job.prompt)} prompt characters, {len(job.image.references)} references)"
        )
    lines.append(f"Images to make: {len(batch.to_make(force))}")
    return "\n".join(lines)


SPEND_NOTICE = (
    "Nothing was sent. Each image costs money on the owner's OpenAI account. "
    "Ask the owner to agree to the images above, then run the same command again with --spend."
)


def request_image(service: ImageService, batch: Batch, job: Job) -> GeneratedImage:
    common = {
        "model": batch.model,
        "prompt": job.prompt,
        "size": batch.size,
        "quality": batch.quality,
        "transparent": batch.transparent,
    }
    if job.image.references:
        return service.edit(**common, references=job.image.references)
    return service.generate(**common)


def _sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def record(batch: Batch, job: Job, image: GeneratedImage, created: datetime) -> dict:
    """The sidecar that lets anyone regenerate or audit the image."""
    loaded = batch.loaded
    return {
        "created": created.isoformat(),
        "model": batch.model,
        "size": batch.size,
        "quality": batch.quality,
        "background": loaded.spec.background(),
        "has_alpha": png_has_alpha(image.png),
        "contract": str(loaded.contract) if loaded.contract else None,
        "layers": [str(path) for path in loaded.layers],
        "slug": job.image.slug,
        "variant": job.image.variant,
        "references": [
            {"path": str(path), "sha256": batch.hashes[str(path)]} for path in job.image.references
        ],
        "image_sha256": _sha256(image.png),
        "prompt": job.prompt,
        "revised_prompt": image.revised_prompt,
        "spec": loaded.spec.document(),
    }


def manifest_line(batch: Batch, job: Job, image: GeneratedImage, created: datetime) -> dict:
    return {
        "path": str(job.image.path),
        "slug": job.image.slug,
        "variant": job.image.variant,
        "prompt_sha256": _sha256(job.prompt),
        "model": batch.model,
        "size": batch.size,
        "background": batch.loaded.spec.background(),
        "has_alpha": png_has_alpha(image.png),
        "created": created.isoformat(),
        "revised_prompt": image.revised_prompt,
    }


def write_image(batch: Batch, job: Job, image: GeneratedImage, created: datetime) -> None:
    path = job.image.path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image.png)
    sidecar = json.dumps(record(batch, job, image, created), indent=2) + "\n"
    path.with_suffix(".json").write_text(sidecar)
    with (path.parent / MANIFEST).open("a") as manifest:
        manifest.write(json.dumps(manifest_line(batch, job, image, created)) + "\n")


def redact(message: str, secret: str) -> str:
    return message.replace(secret, "[OPENAI_API_KEY]") if secret else message


class Runtime(BaseModel):
    """The boundaries that generate needs, so tests can replace them."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    environ: Mapping[str, str]
    open_service: Callable[[str], ImageService]
    now: Callable[[], datetime]


def default_runtime() -> Runtime:
    return Runtime(environ=os.environ, open_service=ImageService, now=lambda: datetime.now(UTC))


def api_key(environ: Mapping[str, str]) -> str:
    if key := environ.get(KEY_VARIABLE, ""):
        return key
    raise SpecError(
        f"{KEY_VARIABLE} is not set. Set it to the owner's OpenAI API key, then run again."
    )


def generate(arguments: argparse.Namespace, runtime: Runtime) -> int:
    batch = plan(arguments)
    print(describe_plan(batch, arguments.force))
    jobs = batch.to_make(arguments.force)
    if not jobs:
        return 0
    if not arguments.spend:
        print(SPEND_NOTICE)
        return PLANNED
    key = api_key(runtime.environ)
    service = runtime.open_service(key)
    without_alpha = 0
    for job in jobs:
        try:
            image = request_image(service, batch, job)
        except ImageServiceError as error:
            raise SpecError(
                f"{job.image.path}: the image API failed: {redact(str(error), key)}"
            ) from None
        write_image(batch, job, image, runtime.now())
        print(f"Wrote {job.image.path} and {job.image.path.with_suffix('.json')}")
        if batch.transparent and not png_has_alpha(image.png):
            without_alpha += 1
            print(f"FAIL: {job.image.path} has no alpha channel. ", file=sys.stderr, end="")
            print("The spec asked for a transparent background.", file=sys.stderr)
    return 1 if without_alpha else 0


# --- Command line ------------------------------------------------------------


def _add_selection(command: argparse.ArgumentParser) -> None:
    command.add_argument("layers", nargs="+", type=Path, metavar="LAYER.json")
    command.add_argument(
        "--reference",
        action="append",
        default=[],
        type=Path,
        metavar="IMG",
        help="a subject reference image for every image; repeat for more",
    )
    command.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="SLUG",
        help="only images with this item slug, variant slug or file name; repeat for more",
    )


def _add_generate(commands: argparse._SubParsersAction) -> None:
    made = commands.add_parser("generate", help="plan images, or make them with --spend")
    _add_selection(made)
    made.add_argument(
        "--out", required=True, type=Path, help="PATH.png for one image, a directory for a set"
    )
    made.add_argument("--spend", action="store_true", help="call the API; this costs money")
    made.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="sunburst (gpt-image-2.5-sunburst: high quality, the default), "
        "flare (gpt-image-2.5-flare: lower quality, cheaper), or a full model id",
    )
    made.add_argument("--size", help="WxH or auto; default: Canvas.size")
    made.add_argument("--quality", choices=QUALITIES, default="auto")
    made.add_argument("--force", action="store_true", help="replace existing images")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = root.add_subparsers(dest="command", required=True)
    composed = commands.add_parser("compose", help="merge the contract and layers")
    composed.add_argument("layers", nargs="+", type=Path, metavar="LAYER.json")
    composed.add_argument("-o", "--out", type=Path, help="default: standard output")
    prompted = commands.add_parser("prompt", help="print the exact prompts (no API call)")
    _add_selection(prompted)
    _add_generate(commands)
    commands.add_parser("schema", help="print the JSON Schema of a resolved spec")
    return root


def compose(arguments: argparse.Namespace) -> int:
    text = json.dumps(load(arguments.layers).spec.document(), indent=2) + "\n"
    if arguments.out:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(text)
    else:
        print(text, end="")
    return 0


def prompt(arguments: argparse.Namespace) -> int:
    spec = load(arguments.layers).spec
    out = Path("image.png") if spec.items is None else Path(".")
    images = select(plan_images(spec, out, arguments.reference), arguments.only)
    if spec.items is None:
        print(build_prompt(spec, images[0]))
        return 0
    for image in images:
        print(f"=== {image.path} ===\n{build_prompt(spec, image)}\n")
    return 0


def schema() -> int:
    print(json.dumps(Spec.model_json_schema(by_alias=True), indent=2))
    return 0


def main(argv: list[str] | None = None, runtime: Runtime | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        match arguments.command:
            case "compose":
                return compose(arguments)
            case "prompt":
                return prompt(arguments)
            case "generate":
                return generate(arguments, runtime or default_runtime())
            case _:
                return schema()
    except (SpecError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
