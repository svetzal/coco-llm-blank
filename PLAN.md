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
  validates selected ZIP members, and stores it outside Git. Bootstrap now
  provisions firmware; doctor and example runners check installed bytes and
  pass explicit ROM paths. See [firmware safeguards](guidance/toolchain.md#firmware-and-launching).
- `AGENTS.md` routes tasks through ordinary Markdown files without agent skills.
- Native-tool guidance and discovery cover LWTOOLS, ToolShed, and XRoar.
  Stacey selected assembly only; C compilation is outside the baseline.

## Beginner onboarding priorities

1. Keep the starting prompt short. README now asks only for the repository,
   agent-led setup, and the project idea. AGENTS.md owns the setup procedure.
2. Reduce setup work. `scripts/bootstrap.sh` prepares uv, Python, and project
   notes, native tools, and checksum-verified firmware. The demo check no longer
   treats optional disk tools as blockers.
   Native tools now install through Homebrew on macOS or verified source builds
   on Ubuntu 24.04. ToolShed and other Linux distributions remain manual.
3. Establish platform evidence. GitHub Actions now defines Ubuntu and Apple
   Silicon macOS jobs for locked setup, specifications, real Docling conversion,
   and project initialization. The initial checks passed on both platforms.
   The native installer and first-screen memory check also passed in a clean
   Ubuntu 24.04 container. The full corrected [Linux onboarding run](guidance/linux-onboarding-validation.md#full-corrected-bootstrap-validation)
   now passes in a fresh Ubuntu 24.04 ARM64 root container without manually
   installed prerequisites: bootstrap took 796.40 seconds, all 13 CoCo 2
   moving-object frames passed, and a 1.06-second rerun preserved edited notes.
   These are measured run times, not guarantees. Native desktop, x86-64,
   and GUI onboarding remain unverified by this run. A separate
   [nonroot sudo run](guidance/linux-onboarding-validation.md#nonroot-sudo-validation)
   passed bootstrap, all 13 CoCo 2 frames and note preservation. Its no-sudo
   control failed actionably. Separate [sudo-policy validation](guidance/sudo-policy-validation.md)
   covers denied/password-required failures and prerequisite-only recovery.
   Neither run supplies visual, audible or physical-machine evidence.

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

The [technique index](guides/README.md) records current evidence by task.
Opaque, masked and tile-room examples have bounded CoCo 1/2 framebuffer checks.
Static renderer geometry is measured on CoCo 1 and an explicit NTSC, 32 KiB,
normal-clock, non-T1 CoCo 2. The [CoCo 2 display record](guidance/display-coco2-validation.md)
reports 12 positive cases at 0.5 and 1.0 seconds of settling, plus a wrong-SAM
control. This is stationary output, not animation or physical-display evidence.
Sound experiments cover CoCo 1/3 execution and DAC intervals; CoCo 2 sound
runtime coverage remains open.

[Controls and collision validation](guidance/controls-collision-validation.md)
reports 26 host cases for bounded logical-input and collision policies. It
supplies no keyboard-driver, 6809 execution, timing or hardware evidence.
[Game-state validation](guidance/game-state-validation.md) now reports 60 host
cases for bounded commands, journeys, phases and menu transitions, without
CoCo execution. [Selective redraw](guidance/selective-redraw-validation.md)
passes 12 checkpoints for each selective and full-region build on explicit
NTSC CoCo 3 configurations at 128 and 512 KiB. It checks two bounded RAM
windows and failure controls, not rendered output or speed.
[Asset validation](guidance/asset-validation.md) reports 33 host cases for
original RG6 packing, scene composition and publication.
[Asset guidance](guides/assets.md) distinguishes that adaptation from its
[examined CoCo 3 community sources](guidance/community-game-research.md).
Target asset loading, banked storage, compression and animation cadence remain
unverified.

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
At the end of this first batch, no new game technique had been reproduced
or benchmarked. Shared CoCo 1/2 articles
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
Per-sample jitter was not measured in this pass; the later
[DAC interval validation](guidance/audio-timing-validation.md) supplies bounded
measurements. Audible quality, bank switching, analog input, and physical
GIME timing remain unverified. Lower sample rates and leaner handlers are
possible follow-up experiments, not measured improvements.

### Rendering and collision pass

Added [moving-object guidance](guides/moving-objects.md) from examined assembly
and BASIC sources. The graphics book supplies shape storage, placement bounds,
and rectangle erasure. The guide explains why that erasure does not restore
scenery and marks save/restore and redraw designs as our untested proposals.

The October 1992 Rainbow issue adds a trail game's use of screen values for
collision and precomputed rotation coordinates for animation. Added the issue
to the manifest with its download hash. Converted PDF 3 and 10 and checked
exported images. Also converted graphics-book PDF 159–164.
Dense listing OCR remains unreliable despite no sparse warnings.
The animation guide separates its proposed packed format from BASIC arrays.

Sampled Undercolor's first contents page and mapped Color Computer Magazine's
directory. Neither counts as examined technical coverage. Tile maps, masked
rendering, and a reproduced multi-object example were still open at this stage;
the later passes below record the completed work. CoCo 1/2 adaptation
notes in a magazine do not establish runtime support. No new emulator or
physical-machine result is claimed for this pass.

### Parallel source and implementation validation

Completed Matthews's October 1987 listing through PDF 47 and examined the
MC6847/MC6847Y technical datasheet. Its RG6 tables resolve the chip's bit order.
Board wiring and visible output still need separate checks. The generic
non-SAM memory-access discussion must not become a CoCo screen-write restriction.

Read Blochowiak's January 1988 SMOOTHY article and its April 1988 correction.
It concerns CoCo 3 text scrolling, with distinct 128K and 512K requirements.
The GIME cross-check is complete: Tandy PDF 13 and Tepolt PDF 29, 33, and 58
explain the physical-address fields and 128K alias behind the 512K correction.
The scrolling guide labels the address calculation as our cross-source explanation.
An original display-address probe now checks all eight address/RAM-size cases
at an instrumented XRoar 1.12.1 GIME fetch boundary. Each produced 40 matching
reads and a ready snapshot; the unreachable-trap control produced no snapshot.
The separate emulator build and diagnostic are documented in
[the experiment](examples/text-addressing/README.md). No global executable changed.
SMOOTHY, rendered appearance, timing, firmware compatibility, and physical
hardware remain unverified.
The datasheet and paired article/correction are now checksum-pinned resources.
Converted MC6847 PDF 19–22, January PDF 80/82, April PDF 14, and Matthews PDF 47.
Exported images were checked. Sideways tables and dense listings still need
image-first reading. Sixty-one setup/reference specifications pass.
October pages 44/46 were read as source images but remain outside the active
converter profile. Their older checkpoints do not establish current Markdown coverage.

The original [moving-object example](examples/moving-objects/README.md) implements
full background redraw and ordered opaque objects. Thirteen frame checks pass
on each defined non-T1 CoCo 1 and CoCo 2 configuration. They cover overlap,
separation, changed scenery, complete-object bounds, and memory guards.
A separate static review found the CI firmware-provisioning gap for CoCo 2;
CI now provisions CoCo 2 alongside CoCo 3 before running pytest.
The full suite passes: 133 tests with 93.99% combined coverage. Ruff checks pass.
That pass did not verify visual output, timing, masks, clipping, or physical
hardware. Later masking and static-renderer checks are recorded below.

The independent Claude Code beginner trial, Claude 02, is assessed in the
[external evaluation record](/Users/svetzal/Work/Experiments/coco-starter-onboarding/claude-02-evaluation.json).
Observed primary-text and diagram reads preceded implementation. Independent
build and framebuffer checks passed on explicit CoCo 2 configurations at
32/64 KiB, including 30 fresh snapshots. The trial's full gate failed at
83.32% coverage (151 passed, three skipped); visual and physical evidence
remain incomplete. The assessment also records configuration-provenance,
partial-firmware recovery, launcher-argument and board-citation weaknesses.
These findings do not negate the narrower runtime result or establish Linux
onboarding. The trial received no implementation coaching.

### Masking, tile reading, display and audio follow-up

The original [masked-object example](examples/masked-objects/README.md) passed
12 scenes on each explicit NTSC, 32 KiB, normal-clock, non-T1 CoCo 1 and CoCo 2
configuration. Checks cover transparency versus opaque black, overlap in both
orders, removal, changed scenery, full framebuffer bytes and guards. This is
bounded full redraw, not clipping, collision, calibrated animation or a physical
hardware result.

The [tile-map guide](guides/tile-maps.md) now distills the examined PacDude
CoCo 3 map, drawing and movement paths. The complete Barden maze article and
both listings are read in [legacy tile research](guidance/legacy-tile-research.md).
That legacy BASIC source supplies room graphs and model-driven perspective
redraw, not bitmap tiles or sprite restoration. The historical CoCo 1/2
bitmap tile-ID renderer source gap remains open. The original tile-room
implementation below supplies separate evidence; it does not close that gap.

[Display validation](guidance/display-validation.md) measured five positive
static CoCo 1 renderer cases, including three frozen moving-object frames.
Every rendered sample matched; a wrong-SAM control exposed a display error
despite matching RAM. This establishes static geometry only in the named
software-renderer configuration, not CoCo 2/3 output, animation, tearing,
composite appearance or physical display behaviour.

[Audio timing validation](guidance/audio-timing-validation.md) measured eleven
cases, including calibration, deferred-interrupt and repeatability controls.
Timer DAC intervals have a nonzero observed spread despite stable average
throughput. These are finite-window emulator measurements, not worst-case
bounds, physical GIME timing or listening evidence.

Both private experiments now have tracked reproduction code and instructions
for a fresh clone. Display results reproduced with the retained package; all
eleven audio results matched in an empty-output run using the existing checkout,
environment and verified firmware. This is not evidence of a newly provisioned
clone or completed Linux onboarding.

### Published source and tile-room follow-up

The original [tile-room example](examples/tile-room/README.md#evidence-and-limits)
passes all 42 checkpoints on each defined CoCo 1 and CoCo 2 configuration.
It checks map persistence after collection and return, blocked movement,
actor state, full framebuffer bytes and guards. The runner enforces NTSC and
excludes user configuration. This is a 32 KiB, normal-clock, non-T1 emulator
result, not a historical reproduction, visual check or physical-hardware test.

[Hot CoCo research](guidance/hot-coco-game-research.md) now supplies examined
collision, control and foreground-coverage articles.
[Undercolor research](guidance/undercolor-game-research.md) adds selected
turn-state, single-switch menu and small-animation sources.
[CoCo 3 source research](guidance/coco3-game-source-research.md) examines Gloom
and Symmetry; [expanded legacy research](guidance/legacy-tile-research.md#three-game-source-candidates)
assesses Droid War, Dunkey Munkey and Sea Quest. Useful findings are linked
through the technique guides. These source-only passes did not run the historical
programs or validate the proposed adaptations. They broaden selected coverage;
the archive survey remains incomplete.
The [bounded tile-source follow-up](guidance/tile-source-followup.md) inspected
three further packages, then Rat Maze and its bounded correction leads. None
established the required CoCo 1/2 grid-to-tile-ID bitmap renderer. Rat Maze
supplies passage topology and procedural walls instead. The historical source
gap remains unresolved, but this hunt is stopped pending a substantive new
lead identifying a plausible legacy bitmap tile-ID drawing chain. No further
candidate search is queued. This does not establish an archive-wide absence.

The published [Color Computer Magazine research](guidance/color-computer-magazine-research.md)
examines four articles across March through June 1983: Field of Honor,
The Sorcerer's Puzzles, and both parts of Color Animation. It also records
Ramella's June correction. The [game-loop guide](guides/game-loop.md) now
explains preparation, playback and return-to-play contracts. Its original
pseudocode remains untested; these readings establish neither later-machine
compatibility nor measured responsiveness.

[Conversion-quality inspection](guidance/conversion-quality.md) now covers six
difficult pages and all eleven exported images. Tables, diagrams and listing
images remain useful where OCR merges rows or columns and damages code.
This bounded inspection does not establish book-wide accuracy or change the
shared Matthews conversion coverage.

### Next research passes

1. Continue beyond the published Hot CoCo, Undercolor, CoCoNutz and four
   Color Computer Magazine article readings when a specific technique warrants
   another source. Follow unresolved errata and sample early and late periods
   for each machine; selected readings do not complete publication coverage.
2. Investigate sound alongside animation and controls. Distinguish the stock
   DAC, one-bit output, cassette audio, and expansion hardware. Check timing
   costs and interference with input rather than assuming simultaneous playback.
3. Keep the historical CoCo 1/2 bitmap tile-ID source hunt stopped unless a
   substantive new lead meets the boundary above. Use published full-redraw
   examples as correctness baselines for implementation work. The bounded
   CoCo 3 selective-redraw RAM result does not establish displayed restoration,
   scrolling or cross-target memory and frame-time comparisons.
4. Inspect published game/demo source and companion magazine disks. Record
   licenses separately from archive availability. Do not redistribute code or
   assets merely because they are downloadable.
5. Extend the host controls model with a target-specific input adapter and
   execution checks. Extend host game-state evidence to target execution, and
   validate animation and asset integration with small original examples. Keep
   CoCo 3 implementation evidence alongside CoCo 1/2 work before claiming broad
   coverage.

Each pass should produce a few examined references and their usable guide text.
Update existing guides when a finding changes their advice. Review topic and
machine gaps after every pass.

### Current dispatched batch: in progress

The entries below distinguish completed work from contracts still in progress
or independent review. A future worker file or reported test count alone is not
evidence; integration follows review of the delivered record and checks.

- Keyboard input. Declare one target and scan policy; check press, hold,
  release, repress and simultaneous-key handling through the actual adapter,
  including rejection and return to play. Logical host events alone do not
  establish keyboard scanning, physical debounce or all-model support.
- Target assets. Consume the published host converter's original output on an
  explicitly configured target; compare placement, packed bytes and guards with
  independent expectations and a damaged-input/output control. The 33 host
  cases do not establish target loading, banked storage or compression.
- CoCo 3 state subset. Declare the implemented subset, integer bounds and RAM
  layout; check accepted transitions, unchanged state on rejection, slot reuse
  and phase order against independent vectors. The 60 host cases remain
  separate; a subset cannot validate the whole host model, display or input.
- CoCo 2 sound. Declare the CoCo 2 profile, firmware and clock; check a bounded
  DAC sequence with foreground progress and a meaningful failure control. CoCo
  1/3 results do not transfer; execution does not establish listening quality
  or worst-case timing.
- Animation cadence. Declare sequence, dwell units, timing source and wrap
  policy; measure a finite sequence including return/repeat and delayed work,
  with an incorrect-cadence control. Static frames do not establish cadence;
  finite-window timing is not physical-display or worst-case evidence.
- Input source crosscheck (completed). [Primary manual findings](guidance/input-hardware-research.md)
  record 18 examined pages, matrix coordinates, board distinctions and unresolved
  conflicts. Source interpretation alone is not an executed
  keyboard driver or a claim of archive-wide errata coverage.
- Denied sudo (completed, prerequisite scope). [Validation](guidance/sudo-policy-validation.md)
  covers password-required and denied policies, followed by administrator
  correction and real curl/CA/HTTPS recovery. The original contract was to
  exercise present-but-denied noninteractive sudo as an ordinary
  user in an isolated Ubuntu case; require nonzero exit, actionable diagnostics
  and no false readiness. The published missing-sudo control is different;
  neither case proves interactive password handling or native desktop
  onboarding.

Retain original code and reproduction instructions in Git; keep downloads and
generated evidence ignored. Before any worker emulator run, verify ROM bytes
and declare an isolated machine configuration. Report assembly, execution,
framebuffer, rendered output, audio and hardware evidence separately. This
plan/index update performs no runtime work and adds no runtime result.

## Next increments

1. Use the six-page conversion-quality findings when selecting further difficult
   pages. Preserve explicit coverage and image checks; book-wide quality remains
   unverified.
2. Add target-specific manuals and datasheets and select resource groups by
   target. The first books are shared 6809 and CoCo 1/2 background, not a
   complete CoCo 3 library.
3. Extend native-tool installation to other Linux distributions and disk tools.
   The original first-screen example now supplies an assembly and emulator baseline.
4. Extend host evidence beyond completed Ubuntu ARM64 root and passwordless-sudo
   container runs to native desktop, complete bootstrap after restricted-sudo
   recovery, GUI journeys and clean macOS onboarding.
   x86-64 Linux and Intel Mac compatibility need separate checks.
5. Extend beginner trials after addressing observed failures. The first Claude
   Code trial built a demo and passed runtime checks; Claude 02 now has an
   independent assessment above. Visual evidence remains incomplete.
   Leave Stacey's `coco-lines` project untouched.

## Acceptance evidence

A checkout can create its Python environment from the lockfile, initialize
guidance, verify a downloaded PDF, convert selected pages, and find them through
the index. Reruns preserve project notes and completed pages. Failed conversions
retain successful checkpoints and return nonzero status. Git tracks no reference
content, model weights, or virtual environment.

## Verification status

The published independent full-suite run on the development Mac passed
239 tests with 95.28% combined statement and branch coverage. That run preceded
two configuration regression tests; it does not establish a full-suite result
for the later test set. The tile-room example records its separate scoped run.
The co-located specifications cover real Docling OCR
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
