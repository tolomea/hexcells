"""
Hexcells Solver

Usage:
  hexcells.py HEXCELLS_FILE [--debug=LEVEL]

Options:
  -h --help        Show this screen.
  --debug=LEVEL  Debug print level [default: 10]
"""

from __future__ import unicode_literals
from __future__ import division

"""
Level credits
cookie-teamwork - All the early development was against this level
cookie-the_star - This one necessitated advanced_arithmetic
darman-tutorial_12 - Currently unsolved
pteranodonc-rings - Hang
"""

from collections import defaultdict
import random
import time
import itertools

from docopt import docopt
from cached_property import cached_property
from colorama import init, Back
init()

DEBUG = 0

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

    @cached_property
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

    @cached_property
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

    @cached_property
    def true_value(self):
        if self._parts[0] in 'xX':
            return 1
        return 0

    @cached_property
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
        del self.color
        del self.constraint_type

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

        self._cells = self._parse_body(lines[5:])

    def _parse_body(self, lines):
        cells = {}
        for y, row in enumerate(lines):
            for x, cell in enumerate(zip(row[::2], row[1::2])):
                cells[x, y] = Cell(cell)
        return cells

    def neighbours(self, cell):
        for c in [
            (1, -1),
            (0, -2),
            (-1, -1),
            (-1, 1),
            (0, 2),
            (1, 1),
        ]:
            yield add(cell, c)

    def community(self, cell):
        for c in self.neighbours(cell):
            yield c
        for c in [
            (2, -2),
            (1, -3),
            (0, -4),
            (-1, -3),
            (-2, -2),
            (-2, 0),
            (-2, 2),
            (-1, 3),
            (0, 4),
            (1, 3),
            (2, 2),
            (2, 0),
        ]:
            yield add(cell, c)

    def _line(self, cell, step):
        while True:
            cell = add(cell, step)
            if cell not in self._cells:
                return
            yield cell

    def vertical(self, cell):
        return self._line(cell, (0, 2))

    def left_diag(self, cell):
        return self._line(cell, (-1, 1))

    def right_diag(self, cell):
        return self._line(cell, (1, 1))

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

        for y in range(33):
            s = ""
            for x in range(33):
                s += colored(str(self._cells[(x, y)]), colors[x, y])
                del colors[x, y]
            print s

        for key, color in colors.iteritems():
            print colored(key, color)

    def get_color(self, c):
        return self._cells.get(c, Cell("..")).color

    def get_constrant(self, c):
        t = self._cells.get(c, Cell("..")).constraint_type
        if t is None:
            return None
        cells = self.get_cells(c, t)
        count = self._true_count(cells)
        modifier = self._cells[c].modifier
        return t, cells, count, modifier

    def _true_count(self, cells):
        return sum(self._cells.get(c, Cell("..")).true_value for c in cells)

    def play(self, c, value):
        self._cells[c].play()
        assert self._cells[c].color == value

    def done(self):
        return all(self._cells[c].done for c in self.all_cells())


class ConstraintViolation(Exception):
    pass


class BasicConstraint(object):
    def __init__(self, bases, cells, min_count, max_count, level):
        cells, min_count, max_count = self._normalize(cells, min_count, max_count, level)
        self.bases = frozenset(bases)
        self.cells = set(cells)
        self.min_count = min_count
        self.max_count = max_count
        self._key = frozenset(self.cells), self.min_count, self.max_count

    @staticmethod
    def _normalize(cells, min_count, max_count, level):
        assert 0 <= min_count <= max_count
        blue_count = sum(1 for c in cells if level.get_color(c) == BLUE)
        unknown = {c for c in cells if level.get_color(c) == UNKNOWN}
        min_count = max(0, min_count - blue_count)
        max_count -= blue_count
        assert 0 <= min_count <= max_count
        cells = unknown
        if max_count < min_count:
            raise ConstraintViolation()
        if min_count > len(cells):
            raise ConstraintViolation()
        return cells, min_count, max_count

    def get_moves(self, level):
        cells, min_count, max_count = self._normalize(self.cells, self.min_count, self.max_count, level)
        if len(cells) == 0:
            return None, set()
        if min_count == len(cells):
            return None, {(c, BLUE) for c in cells}
        if max_count == 0:
            return None, {(c, BLACK) for c in cells}
        return self.get_reduced(level), set()

    def get_reduced(self, level):
        return BasicConstraint(self.bases, self.cells, self.min_count, self.max_count, level)

    def __hash__(self):
        return hash(self._key)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._key == other._key

    def __ne__(self, other):
        return not(self == other)

    def get_inverse_subset_constraint(self, other, level):
        """ if other is a subset of us, return the complement of that subset """
        if other.cells < self.cells:
            bases = self.bases | other.bases
            cells = self.cells - other.cells
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
        return "{s.__class__.__name__}({s.bases})".format(s=self)


class _AdvancedConstraint(BasicConstraint):
    def __init__(self, bases, cells, count, wrap, level):
        self.orig_count = count
        self.wrap = wrap
        if wrap:
            self.all_cells = cells
        else:
            self.all_cells = [c for c in cells if level.get_color(c) != EMPTY]
        super(_AdvancedConstraint, self).__init__(bases, cells, count, count, level)

    def get_reduced(self, level):
        return self.__class__(self.bases, self.all_cells, self.orig_count, self.wrap, level)

    def get_moves(self, level):
        constraint, moves = super(_AdvancedConstraint, self).get_moves(level)
        if moves is None:
            return constraint, moves

        current_colors = [level.get_color(c) for c in self.all_cells]
        blue_count = sum(1 for x in current_colors if x == BLUE)
        unknown_indicies = [i for i, x in enumerate(current_colors) if x == UNKNOWN]
        needed = self.orig_count - blue_count

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

        return constraint, moves

    def _is_valid(self, new_colors):
        raise NotImplemented()


class DisjointConstraint(_AdvancedConstraint):
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


class JointConstraint(_AdvancedConstraint):
    def _is_valid(self, new_colors):
        state = 0
        for c in new_colors:
            if state == 0:  # looking for blues
                if c == BLUE:
                    state = 1
            if state == 1:  # looking for a gap
                if c != BLUE:
                    state = 2
            if state == 2:  # check no more blues
                if c == BLUE:
                    return False
        return True


class Solver(object):
    def __init__(self, level):
        self.queue = set()
        self.all_constraints = set()
        self.new_constraints = set()
        self.old_constraints = set()
        self.level = level
        self._init_constraints()

    def _clear_constraints(self):
        if DEBUG > 20: print "clear"
        self.all_constraints = set()
        self.new_constraints = set()
        self.old_constraints = set()
        self.queue=set()

    def _init_constraints(self):
        if DEBUG > 20: print "init"
        for c in level.all_cells():
            self.cell_updated(c)

    def add_constraint(self, cs):
        if cs not in self.all_constraints:
            if DEBUG > 30: print "new", cs
            self.all_constraints.add(cs)
            self.new_constraints.add(cs)
            self.queue.add(cs)

    def cell_updated(self, c):
        res = self.level.get_constrant(c)
        if res:
            cs_type, cells, count, modifier = res
            if modifier == APART:
                cs = DisjointConstraint({c}, cells, count, cs_type==BASIC, self.level)
            elif modifier == TOGETHER:
                cs = JointConstraint({c}, cells, count, cs_type==BASIC, self.level)
            else:
                cs = BasicConstraint({c}, cells, count, count, self.level)
            self.add_constraint(cs)

    def play(self, cell, color):
        if DEBUG > 20: print "playing", cell, color
        self.level.play(cell, color)
        self._clear_constraints()
        self._init_constraints()

    def evaluate(self):
        if DEBUG > 20: print "evaluating", len(self.all_constraints), len(self.queue)
        while self.queue:
            cs = self.queue.pop()
            if DEBUG > 30: print "chk", cs
            new_cs, moves = cs.get_moves(self.level)
            if moves:
                for cell, color in moves:
                    self.play(cell, color)
                if DEBUG > 10: self.level.dump(cs.bases, [c for c,_ in moves])
            elif new_cs != cs:
                if new_cs is not None:
                    self.add_constraint(new_cs)

    def arithmetic(self):
        if DEBUG > 20: print "constraint arithmetic"
        new_constraints = set()
        def inner(a, b):
            for cs1 in a:
                for cs2 in b:
                    if cs2.cells < cs1.cells:
                        new_constraint = cs1.get_inverse_subset_constraint(cs2, self.level)
                        if new_constraint:
                            new_constraints.add(new_constraint)
        inner(self.new_constraints, self.new_constraints)
        inner(self.old_constraints, self.new_constraints)
        inner(self.new_constraints, self.old_constraints)
        self.new_constraints.update(self.old_constraints)
        self.old_constraints = set()

        for cs in new_constraints:
            self.add_constraint(cs)

    def advanced_arithmetic(self):
        if DEBUG > 20: print "advanced arithmetic"
        new_constraints = set()
        for cs1 in self.all_constraints:
            for cs2 in self.all_constraints:
                new_constraint = cs1.get_intersection(cs2, self.level)
                if new_constraint:
                    new_constraints.add(new_constraint)
        for cs in new_constraints:
            self.add_constraint(cs)

    def solve(self):
        if DEBUG > 10: level.dump()

        while self.queue:
            self.evaluate()
            self.arithmetic()
            if not self.queue:
                self.advanced_arithmetic()
                if not self.queue:
                    # add in the global constraint
                    count = self.level.total_count()
                    cells = self.level.all_cells()
                    self.add_constraint(BasicConstraint({"global"}, cells, count, count, self.level))
                    print "global"

        print len(self.all_constraints), len(self.queue)
        return level.done



if __name__ == "__main__":
    arguments = docopt(__doc__)
    DEBUG = int(arguments["--debug"])

    fname = arguments["HEXCELLS_FILE"]


    level = Level(open(fname).read())

    start = time.time()

    Solver(level).solve()

    print time.time() - start

    level.dump()
    print "Done:", level.done()

    if not level.done:
        sys.exit(1)
