def add(a, b):
    if a < 0:
        raise ValueError()
    return a + b


class Calc:
    def mul(self, x, y):
        return x * y
