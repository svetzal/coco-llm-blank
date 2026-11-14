# Starter kit plan

## Purpose and boundary

Provide a cloneable repository that prepares local reference material and
agent guidance for CoCo development. Own the setup, manifest, original
guidance, and verification. Download reference works from their source into
ignored local storage. Do not bundle books, derived book text, or ROMs.

## First increment

- Support macOS and Linux with Python and Poppler.
- Let the user choose CoCo 1, CoCo 2, or CoCo 3 during setup.
- Generate local project notes without overwriting user changes.
- Fetch a small explicit manifest, validate checksums, and reuse downloads.
- Extract text with PDF page boundaries and flag sparse pages.
- Offer OCR with an optional page range for a small initial trial.
- Produce a local source index for agents.
- Test downloads, extraction, reruns, and failure behavior.

The repository stays local and unregistered with Foundry at Stacey's request.

## Next increments

1. Make OCR resumable per page and evaluate scan quality on assembly listings.
   The first version supports explicit full-book or bounded-range OCR.
2. Add target-specific manuals and datasheets, then select resource groups
   by target. The first collection is shared 6809 and CoCo 1/2 background;
   it is not a complete CoCo 3 reference library.
3. Add a toolchain check for LWTOOLS and XRoar, explicit ROM configuration,
   and an original small program with an emulator smoke test.
4. Verify setup on a clean Linux host and a clean macOS host before claiming
   cross-platform validation. Current local execution is on macOS.
5. Prepare public-template metadata and licensing when publication is wanted.

## Acceptance evidence

A fresh checkout can initialize guidance, obtain a checksum-verified PDF,
convert its text, and locate it through the index. A second run preserves
project notes and reuses downloads. Failed downloads and conversion return
nonzero status without replacing valid output. Git tracks no downloaded or
derived reference content.

## Current verification

Nine tests pass on the development Mac, including real HTTP download behavior,
Poppler conversion, Tesseract OCR, preserved project notes and OCR text,
checksum rejection, and failed conversion output preservation.

Both manifest PDFs were downloaded from the archive and checksum-verified.
Both are image-only scans. PDF pages 10 through 12 of each were processed with
Tesseract and produced text. The rest still need OCR. Downloaded PDFs,
extracted text, metadata, and the local index are ignored by Git.

Linux execution and full-book OCR have not been verified.
