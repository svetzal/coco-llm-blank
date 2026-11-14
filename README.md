# coco-llm-blank

A starting repository for agent-assisted Tandy Color Computer projects.
Choose a machine target, build local agent context, and download selected
references directly from the Color Computer Archive. No books or ROMs ship
in this repository.

## Setup

Requires Python 3.10 or newer and Poppler's `pdftotext` on macOS or Linux.
Install Poppler with `brew install poppler` on macOS, or
`sudo apt install poppler-utils` on Debian/Ubuntu.

```sh
python3 scripts/setup.py
```

Setup asks for CoCo 1, CoCo 2, or CoCo 3 and downloads the reference manifest.
For an unattended run, choose the target explicitly:

```sh
python3 scripts/setup.py --target coco2
```

To create local guidance without downloading books:

```sh
python3 scripts/setup.py --target coco3 --guidance-only
```

Use `--list` to see resources or `--resource ID` to download one selection.
Repeat `--resource` for several. Reruns verify and reuse cached PDFs. Existing
project notes are preserved; changing the selected target requires editing
`local/PROJECT.md` deliberately. No system packages are installed by setup.

## Local references

`resources.json` holds titles, source URLs, and SHA-256 checksums. Downloads go
to `local/references/ID/source.pdf`; page-numbered text goes to `text.md`.
`local/INDEX.md` lists each resource and extraction status. PDF page numbers
count from the PDF's first page, not the book's printed numbering.

Text extraction preserves page boundaries but not diagrams or page layout.
Pages with little text are flagged for inspection, not silently called usable
OCR. Both initial books are scans and need OCR to become searchable. Install
Tesseract with `brew install tesseract` or `sudo apt install tesseract-ocr`.
Then use `--ocr`, optionally limiting the first trial to a page range:

```sh
python3 scripts/setup.py --resource assembly-graphics --ocr --pages 10:12
```

Omit `--pages` to process the whole book. Full-book OCR can take considerable
time. A range run leaves other scanned pages unconverted and marks them sparse.
Each explicit OCR run regenerates text from the PDF; range runs replace prior
OCR text, so use the full range for a complete library. Ordinary reruns preserve
existing OCR text. OCR uses Tesseract English at 150 DPI and can misread assembly
code. Check the PDF when text is missing or uncertain.
`local/` is ignored by Git, including derived text.
Archive availability does not change a work's copyright or license.

## Development

```sh
python3 -m unittest discover -s tests -v
```

The setup script uses the Python standard library and the external Poppler
converter. Tests use synthetic PDFs and a local HTTP server; they do not
redistribute reference material or need the archive to be online.

See [PLAN.md](PLAN.md) for the current scope and next increments.
