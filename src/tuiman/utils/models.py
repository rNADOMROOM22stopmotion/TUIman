class ReversibleIterator:
    def __init__(self, lst):
        self.lst = lst
        self.pos = 0
        self.delta = 1

    def __next__(self):
        ret = self.lst[self.pos]
        self.pos = (self.pos + 1) % len(self.lst)
        return ret

    def __iter__(self):
        return self