"""The demo: a short lesson that plays by itself after 5 seconds on the title.

prepare.py makes the program's data from this file. expected.py plays the
same steps with its own rules. It must agree with each board after a move,
written here by hand from the rules in README.md.

A caption is a list of lines of at most 6 letters, for the 48-pixel margin
at the left of the board.

Each step is (wait, action, ...). The wait is the number of scans after the
step before it. A wait of 0 runs the step in the same scan.

- ("board", board): a new board. The demo game starts again from it.
- ("caption", name): the caption at the left of the board.
- ("key", arrow): the arrow key that lights at the right of the board, or "-".
- ("move", arrow, square, board): one move. A microbe appears in square
  (row * 4 + column), not in a random square, so that each lesson is the
  same. The board is the result, written by hand.
- ("end",): back to the title screen.

A board is four rows of levels: 0 is empty, A is 10 and B is 11.
"""

# Scans without a key on the title screen before the demo starts: 5 seconds
# at 59.94 fields each second.
IDLE_SCANS = 300

CAPTIONS = {
    "push": ["ARROWS", "PUSH", "ALL", "THAT", "WAY"],
    "spawn": ["AFTER", "EACH", "MOVE", "A NEW", "ONE", "COMES"],
    "merge": ["TWO", "ALIKE", "MERGE", "AND", "EVOLVE"],
    "chain": ["KEEP", "GOING", "UP THE", "CHAIN"],
    "lose": ["BOARD", "FULL", "AND", "STUCK", "GAME", "OVER"],
    "win": ["MAKE", "THE", "HUMAN", "TO", "WIN!"],
}

STEPS = [
    # The arrows push every creature as far as it goes.
    (0, "board", "0000/0010/0200/0000"),
    (0, "caption", "push"),
    (90, "key", "L"),
    (30, "move", "L", 3, "0001/1000/2000/0000"),
    (40, "key", "-"),
    (60, "key", "D"),
    (30, "move", "D", 0, "1000/0000/1000/2001"),
    (40, "key", "-"),
    # A microbe appears after each move.
    (30, "caption", "spawn"),
    (90, "key", "R"),
    (30, "move", "R", 4, "0001/1000/0001/0021"),
    (40, "key", "-"),
    # Two equal creatures merge into the next one. A new kind sings.
    (90, "board", "0000/1100/0000/0000"),
    (0, "caption", "merge"),
    (90, "key", "R"),
    (30, "move", "R", 8, "0000/0002/1000/0000"),
    (40, "key", "-"),
    # Two jellyfish make a trilobite that the board already has: one note.
    # Two trilobites make the first fish: three notes.
    (90, "board", "2000/2000/3000/0000"),
    (0, "caption", "chain"),
    (90, "key", "U"),
    (30, "move", "U", 15, "3000/3000/0000/0001"),
    (40, "key", "-"),
    (60, "key", "U"),
    (30, "move", "U", 14, "4001/0000/0000/0010"),
    (40, "key", "-"),
    # A full board with no equal neighbours loses.
    (90, "board", "2323/3232/2323/2320"),
    (0, "caption", "lose"),
    (90, "key", "R"),
    (30, "move", "R", 12, "2323/3232/2323/1232"),
    (40, "key", "-"),
    # The human wins.
    (180, "board", "0000/0AA0/0000/1234"),
    (0, "caption", "win"),
    (90, "key", "L"),
    (30, "move", "L", 3, "0001/B000/0000/1234"),
    (40, "key", "-"),
    (240, "end"),
]
