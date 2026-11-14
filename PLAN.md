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

## Game and demo research

Stacey requested a methodical archive survey, with equal attention to CoCo 1,
CoCo 2, and CoCo 3. No preferred games or genres define the selection.
[Research notes](guidance/game-research.md) hold findings and source judgements.
[Permanent technique guides](guides/README.md) turn examined findings into practical
guidance. Update these living documents as research proceeds.

### Method

1. Map books, magazine indexes, manuals, datasheets, and published source.
   Use colorcomputerarchive.com as the primary collection.
2. Search by technique and synonyms. Include animation, scrolling, collision,
   controls, audio, timing, memory, asset formats, and game-state design.
3. Download promising sources into ignored local storage. Record the exact
   archive URL, SHA-256, edition or issue, and PDF page count.
4. Read the actual section, including figures, listings, and continuation pages.
   Check magazine corrections. A contents entry remains a discovery lead.
5. Record machine, RAM, video standard, display path, language, and dependencies
   where the source establishes them. Mark missing details as unresolved.
6. Select sources that explain a reusable technique, expose a useful tradeoff,
   or resolve a hardware question. Keep reasons for exclusions and narrower uses.
7. Add selected sources to the manifest and page-level navigation guide.
   Test selected-page conversion. Check difficult output against page images.
8. Write or update a task-focused technique guide for each selected useful finding.
   Cite claims at the relevant passage. Label adaptations and proposed checks.
9. Reproduce a small example before presenting an implementation as tested.
   Record build, runtime, visual, audible, and hardware evidence separately.
   Update the guide with the result, configuration, and limits.

For each technique, distinguish **discovered**, **examined**, and **reproduced**.
Examined means the relevant source was read; it does not mean its code works.
Do not rank by nostalgia, impressive titles, or the number of pages collected.
A BASIC tutorial can explain an algorithm without being a usable assembly driver.

### Permanent technique guides

The repository has three connected layers. Research notes preserve source
selection and uncertainty. Guides explain how to use the findings. Original
examples supply bounded implementation evidence. A source list alone does not
complete a research pass.

Keep guides under `guides/`, with one index organized by the effect a builder
wants. AGENTS.md routes agents to that index and then to the relevant guide.
The beginner README links the collection without making it required reading.
Guides use ordinary Markdown and need no agent-specific skill loader.

Each guide must include:

- The task, applicable machines, and known configuration limits.
- Practical steps, memory or timing tradeoffs, and likely failure cases.
- Citations beside sourced claims, naming the author, title, edition or issue,
  exact PDF pages, printed pages when known, archive URL, and resource ID.
- Clear attribution for published explanations, our adaptations, derived
  calculations, measured results, and untested proposals.
- Links to original examples and their checks when implementation evidence exists.
- Unresolved conflicts and the evidence needed to settle them.

Credit an examined author without claiming they invented the technique.
Do not cite unread continuation pages as support. Check diagrams and listings
against images when conversion is uncertain. Keep copyrighted source content
in ignored local storage; publish our explanations and source metadata only.

A guide can document an examined technique before reproduction, provided its
procedures remain labelled proposals. Only measured claims gain tested status.
Emulator memory, visible output, audible output, and physical hardware remain
separate evidence. Compatibility needs a test on each claimed target.

The first guides now cover animation storage, prepared pictures, CoCo 3
scrolling and mapping, display-dependent colours, and sound scheduling.
Graphics procedures remain proposals. Sound guides link original CoCo 1 and
CoCo 3 emulator experiments. CoCo 2 runtime coverage remains incomplete.

For each later pass, update the relevant guide and navigation before calling
the pass complete. Check citations, relative links, Markdown, and runnable
commands. Re-run example checks when their code or contract changes.

### First batch

Archive directories mapped: books, magazines, articles, hardware manuals,
datasheets, and programming source. Nine PDFs downloaded locally: two books,
two service manuals, a datasheet, a magazine index, and three Rainbow issues.
Six selected sources added to the manifest. Others remain optional background,
rejected matches, or unexamined candidates in the research guide.

Examined topics include compact object storage, prepared-frame animation,
CoCo 2 artifact circuitry, CoCo 3 scrolling, palette interpretation, and
interrupt visibility during memory remapping. Thirteen selected pages were
converted. A nearly blank render affected CoCo 3 manual pages 16–18.
The converter now retries through Docling's PDFium backend when an independent
render shows detail. The repaired page-17 image was checked. Profile 3 prevents
reuse of the old blank checkpoints. OCR still needs image checks: palette row
labels can merge, and Tepolt page 59 has damaged text without a sparse flag.
No new game technique is reproduced or benchmarked yet. Shared CoCo 1/2 articles
need separate compatibility checks. The specific CoCo 2 service manual does
not establish every board revision.

### Sound research pass

Examined sound/input hardware in the CoCo 1 technical manual, the named CoCo 2
NTSC service manual, and the CoCo 3 service manual. Read the six-voice Rainbow
player and sampled Hot CoCo's Sound/Speech cartridge review. Added these two
issues to the download manifest. The [sound guide](guidance/sound-research.md)
records exact pages, narrower uses, source inconsistencies, and untested claims.
Converted Rainbow PDF 77–78 and Hot CoCo PDF 75. Their exported page images
retain the source content; listing OCR still needs comparison with those images.

An original CoCo 1 experiment interleaves DAC samples, marker movement, and
fire-button reads. XRoar checks exact sample sequences, framebuffer contents,
press/hold/release fixtures, and an unreachable checkpoint. Its ordinary sample
gap is 11 instructions; frame work increases that to 30. A separate one-second
run completes 60 marker updates and bounds throughput at 15,360–15,616 samples.
This establishes cooperative progress, not constant timing or audible quality.
The fixture is not physical-input evidence. CoCo 2 runtime reproduction and
physical/display/audio checks remain open.
The following pass adds CoCo 3 timer evidence.

### CoCo 3 timer comparison

Read Tepolt's interrupt chapter and checked its vector, acknowledgement, and
mapping details against the CoCo 3 service manual. Converted PDF 48–53.
Found a timer-clock discrepancy: the older books describe about 14 MHz;
Kowalski's later reference and XRoar use about 3.58 MHz. The sound guide records
this conflict and the GIME revision offsets explicitly.

The original timer/cooperative comparison runs on the same slow-clock CoCo 3.
Both emulated GIME revisions retain their predicted audio throughput during a
full framebuffer clear. Foreground redraws fall from 27 to 2 per measured second.
The cooperative comparison loses most of its audio throughput under that load.
All DAC values and completed-frame memory are checked. A missing-acknowledgement
negative control fails as expected. CI now provisions CoCo 3 firmware without
changing its existing project target, so these checks do not silently skip.

This establishes a tested scheduling choice, not a maximum performance claim.
Per-sample jitter, audible quality, bank switching, analog input, and physical
GIME timing remain unverified. Lower sample rates and leaner handlers are
possible follow-up experiments, not measured improvements.

### Next research passes

1. Broaden magazine coverage to Hot CoCo, Color Computer Magazine, Undercolor,
   and later community publications. Read original articles and their errata,
   not only Rainbow's index. Sample early and late periods for each machine.
2. Investigate sound alongside animation and controls. Distinguish the stock
   DAC, one-bit output, cassette audio, and expansion hardware. Check timing
   costs and interference with input rather than assuming simultaneous playback.
3. Examine reusable rendering and game techniques: masked objects, background
   restoration, collision, tile maps, scrolling, text/adventure state, and
   deterministic movement. Compare memory and frame-time costs on each target.
4. Inspect published game/demo source and companion magazine disks. Record
   licenses separately from archive availability. Do not redistribute code or
   assets merely because they are downloadable.
5. Reproduce selected small techniques with original implementations and tests.
   Choose examples across all three machines before claiming broad coverage.

Each pass should produce a few examined references and their usable guide text.
Update existing guides when a finding changes their advice. Review topic and
machine gaps after every pass.

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
5. Extend beginner trials after addressing observed failures. The first Claude
   Code trial built a demo and passed runtime checks; visual evidence is incomplete.
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
inherit. Full-book conversion quality remains unverified.

The original first-screen example passes complete framebuffer checks and an
unreachable-checkpoint negative control in XRoar on macOS and Ubuntu 24.04.
The available Mac UI tool could not select the Homebrew executable, so this
session does not claim a visual check.
