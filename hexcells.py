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

# modifiers
TOGETHER, APART = range(1, 3)

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

    @property
    def modifier(self):
        if self._parts[1] == 'c':
            return TOGETHER
        elif self._parts[1] == 'n':
            return APART
        else:
            return None

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
        count = self._true_count(cells)
        modifier = self._cells[c].modifier
        return t, cells, count, modifier

    def _true_count(self, cells):
        return sum(self._cells[c].true_value for c in cells)

    def play(self, c, value):
        print "playing", c, value
        self._cells[c].play()
        assert self._cells[c].color == value


class ConstraintViolation(Exception):
    pass


class BasicConstraint(object):
    def __init__(self, base, cells, count):
        self.bases = [base]
        self.cells = cells
        self.count = count

    def _normalize(self, level):
        blue = [c for c in self.cells if level.get_color(c) == BLUE]
        unknown = [c for c in self.cells if level.get_color(c) == UNKNOWN]
        self.count -= len(blue)
        self.cells = unknown
        if self.count < 0:
            raise ConstraintViolation()
        if self.count > len(self.cells):
            raise ConstraintViolation()

    def done(self, level):
        self._normalize(level)
        return len(self.cells) == 0

    def get_moves(self, level):
        self._normalize(level)
        if self.done(level):
            return set()
        if self.count == len(self.cells):
            print "A", {(c, BLUE) for c in self.cells}
            return {(c, BLUE) for c in self.cells}
        if self.count == 0:
            print "B", {(c, BLACK) for c in self.cells}
            return {(c, BLACK) for c in self.cells}
        return set()

class DisjointConstraint(BasicConstraint):
    def __init__(self, base, cells, count, wrap, level):
        super(DisjointConstraint, self).__init__(base, cells, count)
        self.wrap = wrap
        self.total_count = count
        if wrap:
            self.all_cells = cells
        else:
            self.all_cells = [c for c in cells if level.get_color(c) != EMPTY]
        self._normalize(level)

    def _normalize(self, level):
        super(DisjointConstraint, self)._normalize(level)
        if self.wrap:
            for i, c in enumerate(self.all_cells):
                if level.get_color(c) in [BLACK, EMPTY]:
                    self.all_cells = self.all_cells[i:] + self.all_cells[:i]
                    self.wrap = False
                    break

    def walk(self, cells, level):
        """
        unhandled

               B
           D3
        ?      ?
            B

        left question mark is made blue by end rule
        right one should be made black cause it would form a 3 run

        ?
           ?
        D2

        ?

        can't have both top question marks
        so bottom one should be blue

        """

        possible_run = []
        possible_runs = []
        blue_run = []
        for c in cells:
            color = level.get_color(c)

            # N-1 in a row can't have another
            if color == UNKNOWN and len(blue_run) == self.total_count - 1:
                print "C", c, BLACK
                yield c, BLACK

            # continue or end the blue run
            if color != BLUE:
                blue_run = []
            else:
                blue_run.append(c)

            # continue or end the possible run
            if color in [UNKNOWN, BLUE]:
                possible_run.append(c)
            else:
                if len(possible_run):
                    possible_runs.append(possible_run)
                possible_run=[]

        # pick up a trailing possible run
        if len(possible_run):
            possible_runs.append(possible_run)

        # no possible runs = fail
        if len(possible_runs) < 1:
            raise ConstraintViolation()

        # one possible section, apply the end rule
        if len(possible_runs) == 1 and not self.wrap:
            possible_run = possible_runs[0]
            if len(possible_run) == self.total_count + 1:
                if level.get_color(possible_run[0]) != BLUE:
                    print "D", possible_run[0], BLUE
                    yield possible_run[0], BLUE

    def get_moves(self, level):
        moves = super(DisjointConstraint, self).get_moves(level)
        moves.update(self.walk(self.all_cells, level))
        moves.update(self.walk(reversed(self.all_cells), level))
        return moves


if __name__ == "__main__":
    level = Level(open("cookie1.hexcells").read())

    queue = set()
    cell_constraints = defaultdict(set)

    def cell_updated(c):
        res = level.get_constrant(c)
        if res:
            cs_type, cells, count, modifier = res
            if modifier == APART:
                cs = DisjointConstraint(c, cells, count, cs_type==BASIC, level)
            else:
                cs = BasicConstraint(c, cells, count)
            queue.add(cs)
            for c in cells:
                cell_constraints[c].add(cs)

    for c in level.all_cells():
        cell_updated(c)

    def play(cell, color):
        level.play(cell, color)
        cell_updated(cell)
        queue.update(cell_constraints[cell])

    def evaluate():
        while queue:
            cs = queue.pop()
            print cs
            moves = cs.get_moves(level)
            if moves:
                for cell, color in moves:
                    play(cell, color)
                level.dump(cs.bases, [c for c,_ in moves])

    level.dump()
    evaluate()


