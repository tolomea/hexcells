"""
Hexcells Solver

Usage:
  hexcells.py [--debug=LEVEL] [--show-moves] HEXCELLS_FILES...

Options:
  -h --help        Show this screen.
  --debug=LEVEL    Debug print level [default: 10]
  --show-moves     Show moves made during solving (synonym for --debug=15)
"""

from __future__ import unicode_literals
from __future__ import division

"""
Level credits
alpha-first_hexcells_test - Invaluable for basic debug and testing
cookie-teamwork - All the early development was against this level
cookie-the_star - This one necessitated advanced_arithmetic
"""

from collections import defaultdict
import random
import time
import itertools
import sys

import docopt
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
    if color:
        return color + text + Back.RESET
    else:
        return text


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
        self._colors = dict()

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
        colors = defaultdict(lambda: None)
        if blues:
            for c in blues:
                colors[c] = Back.CYAN
        if reds:
            for c in reds:
                colors[c] = Back.MAGENTA

        s = ""

        for y in range(33):
            for x in range(33):
                s += colored(str(self._cells[(x, y)]), colors[x, y])
                del colors[x, y]
            s += "\n"

        for key, color in colors.iteritems():
            s += colored(key, color) + "\n"
        print s

    def get_color(self, c):
        try:
            return self._colors[c]
        except:
            res = self._cells.get(c, Cell("..")).color
            self._colors[c] = res
            return res

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
        self._colors[c] = value

    def done(self):
        return all(self._cells[c].done for c in self.all_cells())


def transpose(matrix):
    return zip(*matrix)


def cut_patterns(indicies, patterns, new_cells):
    res_i = []
    res_v = []
    for i, v in zip(indicies, transpose(patterns)):
        if i in new_cells:
            res_i.append(i)
            res_v.append(v)
    return res_i, transpose(res_v)


def intersect_patterns(p1, p2):
    p1 = set(p1)
    p2 = set(p2)
    return p1 & p2


def limit_patterns(patterns, min_count, max_count):
    new_min = 1000
    new_max = 0
    res = []
    for v in patterns:
        c = sum(x==BLUE for x in v)
        if min_count <= c <= max_count:
            res.append(v)
            new_min = min(c, new_min)
            new_max = max(c, new_max)
    return res, new_min, new_max


class Constraint(object):
    def __init__(self, bases, cells, min_count, max_count, debug, indicies=None, patterns=None):
        self.bases = frozenset(bases)
        self.cells = frozenset(cells)
        self.min_count = min_count
        self.max_count = max_count
        self._key = self.cells, self.min_count, self.max_count
        self.interesting = min_count != 0 or max_count != len(cells)
        self.indicies = indicies
        self.patterns = patterns
        self.debug = debug

    @classmethod
    def make(cls, base, cells, min_count, max_count, level, indicies=None, patterns=None):
        cells, min_count, max_count = cls._normalize(cells, min_count, max_count, level)
        debug = str(base)
        return Constraint({base}, cells, min_count, max_count, debug, indicies, patterns)

    @staticmethod
    def _normalize(cells, min_count, max_count, level):
        assert 0 <= min_count <= max_count
        blue_count = sum(1 for c in cells if level.get_color(c) == BLUE)
        cells = {c for c in cells if level.get_color(c) == UNKNOWN}
        min_count = max(0, min_count - blue_count)
        max_count -= blue_count
        assert 0 <= min_count <= max_count <= len(cells)
        return cells, min_count, max_count

    def get_moves(self, level):
        if len(self.cells) == 0:
            return set()
        if self.min_count == len(self.cells):
            return {(c, BLUE) for c in self.cells}
        if self.max_count == 0:
            return {(c, BLACK) for c in self.cells}
        if self.patterns:
            moves = set()
            for c, values in zip(self.indicies, transpose(self.patterns)):
                if len(set(values)) == 1:
                    moves.add((c, values[0]))
            return moves
        return set()

    def __hash__(self):
        return hash(self._key)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._key == other._key

    def __ne__(self, other):
        return not(self == other)

    def get_inverse_subset_constraint(self, other):
        """ if other is a subset of us, return the complement of that subset """
        if other.cells < self.cells:
            bases = self.bases | other.bases
            cells = self.cells - other.cells
            min_count = max(self.min_count - other.max_count, 0)
            max_count = min(self.max_count - other.min_count, len(cells))
            assert max_count >= min_count
            debug = "({0}-{1})".format(self.debug, other.debug)

            if self.patterns:
                indicies, patterns = cut_patterns(self.indicies, self.patterns, cells)
                patterns, min_count, max_count = limit_patterns(patterns, min_count, max_count)
            else:
                indicies = None
                patterns = None

            return Constraint(bases, cells, min_count, max_count, debug, indicies=indicies, patterns=patterns)
        else:
            return None

    def get_intersection(self, other):
        cells = self.cells & other.cells
        if not cells:
            return None
        len_cells = len(cells)
        self_rem = len(self.cells) - len_cells
        other_rem = len(other.cells) - len_cells
        min_count = max(self.min_count - self_rem, other.min_count - other_rem, 0)
        max_count = min(self.max_count, other.max_count, len_cells)
        bases = self.bases | other.bases
        assert max_count >= min_count
        debug = "({0}&{1})".format(self.debug, other.debug)

        if self.patterns:
            indicies, patterns = cut_patterns(self.indicies, self.patterns, cells)
            if other.patterns:
                indicies2, patterns2 = cut_patterns(other.indicies, other.patterns, cells)
                assert indicies == indicies2
                patterns = intersect_patterns(patterns, patterns2)
            patterns, min_count, max_count = limit_patterns(patterns, min_count, max_count)
        else:
            if other.patterns:
                indicies, patterns = cut_patterns(other.indicies, other.patterns, cells)
                patterns, min_count, max_count = limit_patterns(patterns, min_count, max_count)
            else:
                indicies = None
                patterns = None

        return Constraint(bases, cells, min_count, max_count, debug, indicies=indicies, patterns=patterns)

    def __str__(self):
        return "{s.__class__.__name__}({s.debug})".format(s=self)

    def merge(self, other):
        assert self.cells == other.cells
        min_count = max(self.min_count, other.min_count)
        max_count = min(self.max_count, other.max_count)
        if self.min_count == min_count and self.max_count == max_count:
            return None
        if other.min_count == min_count and other.max_count == max_count:
            return other
        debug = "{0}%{1}".format(self.debug, other.debug)

        if self.patterns:
            indicies, patterns = self.indicies, self.patterns
            if other.patterns:
                indicies2, patterns2 = other.indicies, other.patterns
                assert indicies == indicies2
                patterns = intersect_patterns(patterns, patterns2)
            patterns, min_count, max_count = limit_patterns(patterns, min_count, max_count)
        else:
            if other.patterns:
                indicies, patterns = other.indicies, other.patterns
                patterns, min_count, max_count = limit_patterns(patterns, min_count, max_count)
            else:
                indicies = None
                patterns = None

        return Constraint(self.bases | other.bases, self.cells, min_count, max_count, debug, indicies=indicies, patterns=patterns)


def basic(base, cells, count, level):
    cs = Constraint.make(base, cells, count, count, level)
    moves = cs.get_moves(level)
    if moves:
        return moves, cs
    if cs.interesting:
        return None, cs
    return None, None


def eval_modifier(cells, count, is_valid, wrap, level):
    if not wrap:
        cells = [c for c in cells if level.get_color(c) != EMPTY]

    current_colors = [level.get_color(c) for c in cells]
    blue_count = sum(1 for x in current_colors if x == BLUE)
    unknown_indicies = [i for i, x in enumerate(current_colors) if x == UNKNOWN]
    needed = count - blue_count

    # try out every blue placement and collect the valid ones
    valid = set()
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
        if wrap:
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
        if is_valid(wrapped):
            valid.add(tuple(new_colors))

    # sort them, filter the known ones and collect up the indicies
    indicies = []
    values = []
    for cell, orig_color, new_colors in sorted(zip(cells, current_colors, transpose(valid))):
        if orig_color == UNKNOWN:
            indicies.append(cell)
            values.append(new_colors)
    return indicies, transpose(values)

def disjoint(base, cells, count, loop, level):
    def is_valid(new_colors):
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

    indicies, valid = eval_modifier(cells, count, is_valid, loop, level)
    cs = Constraint.make(base, cells, count, count, level, indicies, valid)
    moves = cs.get_moves(level)
    if moves:
        return moves, cs
    if cs.interesting:
        return None, cs
    return None, None


def joint(base, cells, count, loop, level):
    def is_valid(new_colors):
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

    indicies, valid = eval_modifier(cells, count, is_valid, loop, level)
    cs = Constraint.make(base, cells, count, count, level, indicies, valid)
    moves = cs.get_moves(level)
    if moves:
        return moves, cs
    if cs.interesting:
        return None, cs
    return None, None


def subset(cs1, cs2, level):
    cs = cs1.get_inverse_subset_constraint(cs2)
    if cs:
        moves = cs.get_moves(level)
        if moves:
            return moves, cs
        if cs.interesting:
            return None, cs
    return None, None


def intersection(cs1, cs2, level):
    cs = cs1.get_intersection(cs2)
    if cs:
        moves = cs.get_moves(level)
        if moves:
            return moves, cs
        if cs.interesting:
            return None, cs
    return None, None


class Solver(object):
    def __init__(self, level):
        self.level = level

    def evaluate(self):
        if DEBUG > 20: print "evaluate"
        self.all_constraints = dict()
        self.arith_new = set()
        self.arith_old = set()
        self.adv_new = set()
        self.adv_old = set()
        self.super_new = set()
        self.super_old = set()
        self.new_stuff = True
        for c in self.level.all_cells():
            res = self.level.get_constrant(c)
            if res:
                cs_type, cells, count, modifier = res
                if modifier == APART:
                    moves, cs = disjoint(c, cells, count, cs_type==BASIC, self.level)
                elif modifier == TOGETHER:
                    moves, cs = joint(c, cells, count, cs_type==BASIC, self.level)
                else:
                    moves, cs = basic(c, cells, count, self.level)
                if moves:
                    return moves, cs
                if cs:
                    self.add_constraint(cs)
        return None, None

    def add_constraint(self, cs):
        old = self.all_constraints.get(cs.cells)
        if old is not None:
            old = self.all_constraints[cs.cells]
            cs = old.merge(cs)
            if cs is None:
                return
            self.arith_new.discard(old)
            self.arith_old.discard(old)
            self.adv_new.discard(old)
            self.adv_old.discard(old)
            self.super_new.discard(old)
            self.super_old.discard(old)
        if DEBUG > 30: print "new", cs
        self.all_constraints[cs.cells] = cs
        self.arith_new.add(cs)
        self.adv_new.add(cs)
        self.super_new.add(cs)
        self.new_stuff = True

    def play(self, cell, color):
        if DEBUG > 20: print "playing", cell, color
        self.level.play(cell, color)

    def arithmetic(self):
        if DEBUG > 20: print "constraint arithmetic", len(self.all_constraints), len(self.arith_new)
        new_constraints = set()
        def inner(a, b):
            for cs1 in a:
                for cs2 in b:
                    if cs2.cells < cs1.cells:
                        moves, cs = subset(cs1, cs2, self.level)
                        if moves:
                            return moves, cs
                        if cs:
                            new_constraints.add(cs)
            return None, None
        moves, cs = inner(self.arith_new, self.arith_new)
        if moves:
            return moves, cs
        moves, cs = inner(self.arith_old, self.arith_new)
        if moves:
            return moves, cs
        moves, cs = inner(self.arith_new, self.arith_old)
        if moves:
            return moves, cs

        self.arith_old.update(self.arith_new)
        self.arith_new = set()

        for cs in new_constraints:
            self.add_constraint(cs)
        return None, None

    def advanced_arithmetic(self):
        if DEBUG > 20: print "advanced arithmetic", len(self.all_constraints), len(self.adv_new)
        new_constraints = set()
        def inner2(a):
            a = list(a)
            for i, cs1 in enumerate(a):
                for cs2 in a[i:]:
                    moves, cs = intersection(cs1, cs2, self.level)
                    if moves:
                        return moves, cs
                    if cs:
                        new_constraints.add(cs)
            return None, None
        def inner(a, b):
            for cs1 in a:
                for cs2 in b:
                    moves, cs = intersection(cs1, cs2, self.level)
                    if moves:
                        return moves, cs
                    if cs:
                        new_constraints.add(cs)
            return None, None
        moves, cs = inner2(self.adv_new)
        if moves:
            return moves, cs
        moves, cs = inner(self.adv_new, self.adv_old)
        if moves:
            return moves, cs

        self.adv_old.update(self.adv_new)
        self.adv_new = set()

        for cs in new_constraints:
            self.add_constraint(cs)
        return None, None

    def global_constraint(self):
        if DEBUG > 20: print "global constraint"
        count = self.level.total_count()
        cells = self.level.all_cells()
        moves, cs = basic("global", cells, count, self.level)
        if moves:
            return moves, cs
        if cs:
            self.add_constraint(cs)
        return None, None

    def _solve(self):
        moves, cs = self.evaluate()
        if moves:
            return moves, cs

        while self.new_stuff:
            self.new_stuff = False
            moves, cs = self.arithmetic()
            if moves:
                return moves, cs

            if not self.new_stuff:
                moves, cs = self.advanced_arithmetic()
                if moves:
                    return moves, cs

            if not self.new_stuff:
                # add in the global constraint
                moves, cs = self.global_constraint()
                if moves:
                    return moves, cs

        return None, None

    def solve(self):
        if DEBUG > 10: self.level.dump()
        while True:
            moves, cs = self._solve()
            if not moves:
                break
            if DEBUG > 25: print "play", cs
            for cell, color in moves:
                self.play(cell, color)
            if DEBUG > 10: self.level.dump(cs.bases, [c for c,_ in moves])

        return self.level.done


def main():
    global DEBUG
    try:
        arguments = docopt.docopt(__doc__)
    except docopt.DocoptExit:
        print __doc__
        sys.exit(1)
    DEBUG = int(arguments["--debug"])
    if arguments.get("--show-moves"):
        DEBUG = 15

    for fname in arguments["HEXCELLS_FILES"]:
        level = Level(open(fname).read())

        start = time.time()

        Solver(level).solve()


        level.dump()
        print "File:", fname
        print "Done:", level.done()
        print "Time:", time.time() - start

        if not level.done():
            sys.exit(1)

if __name__ == "__main__":
    main()
