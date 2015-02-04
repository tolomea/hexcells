from __future__ import unicode_literals
from __future__ import division

# colors
EMPTY, BLACK, BLUE, UNKNOWN = range(4)

# constraint types
BASIC, AREA, VERTICAL, LEFT_DIAG, RIGHT_DIAG = range(5)


class Cell(object):
    def __init__(self, parts):
        self.parts = parts
    def __str__(self):
        if self.parts[0] == ".":
            return "  "
        return "".join(self.parts)


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
        self.cells = {}
        for r, row in enumerate(lines[5:]):
            for q, cell in enumerate(zip(row[::2], row[1::2])):
                if r%2 != q%2:
                    # even_q -> cube -> axial
                    x = q
                    y = r//2 - (q + (q&1)) // 2
                    self.cells[x, y] = Cell(cell)

    def neighbours(self, cell):
        pass

    def community(self, cell):
        pass

    def vertical(self, cell):
        pass

    def left_diag(self, cell):
        pass

    def right_diag(self, cell):
        pass

    def get_cells(self, cell, constraint_type):
        return {
            BASIC: neighbours,
            AREA: community,
            VERTICAL: vertical,
            LEFT_DIAG: left_diag,
            RIGHT_DIAG: right_diag,
        }[constraint_type](cell)

    def dump(self):
        for r in range(33):
            s = ""
            for q in range(1,33,2):
                s += "  "
                x = q
                y = r - (q + (q&1)) // 2
                s += str(self.cells[x, y])
            print s

            s = ""
            for q in range(0,33,2):
                x = q
                y = r - (q + (q&1)) // 2
                s += str(self.cells[x, y])
                s += "  "
            print s


if __name__ == "__main__":
    lvl = Level(open("cookie1.hexcells").read())
    lvl.dump()
