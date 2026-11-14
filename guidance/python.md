# Python support tools

Load this file when writing host-side scripts, asset converters, reference
implementations, or tests. Run commands from the repository root.

## Environment

Use `uv sync --locked` to create `.venv` from `uv.lock`. Use `uv run` for scripts
and checks. Do not install into system Python or maintain a second requirements
file. Declare a dependency with `uv add`; commit `pyproject.toml` and `uv.lock`
together. Python 3.13 is selected in `.python-version`.

The baseline has Docling and RapidOCR for documents, NumPy for numeric reference
models and test vectors, and Pillow for image conversion and previews.
Development tools are pytest and Ruff. Optional groups provide pygame-ce for
interactive prototypes and music21 for music analysis:

```sh
uv sync --locked --group interactive --group music
uv run --group interactive python path/to/prototype.py
uv run --group music python path/to/music_tool.py
```

Without these flags, later `uv run` commands can remove optional packages while
synchronizing the environment. Keep the group flag on commands that use them.

## What Python does here

The original `coco-llm` used Python for fixed-point reference models, exact test
vectors, waveforms and WAV output, palette and sprite packing, bitmap fonts,
RS-DOS disk images, and XRoar test/capture orchestration. Those are useful
patterns for future projects. Their game and language-model implementations
are not part of this blank starter.

Keep pure transformations separate from file and process I/O. Test packed
bytes and numeric outputs, not only rendered previews. Use `pathlib`, `struct`,
`wave`, and `subprocess` from the standard library where they fit. Put generated
assets in `build/` and reference implementations in `src/reference/` when needed.

Run `uv run pytest -m 'not integration'`, `uv run ruff check .`, and
`uv run ruff format --check .` after changes. For document conversion changes,
also run `uv run pytest -m integration`; this loads real Docling models.

For CoCo binaries and emulator checks, load [toolchain.md](toolchain.md).
For books and OCR, load [references.md](references.md).
