from __future__ import unicode_literals
from __future__ import division

from collections import defaultdict
import random
import time

from colorama import init, Back
init()

# colors
EMPTY, BLACK, BLUE, UNKNOWN = range(1, 5)

# constraint types
BASIC, AREA, VERTICAL, LEFT_DIAG, RIGHT_DIAG = range(1, 6)


def colored(text, color):
    return color + text + Back.RESET


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


class Cell(object):
    def __init__(self, parts):
        self._parts = parts

    def __str__(self):
        if self._parts[0] == ".":
            return "  "
        elif self._parts[0] in 'ox':
            return ".."
        else:
            return "".join(self._parts)

    @property
    def color(self):
        if self._parts[0] == 'O':
            return BLACK
        elif self._parts[0] == 'X':
            return BLUE
        elif self._parts[0] in 'ox':
            return UNKNOWN
        elif self._parts[0] in '\\|/.':
            return EMPTY
        else:
            assert False

    @property
    def constraint_type(self):
        if self._parts[1] == '.':
            return None

        if self._parts[0] in 'ox.':
            return None
        elif self._parts[0] == 'O':
            return BASIC
        elif self._parts[0] == 'X':
            return AREA
        elif self._parts[0] == '\\':
            return RIGHT_DIAG
        elif self._parts[0] == '|':
            return VERTICAL
        elif self._parts[0] == '/':
            return LEFT_DIAG
        else:
            assert False

    @property
    def true_value(self):
        if self._parts[0] in 'xX':
            return 1
        return 0

    def play(self):
        assert self._parts[0] in 'ox'
        self._parts = self._parts[0].upper() + self._parts[1]


class Level(object):
    def __init__(self, data):
        """
        *.hexcells format

        Encoding: UTF-8

        A level is a sequence of 38 lines, separated with '\n' character:

        "Hexcells level v1"
        Level title
        Author
        Level custom text, part 1
        Level custom text, part 2
        33 level lines follow:
        A line is a sequence of 33 2-character groups.
        '.' = nothing, 'o' = black, 'O' = black revealed, 'x' = blue, 'X' = blue revealed, '\','|','/' = column number at 3 different angles (-60, 0, 60)
        '.' = blank, '+' = has number, 'c' = consecutive, 'n' = not consecutive
        """
        lines = data.splitlines()
        assert lines[0] == "Hexcells level v1"
        self.title = lines[1]
        self.author = lines[2]
        self.custom_text_1 = lines[3]
        self.custom_text_2 = lines[4]
        self._cells = {}
        for r, row in enumerate(lines[5:]):
            for q, cell in enumerate(zip(row[::2], row[1::2])):
                if r%2 != q%2:
                    # even_q -> cube -> axial
                    x = q
                    y = r//2 - (q + (q&1)) // 2
                    index = x, y
                    self._cells[index] = Cell(cell)

    def neighbours(self, cell):
        for c in [
            (-1, 0),
            (-1, 1),
            (0, 1),
            (1, 0),
            (1, -1),
            (0, -1),
        ]:
            yield add(cell, c)

    def community(self, cell):
        for c in self.neighbours(cell):
            yield c
        for c in [
            (-2, 0),
            (-2, 1),
            (-2, 2),
            (-1, 2),
            (0, 2),
            (1, 1),
            (2, 0),
            (2, -1),
            (2, -2),
            (1, -2),
            (0, -2),
            (-1, -1),
        ]:
            yield add(cell, c)

    def _line(self, cell, step):
        while True:
            cell = add(cell, step)
            if cell not in self._cells:
                return
            yield cell

    def vertical(self, cell):
        return self._line(cell, (0, 1))

    def left_diag(self, cell):
        return self._line(cell, (-1, 1))

    def right_diag(self, cell):
        return self._line(cell, (1, 0))

    def get_cells(self, cell, constraint_type):
        return list({
            BASIC: self.neighbours,
            AREA: self.community,
            VERTICAL: self.vertical,
            LEFT_DIAG: self.left_diag,
            RIGHT_DIAG: self.right_diag,
        }[constraint_type](cell))

    def all_cells(self):
        return self._cells.keys()

    def dump(self, reds=None, blues=None):
        colors = defaultdict(lambda: Back.RESET)
        if blues:
            for c in blues:
                colors[c] = Back.CYAN
        if reds:
            for c in reds:
                colors[c] = Back.MAGENTA

        for r in range(17):
            s = ""
            for q in range(1,33,2):
                x = q
                y = r - (q + (q&1)) // 2
                s += "  "
                s += colored(str(self._cells[x, y]), colors[x, y])
            print s

            if r < 16:
                s = ""
                for q in range(0,33,2):
                    x = q
                    y = r - (q + (q&1)) // 2
                    s += colored(str(self._cells[x, y]), colors[x, y])
                    s += "  "
                print s

    def get_color(self, c):
        return self._cells[c].color

    def get_constrant(self, c):
        t = self._cells[c].constraint_type
        if t is None:
            return None
        cells = self.get_cells(c, t)
        count = self._count(cells)
        return cells, count

    def _count(self, cells):
        return sum(self._cells[c].true_value for c in cells)

    def play(self, c, value):
        print "playing", c, value
        self._cells[c].play()
        assert self._cells[c].color == value


class ConstraintViolation(Exception):
    pass


class BasicConstraint(object):
    def __init__(self, cells, count):
        self.cells = cells
        self.count = count

    def _normalize(self, lvl):
        blue = [c for c in self.cells if lvl.get_color(c) == BLUE]
        unknown = [c for c in self.cells if lvl.get_color(c) == UNKNOWN]
        self.count -= len(blue)
        self.cells = unknown
        if self.count < 0:
            raise ConstraintViolation()
        if self.count > len(self.cells):
            raise ConstraintViolation()

    def done(self, lvl):
        self._normalize(lvl)
        return len(self.cells) == 0

    def actionable(self, lvl):
        self._normalize(lvl)
        if self.done(lvl):
            return []
        if self.count == len(self.cells):
            return [(c, BLUE) for c in self.cells]
        if self.count == 0:
            return [(c, BLACK) for c in self.cells]
        return []


if __name__ == "__main__":
    lvl = Level(open("cookie1.hexcells").read())

    c = 15, 0
    for d in [BASIC, AREA, VERTICAL, LEFT_DIAG, RIGHT_DIAG]:
        lvl.dump([c],lvl.get_cells(c, d))

    c = 14, 0
    lvl.play(c, BLUE)

    c = 12, 0
    lvl.play(c, BLUE)

    c = 13, 1
    lvl.play(c, BLACK)
    lvl.dump([c])


    for i in range(5):
        lvl.dump()
        for c in lvl.all_cells():
            res = lvl.get_constrant(c)
            if res:
                cells, count = res
                bc = BasicConstraint(cells, count)
                print bc.done(lvl), bc.actionable(lvl)
                for cell, color in bc.actionable(lvl):
                    lvl.play(cell, color)

