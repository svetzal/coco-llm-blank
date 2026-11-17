"""Where the demo puts its words and keys: shared by prepare.py and expected.py.

The board fills the screen from pixel 48 to pixel 271. The demo uses the two
black margins: pixels 0 to 47 and 272 to 319. Each line of words is centred
in its margin.
"""

MARGIN_LEFT, MARGIN_RIGHT, MARGIN_WIDTH = 0, 272, 48
MARGIN_TOP_ROW, CAPTION_ROW, LINE_PITCH = 8, 56, 12
MARGIN_TOP_LEFT = ["DEMO"]
MARGIN_TOP_RIGHT = ["SPACE", "TO", "PLAY"]
# The arrow keys, twice the size of a letter (16 by 16 pixels): x, y of the
# top-left pixel. Up is above Down, like the keys of the CoCo 3.
KEYS = {"U": (288, 140), "L": (272, 162), "D": (288, 162), "R": (304, 162)}


def centred(text: str, margin: int) -> int:
    """The first pixel of a line of 8-pixel letters, centred in a margin."""
    return margin + (MARGIN_WIDTH - 8 * len(text)) // 2
