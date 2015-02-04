class Level(object):
    @staticmethod
    def read(data):
        lines = data.splitlines()
        assert lines[0] == "Hexcells level v1"


if __name__ == "__main__":
    lvl = Level.read(open("cookie1.hexcells").read())
