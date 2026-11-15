# Move objects without losing the world

Read this when a moving object leaves holes in the scenery or when a foreground
layer must hide an object. Read it also when drawing changes which objects collide.
Rendering and collision need separate decisions. The sources are listings and
manuals that we read but did not run. The checked examples run on a defined
CoCo 1 configuration only.

## Start with what the drawing routine overwrites

**Published explanation.** Don Inman, Kurt Inman and Dymax, *Assembly Language
Graphics for the TRS-80 Color Computer*, chapter 7, move a small shape with the
joystick in mode 6C. The drawing routine copies two bytes on each of six rows.
The erase routine clears that same rectangle before it draws elsewhere. The
address calculation clamps the placement before the copy (printed 153–155,
PDF 161–163). [Printed 151–156, PDF 159–164][graphics]

**Our adaptation.** A cleared rectangle cannot restore arbitrary scenery. It
replaces every byte, also where the shape has background-colour pixels. This is
a property of the listing, not an observed failure. The later two-saucer
exercise asks readers to investigate overlap. It gives no overlap-safe
renderer. [Printed 168–169, PDF 176–177][saucers]

Keep a fully visible object inside the screen, in matching units:

```text
0 <= x <= screen_width - object_width
0 <= y <= screen_height - object_height
```

Clipping at an edge needs a different routine. Convert pixels to byte offsets
only after you define packing and alignment. Test every horizontal alignment
that the renderer supports, including partial bytes at the right edge.

## Choose how to restore the background

**Our adaptation.** Choose a restoration method before you add scenery:

| Method | Use it when | Hazard |
| --- | --- | --- |
| Repaint the old rectangle | The background is one colour | It erases another object or a trail in the rectangle |
| Save and restore a rectangle | One object moves over unchanged scenery | An old snapshot can erase a newer object or show removed scenery again |
| Restore from a persistent background | Scenery changes during play | The buffer costs memory and must change with the scenery |
| Redraw affected regions from world state | Several objects overlap | It costs more drawing time, which also matters to [sound](sound.md) |

The [moving-objects example](../../examples/moving-objects/README.md) shows
three of these methods: save and restore, a persistent background, and a full
redraw of the scenery in each frame.

A transparency mask answers a different question: which destination pixels
does this draw keep? It does not remember what was there before the draw. A
masked draw still needs an erase or redraw method. We found no examined
listing of a CoCo masked renderer to use as a reference.

## Restore from a persistent background

**Published explanation.** Harvey Brofman's *Dunkey Munkey* source keeps the
scenery in a separate buffer. Line numbers count every line from one in the
`DunkeyMunkey_Source` files of the [source ZIP][dunkey]:

- `KONG.TXT` 98–99, `SCRSTA` and `BACGRN`: display and background buffers,
  6,144 bytes apart. The two buffers alone cost 12,288 bytes.
- `GRAPH2.TXT` 50–59, `COPYBF`, copies the background to the display. Lines
  314–345, `ERASE`, copy a rectangle of it, not a flat colour. Lines 194–282,
  `MOVE`, use `ERASE` and `SHAPE`. Some paths restore only the exposed strip.
- `SCREN2.TXT` 308–316: a rivet leaves the game state, `ERASEB` removes it
  from the background, and `ERASE` restores the display. Lines 334–355 change
  the background with `ERASEB` and `BSHAPE`, then copy it to the display.

This background is the scenery that stays after an object moves. It is not a
snapshot taken just before the draw. `SHAPE` and `BSHAPE` (`GRAPH2.TXT`
139–174) insert every shape pixel. Their loop has no transparent-colour skip.
`SETX` (83–106) masks one packed pixel in a byte, which is not an object mask.
The source uses 32-byte rows, two-bit pixels and a syntax that is not LWTOOLS.

**Our adaptation.** Keep the scenery authoritative in a separate buffer.
Change that buffer when a door opens, a pickup goes or terrain changes. Restore
old object regions from it. Then redraw the intersecting objects in layer
order.

That redraw rule is ours. The routines do not prove safe handling of
arbitrary overlap. We made no RAM, ROM, mode or CoCo 2/3 assessment.

## Save background regions separately for each screen

**Published explanation.** Sundog Systems' *GrafExpress 2.0* manual describes
nonsticky sprites. The engine saves the regions that the next sprites cover. It
draws all sprites and shows the completed screen. Then it restores the
previously shown screen from that screen's own saved regions. It keeps two sets
of restoration buffers and states their time and memory cost.
[Printed 22, PDF 27][graf-restoration]

**Our adaptation.** Tie each saved region to the screen and frame that it came
from. Save before you draw any object into that frame. Do not repair the
previous screen with the newest saved pixels. Two buffer sets do not show that
a third screen is safe.

This is our derivation, not a tested renderer. The
manual is not engine source. GE16 and GE256 have their own packing, and GE256
shows only on composite displays (printed 2, PDF 7). Neither sets up CoCo 1/2.

## Draw foreground layers last

**Published explanation.** LeRoy W. Gross's *Knight Rider* (16K Extended
Color BASIC) draws the scenery, then the rider, then the foreground scenery.
Lines 210 and 400 select and clear alternate screens. On page 76 he explains a
failure. A green fill of the foliage can find green at its start point and skip
the repaint, so the rider shows through. His listing fills with an intermediate
colour first, then with green. This is a flood-fill workaround, not a mask.
[*Hot CoCo*, October 1983, printed/PDF 72–73 and 76][knight]

**Our adaptation.** In assembly, overwrite the covered pixels of each foreground
layer from stored coverage or opaque spans. Do not rely on the seed colour of a
fill. Draw rear scenery, then actors, then foreground layers into the hidden
screen. Coverage data costs asset memory. A full rebuild costs drawing time. A
hidden screen alone does not prove a display without tearing.

## Decide whether the picture is also the collision map

**Published explanation.** Kenneth Reighard Jr.'s "The Universal Pick-Up"
presents the BASIC game *Interplanetary Trash Collector*. The contents calls it
"Inter-Planetary Trash". Lines 145–220 of the `IPTRASH` listing draw the old
point, read input, advance the position, check bounds and dispatch on `PPOINT`
at the destination. Pixel values tell empty space, obstacles, trail and pickups
apart. [*The Rainbow*, October 1992, cover/PDF 1 and printed/PDF 10][trash]

The article targets CoCo 3 with the faster clock and gives changes for CoCo 1/2
and composite output. These are the author's configurations, not tested support
claims. Do not copy its clock writes into a normal-speed project.

**Our adaptation.** Screen-based collision makes drawing part of game state. A
decorative pixel, an erase or a new trail colour can change a result. That is a
constraint when art and rules must change separately.

Write down what each collision value means before you choose colours. If
decoration must not affect movement, use a separate occupancy map or object
bounds. The [controls guide](controls-and-collision.md) develops them.

### Separate appearance from collision shape

**Published explanation.** *GrafExpress* keeps these contracts apart:

| Contract | Printed / PDF | Consequence |
| --- | --- | --- |
| Transparent pixels and solid pixels are different properties. | 3 / 8 | A visible silhouette need not be the collision shape. |
| A transparency colour makes matching pixels transparent and nonsolid. | 15 / 20 | This one picture operation ties the two properties together. |
| A rectangle picture is transparent but solid. The manual suggests it for collision with separately drawn scenery. | 16 / 21 | Walls can collide without a visible sprite. |
| Sprite changes affect collision checks at once, but reach the display only at `SHOW` or the switch command. | 17 / 22 | Say if collision tests the next state or the shown frame. |
| Disabled sprites and nonsolid pixels do not take part in `HIT`. | 17 / 22 | Visibility and collision need explicit rules. |
| GE16 sprite x positions round down to an even pixel. | 18 / 23 | Single-pixel horizontal steps are not promised. |

Printed 15 / PDF 20 also warns that the first picture definitions empty the
sprite buffers. Its doubled storage for transparent pictures is a fact of that
engine, not a budget for a new mask format. These pages give no mask operation,
pixel-perfect collision or blend loop. [Manual, PDF 20][graf-shapes]

## What the examples check

**Measured result.** Both examples run on CoCo 1 with NTSC, 32 KiB, a
normal-clock 6809 and the non-T1 MC6847. Read each machine contract before
reuse.

- The [moving-objects example](../../examples/moving-objects/README.md)
  restores the patterned scenery under two opaque byte-aligned rectangles,
  then draws them in layer order. The default method copies the old
  rectangles from a scenery buffer. Variants save the screen under each
  object, or redraw all of the scenery. In each method, 15 frames check every
  screen byte and the rendered picture: overlap in both orders and the restore
  after it, changed scenery and reversals.
- The [masked-object example](../../examples/masked-objects/README.md) restores
  the complete background, then draws hollow objects with
  `(screen AND mask) OR ink`. Variants draw the same scenes opaque and with
  XOR. Twelve scenes in each method check every screen byte and the rendered
  picture: corners, overlap order, removal and changed scenery. An independent
  pixel model gives the expected result. Origins are byte-aligned, and objects
  fit on the screen.

Neither example has collision, clipping or partial-byte placement, or
reproduces a historical renderer. Frame rate, PAL, T1 and physical hardware
remain untested. The moving-objects example draws into the shown screen. The
[page flip](../../examples/page-flip/README.md) draws the same scene into a
hidden screen. Read [show only finished frames](animation.md#show-only-finished-frames).

## Open questions

**Proposal.** No check covers the historical methods or collision. Test these
cases first:

- an exact restore of a patterned background from a saved or persistent
  buffer, also after the scenery changes beneath an object
- two objects that cross in both drawing orders, then separate
- the largest object at all four edges, with guards around saved storage
- a foreground layer whose final colour equals the background, with a
  differently coloured actor behind it. Without the foreground pass it fails.
- empty, obstacle, trail and pickup outcomes, and a move that could cross an
  obstacle between sampled positions
- a decorative colour change that must, or must not, change collision

Use expected world state that does not come from the rendering code. Then look
at the display for flicker and measure the work at the chosen clock.

## Sources

- Don Inman, Kurt Inman with Dymax, *Assembly Language Graphics for the TRS-80
  Color Computer*, chapter 7, printed 151–158, 163, 168–169, PDF 159–166, 171,
  176–177. Resource `assembly-graphics`. Its ROM joystick calls depend on the
  ROM version.
- Kenneth Reighard Jr., "The Universal Pick-Up," *The Rainbow*, October 1992,
  cover/PDF 1 and printed/PDF 10. Resource `rainbow-1992-10`. The Rainbow index
  (`rainbow-index`), PDF 87, locates it. A title and author search found no
  correction, but we did not read all later issues.
- Harvey Brofman, *Dunkey Munkey*, source dated June 24, 1982. The source
  header credits Intellectronics. The archive filename credits Cercomp. ZIP
  SHA-256 `f2dd97ac73813e9191e5f396eb24474fa95ec1c3d5cfd6230b77002aea2f06ac`.
  We read the `GRAPH2.TXT` rendering routines, the `KONG.TXT` memory
  definitions and the cited `SCREN2.TXT` callers, not every routine. We found
  no errata and no reuse licence.
- Sundog Systems, *GrafExpress 2.0*, 1991, printed 2–3, 15–18 and 21–22, PDF
  7–8, 20–23 and 26–27, read as page images. Resource `grafexpress`. The front
  addendum has no correction to these contracts. PDF 4 has its copyright and
  distribution terms. They do not permit free redistribution of the engine.
- LeRoy W. Gross, "Knight Rider," *Hot CoCo*, Vol. 1 No. 5, October 1983,
  printed/PDF 72, 73 and 76, with the complete "Riding Knight" listing through
  line 620. The [controls guide](controls-and-collision.md#sources) records the
  hash of the issue and the search for errata.

Leads that gave no rendering evidence:

- *Hot CoCo* Graphic Master adverts
- a *Dragon User* sprite article (not read)
- IBM and Atari COMPUTE! matches
- Ron Clark's BASIC GET/PUT pages (PDF 86–93)
- *Undercolor* 1:1 contents
- the first pages of three *Hot CoCo* animation articles of 1983 and 1986

We examined the cited page images and listings and ran none of them. The
adaptations and test cases are our original guidance.

[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=159>
[saucers]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=176>
[trash]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2012%20No.%2003%20-%20October%201992.pdf#page=10>
[dunkey]: <https://colorcomputerarchive.com/repo/Programming/Source/Dunkey%20Monkey/Dunkey%20Munkey%20Source%20(Harvey%20Brofman)%20(Cercomp).zip>
[graf-restoration]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Programming/GrafExpress%202.0%20(Sundog%20Systems).pdf#page=27>
[graf-shapes]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Programming/GrafExpress%202.0%20(Sundog%20Systems).pdf#page=20>
[knight]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=72>
