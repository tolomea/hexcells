from __future__ import unicode_literals
from __future__ import division

from collections import defaultdict
import random
import time
import itertools

from colorama import init, Back
init()

DEBUG = 15

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

    @property
    def done(self):
        return self._parts[0] not in 'ox'


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

        try:
            self._cells = self._parse_body(0, lines[5:])
        except ValueError:
            self._cells = self._parse_body(1, lines[5:])

    def _parse_body(self, offset, lines):
        cells = {}
        for r, row in enumerate(lines):
            r += offset
            for q, cell in enumerate(zip(row[::2], row[1::2])):
                if r%2 != q%2:
                    # even_q -> cube -> axial
                    x = q
                    y = r//2 - (q + (q&1)) // 2
                    index = x, y
                    cells[index] = Cell(cell)
                else:
                    if cell != (".","."):
                        raise ValueError(cell)
        return cells

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

    def total_count(self):
        return self._true_count(self.all_cells())

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
                s += colored(str(self._cells.get((x, y), Cell(".."))), colors[x, y])
                del colors[x, y]
            print s

            s = ""
            for q in range(0,33,2):
                x = q
                y = r - (q + (q&1)) // 2
                s += colored(str(self._cells.get((x, y), Cell(".."))), colors[x, y])
                s += "  "
                del colors[x, y]
            print s

        for key, color in colors.iteritems():
            print colored(key, color)

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
        self._cells[c].play()
        assert self._cells[c].color == value

    def done(self):
        return all(self._cells[c].done for c in self.all_cells())


class ConstraintViolation(Exception):
    pass


class BasicConstraint(object):
    def __init__(self, bases, cells, min_count, max_count, level):
        self.bases = bases
        self.cells = set(cells)
        self.min_count = min_count
        self.max_count = max_count
        self.orig_min_count = min_count
        self.orig_max_count = max_count
        self._normalize(level)

    def _normalize(self, level):
        blue = [c for c in self.cells if level.get_color(c) == BLUE]
        unknown = {c for c in self.cells if level.get_color(c) == UNKNOWN}
        self.min_count = max(0, self.min_count - len(blue))
        self.max_count -= len(blue)
        self.cells = unknown
        if self.max_count < self.min_count:
            raise ConstraintViolation()
        if self.min_count > len(self.cells):
            raise ConstraintViolation()

    def done(self, level):
        self._normalize(level)
        return len(self.cells) == 0

    def get_moves(self, level):
        self._normalize(level)
        if self.done(level):
            return set()
        if self.min_count == len(self.cells):
            return {(c, BLUE) for c in self.cells}
        if self.max_count == 0:
            return {(c, BLACK) for c in self.cells}
        return set()

    def get_inverse_subset_constraint(self, other, level):
        """ if other is a subset of us, return the complement of that subset """
        if other.cells < self.cells:
            bases = self.bases | other.bases
            cells = {c for c in self.cells if c not in other.cells}
            min_count = max(self.min_count - other.max_count, 0)
            max_count = min(self.max_count - other.min_count, len(cells))
            if min_count == 0 and max_count == len(cells):
                return None
            assert max_count >= min_count
            return BasicConstraint(bases, cells, min_count, max_count, level)
        else:
            return None

    def get_intersection(self, other, level):
        bases = self.bases | other.bases
        cells = self.cells & other.cells
        self_rem = len(self.cells) - len(cells)
        other_rem = len(other.cells) - len(cells)
        min_count = max(self.min_count - self_rem, other.min_count - other_rem, 0)
        max_count = min(self.max_count, other.max_count, len(cells))
        if min_count == 0 and max_count == len(cells):
            return None
        assert max_count >= min_count
        return BasicConstraint(bases, cells, min_count, max_count, level)

    def __str__(self):
        return "{s.__class__.__name__}({s.bases}, {s.orig_min_count}, {s.orig_max_count})".format(s=self)


class DisjointConstraint(BasicConstraint):
    def __init__(self, bases, cells, count, wrap, level):
        self.wrap = wrap
        if wrap:
            self.all_cells = cells
        else:
            self.all_cells = [c for c in cells if level.get_color(c) != EMPTY]
        super(DisjointConstraint, self).__init__(bases, cells, count, count, level)

    def get_moves(self, level):
        moves = super(DisjointConstraint, self).get_moves(level)
        if self.done(level):
            return set()

        current_colors = [level.get_color(c) for c in self.all_cells]
        blue_count = sum(1 for x in current_colors if x == BLUE)
        unknown_indicies = [i for i, x in enumerate(current_colors) if x == UNKNOWN]
        needed = self.orig_min_count - blue_count

        # try out every blue placement and collect the valid ones
        valid = []
        for indicies in itertools.combinations(unknown_indicies, needed):
            indicies = set(indicies)
            new_colors = []
            for i, c in enumerate(current_colors):
                if c == UNKNOWN:
                    if i in indicies:
                        new_colors.append(BLUE)
                    else:
                        new_colors.append(BLACK)
                else:
                    new_colors.append(c)

            # handle wrapping by moving blues from the start to the end
            if self.wrap:
                cnt = 0
                for c in new_colors:
                    if c == BLUE:
                        cnt += 1
                    else:
                        break
                wrapped = new_colors[cnt:] + new_colors[:cnt]
            else:
                wrapped = new_colors

            # check that this is a valid sequence
            if self._is_valid(wrapped):
                valid.append(new_colors)

        # collect the results
        if len(valid) < 1:
            ConstraintViolation()
        valid_colors = [set(x) for x in zip(*valid)]
        for cell, current_color, valid_colors in zip(self.all_cells, current_colors, valid_colors):
            if current_color == UNKNOWN:
                if len(valid_colors) == 1:
                    moves.add((cell, valid_colors.pop()))
            else:
                assert {current_color} == valid_colors

        return moves

    def _is_valid(self, new_colors):
        state = 0
        for c in new_colors:
            if state == 0:  # looking for blues
                if c == BLUE:
                    state = 1
            if state == 1:  # looking for a gap
                if c != BLUE:
                    state = 2
            if state == 2:  # looking for more blues
                if c == BLUE:
                    return True
        return False


if __name__ == "__main__":
    queue = set()
    cell_constraints = defaultdict(set)
    all_constraints = {}

    def add_constraint(cs):
        key = frozenset(cs.cells)
        if key in all_constraints:
            orig = all_constraints[key]
            min_count = max(orig.min_count, cs.min_count)
            max_count = min(orig.max_count, cs.max_count)
            assert min_count <= max_count
            orig.min_count = min_count
            orig.max_count = max_count
        else:
            if DEBUG > 30: print "new", cs
            all_constraints[key] = cs
            queue.add(cs)
            for c in cs.cells:
                cell_constraints[c].add(cs)

    def cell_updated(c):
        res = level.get_constrant(c)
        if res:
            cs_type, cells, count, modifier = res
            if modifier == APART:
                cs = DisjointConstraint({c}, cells, count, cs_type==BASIC, level)
            else:
                cs = BasicConstraint({c}, cells, count, count, level)
            add_constraint(cs)

    def play(cell, color):
        if DEBUG > 20: print "playing", c, color
        level.play(cell, color)
        cell_updated(cell)
        for cs in cell_constraints[cell]:
            if cell in cs.cells:
                queue.add(cs)

    def evaluate():
        if DEBUG > 20: print "evaluating"
        while queue:
            cs = queue.pop()
            if DEBUG > 30: print "chk", cs
            moves = cs.get_moves(level)
            if moves:
                for cell, color in moves:
                    play(cell, color)
                if DEBUG > 10: level.dump(cs.bases, [c for c,_ in moves])

    def arithmetic():
        global all_constraints
        if DEBUG > 20: print "constraint arithmetic"
        all_constraints = {frozenset(cs.cells):cs for cs in all_constraints.values() if not cs.done(level)}
        new_constraints = []
        for cs1 in all_constraints.values():
            for cs2 in all_constraints.values():
                new_constraint = cs1.get_inverse_subset_constraint(cs2, level)
                if new_constraint:
                    new_constraints.append(new_constraint)
        for cs in new_constraints:
            add_constraint(cs)

    def advanced_arithmetic():
        new_constraints = []
        for cs1 in all_constraints.values():
            for cs2 in all_constraints.values():
                new_constraint = cs1.get_intersection(cs2, level)
                if new_constraint:
                    new_constraints.append(new_constraint)
        for cs in new_constraints:
            add_constraint(cs)

    level = Level(open("cookie5.hexcells").read())
    for c in level.all_cells():
        cell_updated(c)
    if DEBUG > 10: level.dump()

    while queue:
        evaluate()
        arithmetic()
        if not queue:
            advanced_arithmetic()

    count = level.total_count()
    add_constraint(BasicConstraint({"global"}, level.all_cells(), count, count, level))

    while queue:
        evaluate()
        arithmetic()
        if not queue:
            advanced_arithmetic()

    level.dump()
    print "Done:", level.done()
