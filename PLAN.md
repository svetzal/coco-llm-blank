# Starter kit plan

## Purpose and boundary

Provide a cloneable repository that prepares local reference material, agent
guidance, and host-side tooling for CoCo development. Own the setup, manifest,
original guidance, and verification. Keep books, converted text, and ROMs in
ignored local storage. Stacey requested public publication as
`svetzal/coco-llm-blank`. Foundry registration remains off.

## Current implementation

- uv owns the Python `.venv`, dependency declarations, and lockfile.
- Docling provides layout analysis, RapidOCR, and table recognition.
- Per-page checkpoints preserve completed work across ranges and interruptions.
- Conversion records preserve source hashes, versions, and PDF provenance.
- Tandy's original CoCo technical manual supplements the graphics and CPU books.
- Figure crops and full-page PNGs are linked from page sections, with image
  checksums and recovery when an image is missing or damaged.
- NumPy and Pillow support reference models, assets, and test vectors.
- pytest and Ruff provide the development checks; pygame-ce and music21 are
  optional dependency groups for interactive and music work.
- Setup selects CoCo 1, 2, or 3 and preserves local project notes.
- `--roms-only` downloads checksum-pinned firmware for the selected target,
  validates selected ZIP members, and stores it outside Git.
- `AGENTS.md` routes tasks through ordinary Markdown files without agent skills.
- Native-tool guidance and discovery cover LWTOOLS, ToolShed, and XRoar.
  Stacey selected assembly only; C compilation is outside the baseline.

## Beginner onboarding priorities

1. Keep the starting prompt short. README now asks only for the repository,
   agent-led setup, and the project idea. AGENTS.md owns the setup procedure.
2. Reduce setup work. `scripts/bootstrap.sh` prepares uv, Python, and project
   notes. The demo check no longer treats optional disk tools as blockers.
   Native tools now install through Homebrew on macOS or verified source builds
   on Ubuntu 24.04. ToolShed and other Linux distributions remain manual.
3. Establish platform evidence. GitHub Actions now defines Ubuntu and Apple
   Silicon macOS jobs for locked setup, specifications, real Docling conversion,
   and project initialization. The initial checks passed on both platforms.
   The native installer and first-screen memory check also passed in a clean
   Ubuntu 24.04 container. Visual and physical-machine checks remain separate.

## Next increments

1. Evaluate Docling output across assembly listings, tables, and diagrams before
   claiming book-wide conversion quality. Preserve explicit page coverage.
2. Add target-specific manuals and datasheets and select resource groups by
   target. The first books are shared 6809 and CoCo 1/2 background, not a
   complete CoCo 3 library.
3. Extend native-tool installation to other Linux distributions and disk tools.
   The original first-screen example now supplies an assembly and emulator baseline.
4. Verify on clean Linux and macOS hosts. The current environment targets
   Apple Silicon macOS and Linux; Intel Mac support needs separate dependency
   compatibility work.
5. Test the beginner prompt with Claude Code in an isolated project.
   Leave Stacey's `coco-lines` project untouched.

## Acceptance evidence

A checkout can create its Python environment from the lockfile, initialize
guidance, verify a downloaded PDF, convert selected pages, and find them through
the index. Reruns preserve project notes and completed pages. Failed conversions
retain successful checkpoints and return nonzero status. Git tracks no reference
content, model weights, or virtual environment.

## Verification status

The co-located pytest specifications pass on the development Mac with combined
statement and branch coverage above the 90% gate. They cover real Docling OCR
of an original image-only PDF, original PDF page provenance for a selected range,
interruption and resume, converter-version cache separation, invalid checkpoint
rejection, download failures, project-note preservation, and native executable
discovery. Ruff checks pass.
The locked environment synchronizes successfully and package compatibility
checks pass. The audit of all locked dependency groups found no known
vulnerabilities. Four newer transitive releases are excluded by current
upstream constraints (huggingface-hub, mpmath, semchunk, and typer). Docling emits
upstream deprecation warnings during conversion.

PDF pages 10 through 12 of both archive books were converted with Docling.
The graphics book now has paragraph structure, headings, and a Markdown table.
Some OCR remains garbled; the 6809 book's contents pages have awkward table
structure. These are useful samples, not evidence of reliable whole-book OCR.
Figure crops and full-page PNGs are now exported. The graphics-book sample's
bit/byte and processor/memory diagrams were visually checked against the full
page; labels are readable. Agents can inspect these PNGs directly. The source
PDF remains available when the rendered images are insufficient.

Graphics-book PDF pages 106–108 and technical-manual pages 30–31 were also
converted and visually checked. The graphics instruction table has merged OCR
cells. The technical manual preserves its mode-table rows but loses two SAM
column labels. Reference guidance identifies these limitations and page ranges.

LWTOOLS and XRoar are discoverable on this Mac. ToolShed's `decb` is not on PATH;
the original project uses an explicit private path that this template does not
inherit. Full-book quality and clean Linux execution remain unverified.

The original first-screen example passes complete framebuffer checks and an
unreachable-checkpoint negative control in XRoar on macOS and Ubuntu 24.04.
The available Mac UI tool could not select the Homebrew executable, so this
session does not claim a visual check.
