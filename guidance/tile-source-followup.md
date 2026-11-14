# Follow-up search for a legacy bitmap tile renderer

Read this when deciding whether another archive source closes the historical
CoCo 1/2 tile-rendering gap. This bounded pass does not close it. Three new
packages were inspected on 2026-11-14; none establishes the complete chain
`grid cell -> tile ID -> packed image -> bitmap destination` on CoCo 1/2.
This is a negative finding about these packages, not about the whole archive.

The prior [tile research](tile-map-research.md),
[legacy research](legacy-tile-research.md) and
[tile guide](../guides/tile-maps.md) were read first. Droid War, Dunkey Munkey,
Sea Search, Barden, PacDude and Ice Hockey were not investigated again.
The existing original tile-room example remains separate implementation
evidence; it cannot establish a historical source's design or compatibility.

## Selection and stopping rule

The [source directory][directory] supplied three discovery leads. Their names
were not evidence of their implementation. The three-package budget includes
selection failures; rejected candidates were not replaced to extend the hunt.

| Package | Examined representation | Disposition |
| --- | --- | --- |
| Cubix | 6809 operating system | Discovery miss |
| Space Raiders | CoCo III object list | Wrong target and map format |
| Calixto Island | Background IDs and overlays | No tile-ID grid |

Only Calixto remained a plausible legacy graphics source after inspection.
Do not describe this as three verified CoCo 1/2 games. The general archive
index request timed out in the web tool. Direct HTTPS directory and ZIP
requests succeeded; there was no retry loop or archive-wide crawl.

## Citation convention

All source citations below count physical lines, including blank lines, after
CRLF and lone CR become LF. Paths are ZIP member names, except Space Raiders,
whose `.TXT` files are inside `SR3.DSK`. These are plain-text source readings,
not OCR or PDF citations. Named ranges were read directly. No complete-game
audit, build, execution, timing, framebuffer, visual or hardware test occurred.

## Cubix: reject the discovery assumption

Dave Dunfield's [Cubix package][cubix], `DOCS/READ.ME` lines 1-24, identifies
version 1.3 as a ROM-based disk operating system for the 6809, with a porting
workflow. `SRC/CUBIX_OS/CUBIX.ASM` lines 1-24 independently identifies the OS,
credits Dunfield, gives a 1983-1994 copyright range, and separates distribution
and demonstration memory configurations. The archive includes editors,
assemblers and language tools. It supplies no basis for the initial game
association. No tile technique is attributed to it and no OS call chain was
traced as if it were a game renderer.

`DOCS/READ.ME` also contains freeware/commercial-redistribution restrictions.
That is not an unrestricted code license. Nothing from the package is copied
into tracked source.

## Space Raiders: a formation is not a tile map

John Crawford's [Space Raiders package][raiders] contains `SR3.DSK`.
`SR3.TXT` lines 1-8 explicitly says CoCo III and records June 21, 1987 as
its last modification. Lines 57-89 set palette registers and a legacy-style
display path. A familiar bitmap stride cannot override that declared target
or prove that the whole program runs on CoCo 1/2.

The examined call chain and data explain why a rectangular formation is
insufficient evidence for a tile grid:

1. `SR3.TXT` lines 122-132 calls `INMAN`. Lines 657-736 initialize five groups
   of eight objects in `SMLOC`. Each eight-byte record has current coordinates,
   saved coordinates, a shape pointer and two state bytes. Positions advance
   by 12 horizontally; each group starts at a different vertical position.
2. `MAIN` and `PUTSHP`, lines 134-208, reach `PMAN`. `PMAN`, 738-759, walks
   records, skips an inactive object, selects its shape pointer or the frame
   18 bytes later, and passes that object's coordinates to `MASK`.
3. `SRFILES.TXT` lines 309-352, `MASK`, reads width and height, consumes packed
   shape bytes, combines shifted data with destination bytes through masks,
   and advances the destination by 32 down each column. After a column it
   restores the starting position and moves right by one byte. The source
   data is therefore column-major, not consecutive horizontal image rows.
4. `SR3.TXT` lines 1002-1011 contains the paired shape records. A width of two
   and height of eight gives 16 payload bytes plus the two-byte header,
   explaining the 18-byte alternate-frame offset. This is source arithmetic,
   not a measured rendering result.

`MVSM`, `SR3.TXT` 460-497, mutates object coordinates and animation state.
This is an object list arranged initially in rows, not cell IDs selecting
terrain from an atlas. `SR3.TXT` 1150-1152 includes `SRFILES`, `FIRESR3` and
`SRC3`; the separately present `SRF1.TXT` is not the included firing module.
Do not use that older-looking companion as evidence of the assembled path.
No reuse license or older CoCo 1/2 revision was established.

## Calixto Island: scene records and packed-byte production

The [Calixto Island package][calixto], `ADVENT.ASM` 358-379, credits Bob
Withers and Stephen O'Dea, with a 1981 Mark Data Products copyright notice.
`ADVENT.ASM` 1-9 defines `GSCRN` at `$0400`, eight overlay slots and 26 rooms.
Its initialization at 216-253 configures the legacy display path and clears
6,144 bytes. These are source facts, not a tested RAM minimum, ROM contract,
PAL/NTSC claim or model-by-model compatibility result.

The scene path was followed through its actual data and byte writer:

- `ADVENT01.ASM` 446-477, `VEC20`/`DRAWSC`, computes the room record offset
  as `(ROOM - 1) * (NOVLY + 1)`, reads its background ID, uses `SCRTAB` to
  select a stream, calls `SHOSC2`, then calls `SHOOBJ` on the remaining slots.
- `ADVENT03.ASM` 513-545 shows concrete room records. With `NOVLY = 8`, each
  contains one background ID and eight overlay slots, padded where needed.
  `SCRTAB`, 737-739, contains six background pointers. This is a room-to-scene
  lookup, not a two-dimensional terrain grid.
- `ADVENT.ASM` 408-452, `SHOSCR`/`SHOSC2`, produces consecutive bitmap bytes
  from literal runs, repeated-byte runs and a special alternating-row form.
  `SCREENS1.ASM` 1-12 provides all six short background streams.
- `ADVENT.ASM` 462-514, `SHOOBJ`, resolves overlay IDs through `SCROBJ` and
  also checks movable room objects. `SHOOVL`, 516-543, reads row, column and
  byte width, then places decoded bytes with a 32-byte destination stride.
- `ADVENT03.ASM` 743-753 documents that overlay header. `OVERLAY1.ASM` 4-6
  supplies a real record beginning at row 65, column 1, width seven bytes.
  `OBJBYT`, `ADVENT.ASM` 545-611, supplies the packed bytes, including the
  special descriptor. Neither the overlay header nor the byte writer reads
  a tile ID from a grid.

This independently examined package resembles the room/overlay architecture
already recorded for Sea Search. It does not become new tile-map evidence
merely because scenery repeats. No Calixto patch was examined, and no
patch-complete behavior or errata search is claimed.

### Useful narrow technique: compress alternating solid rows

Calixto's `SHOSC2` special descriptor starts with two zero bytes, followed by
run width, row count and two packed byte values. Lines 436-451 repeat the first
value across one run, exchange the values, and repeat until the count expires.
`SCREENS1.ASM` 11-12 uses width 32, count 90 and values `$66`/`$99`.
Our arithmetic gives 2,880 expanded bytes from a six-byte descriptor plus the
terminator. That calculation is not a compression benchmark or display test.
The bytes alternate between runs, not between adjacent bytes within a run.

For a builder, this can compact a repetitive rectangular background. It does
not encode arbitrary tile arrangements or collision properties. Separate the
decoded byte stream from placement: `SHOSC2` writes consecutively, whereas
`SHOOVL` imposes its own row stride. A decoder run length need not equal an
overlay's destination width.

The following is **original, untested pseudocode**, adapted from that narrow
operation. It is not a historical transcription or a CoCo initialization recipe.
Explicit bounds and rejection of zero dimensions are our additions.

```text
expand_alternating_runs(width, count, first, second, output_capacity):
    require 1 <= width <= 255 and 1 <= count <= 255
    require first and second are bytes
    require width * count <= output_capacity
    output = empty byte sequence
    for run in 0 .. count - 1:
        value = first if run is even else second
        append width copies of value to output
    return output
```

Proposed independent checks use width three, count three and values `$12` and
`$A7`: expect three `$12`, three `$A7`, then three `$12`, with no fourth run.
Reject zero width, zero count and capacity eight for that nine-byte result.
At placement, test a rectangle narrower than the framebuffer stride and guard
the untouched bytes on both sides. These checks were not run. Historical
zero-count wrap behavior is not adopted as a format feature.

The legacy routine has self-modifying fields and `OBJBYT` terminates by
discarding a return address (`ADVENT.ASM` 577-580). Its output bounds and
malformed-input handling were not established. A reusable decoder should
return explicit completion/error state rather than inherit that stack contract.

## Remaining gap and next leads

The required missing evidence remains a CoCo 1/2 source whose renderer reads
cell identifiers from a regular world grid and selects packed bitmap art.
Neither a room number nor a sprite pointer proves that representation.

The next bounded pass should prefer a magazine listing and its companion
disk over more guesses from this source directory. The existing searchable
[Rainbow index][index], PDF page 19, lists Benjamin W. Brunotte's *Rat maze*,
May 1985, printed page 105. Only that index entry was examined here. The
article, target, renderer and any corrections remain unexamined; this is a
discovery lead, not evidence of tiles. Inspect its data and drawing calls
before downloading a wider issue set.

For the already-examined Space Raiders lineage, an earlier revision would be
worth following only if primary material establishes a CoCo 1/2 target and a
different map representation. No URL or existence claim for such a revision
is supplied. More versions of the same object-list renderer would not close
this gap. Stop after a small candidate budget again.

## Provenance and reproduction

Downloads, directory HTML, original members and normalized text remain under
ignored `local/research/tile-source-followup/`. No downloaded code or art is
tracked. `sources.json` records exact URLs, sizes and hashes. Retrieved ZIPs:

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| [cubix.zip][cubix] | 363837 | `a1c39f4e3562797e53f8282db562b8de54a5946e57c6f7eca60543ea8b6c839a` |
| [SR3.zip][raiders] | 45426 | `0dcc49a4c659d5fd61739115c110b132b2c53a89bee66199a1d1c5ce939826be` |
| [calixto.zip][calixto] | 67402 | `ffe26efd81ebb87ff501032292d18b8f6c19d7513d740ca5220960bc83872971` |

For a fresh clone, download the linked ZIPs into that ignored directory, check
their hashes, and extract Cubix and Calixto as plain data. Decode text as
Latin-1, replace CRLF with LF, then replace lone CR with LF. Do not strip
blank lines or interpret embedded assembler directives. No archive program
needs to execute. No PDF conversion is needed for these sources.

Space Raiders needs disk-contained text extraction. The following original
reading utility preserves the extraction logic in Git. After placing `SR3.zip`
in the directory above, run it from the repository root. It handles this
specific flat 35-track image, not arbitrary disk formats. Its assertions check
image size, chain bounds, cycles and terminal lengths; they are extraction
sanity checks, not independent validation of the game or all disk formats.

```python
from pathlib import Path
from zipfile import ZipFile

root = Path("local/research/tile-source-followup")
with ZipFile(root / "SR3.zip") as archive:
    disk = archive.read("SR3.DSK")
assert len(disk) == 35 * 18 * 256
fat = disk[17 * 4608 + 256:17 * 4608 + 512]
directory = disk[17 * 4608 + 512:18 * 4608]
output = root / "text/SR3"
output.mkdir(parents=True, exist_ok=True)
for offset in range(0, len(directory), 32):
    entry = directory[offset:offset + 32]
    if entry[0] == 255:
        break
    if entry[0] == 0 or entry[8:11] != b"TXT":
        continue
    name = entry[:8].decode("ascii").rstrip() + ".TXT"
    granule = entry[13]
    parts, seen = [], set()
    while True:
        assert granule < 68 and granule not in seen
        seen.add(granule)
        track = granule // 2 + (granule // 2 >= 17)
        start = track * 4608 + (granule % 2) * 2304
        following = fat[granule]
        if following < 68:
            parts.append(disk[start:start + 2304])
            granule = following
            continue
        assert 0xC1 <= following <= 0xC9
        final_bytes = int.from_bytes(entry[14:16], "big")
        assert 0 < final_bytes <= 256
        length = (following - 0xC1) * 256 + final_bytes
        parts.append(disk[start:start + length])
        break
    raw = b"".join(parts)
    text = raw.decode("latin1").replace("\r\n", "\n").replace("\r", "\n")
    (output / name).write_text(text, encoding="utf-8")
```

The extraction produced five text files. Raw lengths were `SR3.TXT` 19,538,
`SRF1.TXT` 4,719, `SRC3.TXT` 4,296, `FIRESR3.TXT` 6,346 and `SRFILES.TXT`
8,786 bytes. The reading was selective as cited above. No runtime experiment
or test controls were removed or replaced by this documentation pass.

Validation: Markdown lint passes, and Ruff passes on the extracted Python
block. Running that tracked block reproduced all five normalized text files
byte-for-byte. The first comparison harness failed because executing the block
in its own namespace overwrote the harness's path variable; rerunning with an
isolated namespace fixed that harness error. It was not a disk extraction or
game failure. The alternating-run pseudocode remains unexecuted.

[directory]: https://colorcomputerarchive.com/repo/Programming/Source/
[cubix]: https://colorcomputerarchive.com/repo/Programming/Source/Cubix/cubix.zip
[raiders]: https://colorcomputerarchive.com/repo/Programming/Source/Space%20Raiders%20%28John%20Crawford%29/SR3.zip
[calixto]: https://colorcomputerarchive.com/repo/Programming/Source/Calixto%20Island/calixto.zip
[index]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20-%20Text%20Searchable%20Index/The%20Rainbow%20-%20Text%20Searchable%20Index.pdf
