

class Stream:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self):
        return self.fn()

    def __rshift__(self, other):
        return concat(self, other)

    def __iter__(self):
        return self

    def __next__(self):
        result = self.fn()
        if result is None:
            raise StopIteration
        print(result)
        value, next_stream = result
        self.fn = next_stream.fn
        return value

# Ideally:
# def trim(stream, index):
#     for i, value in enumerate(stream):
#         if i > index:
#             return None
#         yield value
# But this would require changes to yield.

def trim(stream, index):
    def closure():
        if index == 0:
            return None
        result = stream()
        if result is None:
            return None
        value, next_stream = result
        return (value, trim(next_stream, index-1))
    return Stream(closure)

def concat(a, b):
    def closure():
        result = a()
        if result is None:
            return b()
        value, next_a = result
        return (value, concat(next_a, b))
    return Stream(closure)

def count(start=0):
    return Stream(lambda: (start, count(start+1)))