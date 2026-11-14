# Prepared RG6 asset loading validation

Question: can the existing original host bundle feed a separate 6809 consumer
without moving target concerns into the converter, and can actual execution
produce every expected framebuffer byte on explicit CoCo 1/2 configurations?

The tracked [experiment](../../../experiments/asset-loading/README.md) answers this
bounded question. It adds an original target consumer and verification runner.
The existing [host validation](assets.md) remains a host-only result;
its converter, source art and production examples are unchanged.

## Directly examined primary sources

This pass rendered and read these local primary-source PDF page images before
writing display setup. Downloads and rendered pages remain ignored. The hashes
below were computed from the files examined in this pass.

- Tandy, [Color Computer Technical Reference Manual][technical], PDF 14
  (printed 7): PIA `$FF22` bit meanings and `$FF23` bit 2 data-register selection.
  PDF 15 (printed 8): SAM F display offset, V display mode, page and CPU-rate
  set/clear strobes. PDF 31 (printed 24): 256×192 uses SAM V=`110` and PIA
  bits 7–4=`1111`, with CSS at bit 3 and low three bits marked do not change.
  SHA-256 `8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64`.
- Don Inman, Kurt Inman with Dymax, [Assembly Language Graphics for the TRS-80
  Color Computer][graphics], PDF 107 (printed 98): eight graphic elements per
  byte, with 0 black and 1 green in color set zero.
  SHA-256 `c1259497b7d1505e6908fd3c8a250d47e0c4b549140e308bdc6bf8e345b6ce01`.
- Motorola, [MC6847 datasheet][vdg], PDF/printed 19, Table 3: RG6 is 256×192,
  requires 6,144 bytes, and orders pixels L7 through L0.
  SHA-256 `2d4586d2fd3c82c60071bbe4cc3930e561c00dce1e43245b0c7ffd5e081fe88c`.
- Tandy, [Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)][service],
  PDF/printed 31: MC6847 video generation, SAM memory addressing and PIA-driven
  mode controls. This supports the non-T1 context, not all CoCo 2 revisions.
  SHA-256 `7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447`.
- Ciaran Anscomb, installed XRoar 1.12.1 manual, machine configuration and
  debugging options, read in `/opt/homebrew/share/info/xroar.info`.
  These describe CPU/VDG selection, RAM initialization and PC trap snapshots;
  timeout is also a trap action. The matching project's [online manual][xroar]
  is the public reference, though this pass read the installed version.

Derived values are a 32-byte scanline (256 / 8), framebuffer `$0400–$1BFF`,
SAM F=2 for a `$0400` origin, and PIA video value `$F0` with CSS0. Display setup
preserves the low three PIA bits and selects normal SAM rate with R0=R1=0.
These are our derivations and implementation choices from the source tables.
The program relies on BASIC firmware initialization; it is not bare-metal startup.

## Original adaptation and provenance

All new assembly and runner code are original to this experiment. The original
pictures come unchanged from `experiments/assets/art.json`: offset-dot floor
ID 10, notched wall ID 40, sparkle ID 70 and right-stroke exit ID 90.
The tested input SHA-256 is
`76f3586af746d5f6cb575ab8368a160c0221aadb192b5885ef79340506c26a71`.
The source room belongs to the repository's original tile-room example.
No historical artwork or listing was copied.

The generated format is our adaptation: labeled eight-byte pictures, a four-word
terrain-pointer table and a 48-byte room. A complete canonical comparison through
`prepare.prepare` checks the existing bundle before the consumer emits data.
The converter's host contract is unchanged. No source claims this table layout
is a historical HGET format or disk loading protocol.

The independent expectation uses manually calculated literal picture bytes and
literal cell coordinates. For example, wall row `10111000` is `$B8`, and the
exit's final row is `$C1`. A separate test expands the literals to pixels and
compares every source pixel. The scene oracle includes all unused screen bytes;
it does not use the host's precomposed framebuffer as the target expectation.

## Executed results

The scoped run on 2026-11-14 used Python 3.13.12, LWTOOLS 4.25 and XRoar 1.12.1.
It passed 35 specs with 93.37% combined statement/branch coverage of the new
`loading.py`. Scoped Ruff lint/format and Markdown fix/check passed.
The full starter suite was not run. The direct CLI check also passed.

Both target runs used `cocous`, NTSC, non-T1 MC6847, 6809, 32 KiB and normal
SAM rate. CoCo 1 used verified BASIC 1.1/Extended BASIC 1.0; CoCo 2 used verified
BASIC 1.2/Extended BASIC 1.1. All launches used null UI/audio, no cartridge and
an empty config file. No GUI was launched. The README records these as explicit
experiment choices, not physical-machine specifications supplied by the owner.

The same valid DECB binary has SHA-256
`075bc66b8bd8384ea6519f9f002d7edb2532d656768e8a3eb7fb86a917c3fb88`.
Its initialized program/data region is 267 bytes at `$3000–$310A`.

| Actual target execution | CoCo 1 | CoCo 2 |
| --- | --- | --- |
| All 6,144 framebuffer bytes | Zero differences | Zero differences |
| Six guards, picture bytes, room cells, completion marker | Pass | Pass |
| Unreachable data trap | No capture | No capture |
| Complemented picture bytes | 384 differences | 384 differences |
| Out-of-bounds store | Guard damaged | Guard damaged |

A separately assembled, valid-but-wrong floor/wall assignment was detected on
CoCo 1. Missing, partial and corrupt firmware fail before launching. A real
unreachable completion trap rejected a stale prior snapshot. Corrupted snapshot
controls caught a truncated RAM dump, missing completion marker, changed final
framebuffer byte, changed art, changed room and damaged asset guard.

Host controls rejected changed asset descriptors/payload, source geometry,
truncated/missing bundles, changed source bytes, screen stride and mappings.
Failed rebuilds removed old generated assembly/binary/symbols; rebuilding after
rejection succeeded. Identical input produced identical binary, symbols and
include across two directories. Reordering source assets retained art identity.
A failed rerun invalidated the prior success report.

The README contains fresh-clone commands. Generated reports, binaries, symbols,
RAM captures, logs, coverage and reference images are ignored under
`build/asset-loading/`; essential logic and instructions are tracked source.

## Limits and integration needs

This establishes headless target execution and framebuffer contents. There was
no rendered-display inspection or physical-machine test. It does not establish
composite colors, display-register effects on a rendered frame, PAL/T1 variants,
CoCo 3, disk `LOADM`, gameplay, sound, concurrency safety or performance.
The target consumes trusted assembled data; corrupted input rejection is on the
host, not a runtime binary parser. No minimum RAM below the tested 32 KiB is claimed.

The parent can link this experiment from the asset guide, technique index and
plan. Those shared files remain outside this worker's edits. The guide should
keep the converter's host-only evidence separate from these new consumer results,
and retain banked storage and general asset-loader work as untested proposals.

[technical]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=14>
[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=31>
[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=107>
[vdg]: <https://people.ece.cornell.edu/land/courses/ece4760/ideas/mc6847.pdf#page=19>
[xroar]: <https://www.6809.org.uk/xroar/doc/xroar.shtml>
