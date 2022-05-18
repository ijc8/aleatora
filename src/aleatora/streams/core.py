# Aleatora is a music composition framework built around streams.
# In Python terms, streams are essentially rich iterables. As iterables, they are things which can construct iterators.
# A stream may be called upon to produce many iterators, each of which may yield a new sequence of values.
# Streams may or may not terminate, and they may or may not produce the same sequence of values on each iteration.
# Streams can be specified directly, by defining a class that implements __iter__ or by defining a generator function.
# Or, streams can be constructed out of other streams using the many functions that operate on streams, including overloaded operators.

import collections
import itertools
import operator


def _make_stream_op(op, reversed=False):
    if reversed:
        def fn(self, other):
            # No need to handle the iterable case, because it will be handled by the non-reversed version.
            return self.map(lambda v: op(other, v))
        return fn
    def fn(self, other):
        if isinstance(other, collections.abc.Iterable):
            return self.zip(other).map(lambda p: op(*p))
        return self.map(lambda v: op(v, other))
    return fn

def stream(thing):
    if isinstance(thing, collections.abc.Iterable):
        return Stream(thing)
    elif isinstance(thing, collections.abc.Callable):
        return lambda *args, **kwargs: FunctionStream(lambda: thing(*args, **kwargs))
    raise ValueError("Expected iterable or function")

class Stream(collections.abc.Iterable):
    def __init__(self, iterable):
        self.iterable = iterable
    
    def __iter__(self):
        return iter(self.iterable)

    # `a >> b` means `a` followed by `b`: sequential composition.
    # For streams of audio samples, this is akin to splicing tape together, or arranging tracks horizontally in a DAW.
    def __rshift__(self, other):
        return ConcatStream((self, other))
    
    def __rrshift__(self, other):
        return ConcatStream((other, self))
    
    # `a | f` means stream `a` "piped into" a function that accepts a stream `f`: function composition, as in `f(a)`.
    # If `f` also returns a stream, then the composition can be chained, as in `a | f | g`, which equals `g(f(a))`.
    def __or__(self, other):
        return other(self)

    # The other operators behave differently with streams and other types.
    # If `other` is iterable, these operators will perform the operation element-wise along the stream and the other iterable.
    # If one argument is not a stream, the operators perform the same option (e.g. `* 2`) to each element along the one stream.

    # `a + b` means `a` and `b` at the same time.
    # For streams of audio samples, this is akin to mixing two tapes down to one, or arranging tracks vertically in a DAW.
    # Unlike *, /, etc., + and - keep going until *both* streams have ended.
    # This behavior matches an interpretation of emptiness as "zero": the additive identity and the multiplicative absorbing element.
    def __add__(self, other):
        if isinstance(other, collections.abc.Iterable):
            return MixStream((self, other))
        return self.map(lambda v: v + other)

    def __sub__(self, other):
        return self + -other

    def __getitem__(self, index):
        if isinstance(index, int):
            # Open question: will this functionality (`stream[5]`) ever get used?
            for i, value in zip(range(index), self):
                pass
            if i < index - 1:
                raise IndexError("Index out of range")
            return value
        elif isinstance(index, slice):
            return SliceStream(self, index.start, index.stop, index.step)
    
    __radd__ = _make_stream_op(operator.add, reversed=True)
    __rsub__ = _make_stream_op(operator.sub, reversed=True)

    # `a * b` means a amplitude-modulated by b (order doesn't matter).
    # I don't know if this has a equivalent in tape, but in electronics terms this is a mixer.
    __mul__ = _make_stream_op(operator.mul)
    __rmul__ = _make_stream_op(operator.mul, reversed=True)
    __truediv__ = _make_stream_op(operator.truediv)
    __rtruediv__ = _make_stream_op(operator.truediv, reversed=True)
    __floordiv__ = _make_stream_op(operator.floordiv)
    __rfloordiv__ = _make_stream_op(operator.floordiv, reversed=True)

    # `a % b` and `a ** b` are perhaps a little exotic, but I don't see any reason to exclude them.
    __mod__ = _make_stream_op(operator.mod)
    __rmod__ = _make_stream_op(operator.mod, reversed=True)
    __pow__ = _make_stream_op(operator.pow)
    __rpow__ = _make_stream_op(operator.pow, reversed=True)

    # Unary operators
    def __neg__(self): return self.map(operator.neg)
    def __pos__(self): return self.map(operator.pos)
    def __abs__(self): return self.map(operator.abs)
    def __invert__(self): return self.map(operator.invert)

    @stream
    def map(self, fn, *iterables):
        if iterables:
            for xs in self.zip(*iterables):
                yield fn(*xs)
        else:
            for x in self:
                yield fn(x)

    @stream
    def each(self, fn):
        for x in self:
            fn(x)
            yield x

    def zip(self, *others):
        return FunctionStream(lambda: zip(self, *others))

    @stream
    def filter(self, predicate):
        for x in self:
            if predicate(x):
                yield x
    
    # Monadic bind.
    # Like concat, but the second stream is not created until it is needed, and it has access to the return value of the first stream.
    # This allows for a useful definition of 'split', for example (see the `streaming` library in Haskell).
    @stream
    def bind(self, fn):
        value = yield from self
        yield from fn(value)
    
    @stream
    def join(self):
        for stream in self:
            yield from stream

    @stream
    def cycle(self, limit=None):
        if limit:
            for _ in range(limit):
                yield from self
        else:
            while True:
                yield from self
    
    @stream
    def hold(self, duration):
        for x in self:
            for _ in range(duration):
                yield x

    def reverse(self):
        # NOTE: Naturally, this requires evaluating the entire stream.
        # Calling this on an infinite stream will not result in a good time.
        return FunctionStream(lambda: iter(list(self)[::-1]))
    
    # scan left, or accumulate
    @stream
    def scan(stream, f, acc):
        for x in stream:
            yield acc
            acc = f(acc, x)
        return acc

    # fold left, or reduce
    @stream
    def fold(stream, f, acc):
        for x in stream:
            acc = f(acc, x)
        return acc

    def memoize(self):
        saved = []
        it = iter(self)
        def helper():
            yield from saved
            for x in it:
                yield x
                saved.append(x)
        return FunctionStream(helper)

    @stream
    def chunk(self, size=128):
        it = iter(self)
        chunk = list(stream(it)[:size])
        while chunk:
            yield chunk
            chunk = list(stream(it)[:size])

    @stream
    def flatten(self):
        for chunk in self:
            yield from chunk

    def run(self):
        for _ in self:
            pass

    def split(self, n=2):
        "Split one stream into many, so that it can be used as input in multiple places without recomputing output."
        # NOTE: Unlike the original stream, the 'split' streams are not restartable!
        return [stream(it) for it in itertools.tee(self, n)]



class FunctionStream(Stream):
    def __init__(self, func):
        self.func = func
    
    def __iter__(self):
        return self.func()


class ConcatStream(Stream):
    def __init__(self, streams):
        self.streams = []
        for stream in streams:
            if isinstance(stream, ConcatStream):
                # Flatten to minimize layers.
                self.streams += stream.streams
            else:
                self.streams.append(stream)
    
    def __iter__(self):
        for stream in self.streams:             
            yield from stream


class MixStream(Stream):
    def __init__(self, streams):
        self.streams = []
        for stream in streams:
            if isinstance(stream, MixStream):
                # Flatten to minimize layers.
                self.streams += stream.streams
            else:
                self.streams.append(stream)

    def __iter__(self):
        # This would work if we were okay with terminating when the shortest stream finished:
        #   for values in zip(*self.streams):
        #       yield sum(values)
        # Instead, we basically implement itertools.zip_longest, with the difference
        # that we remove exhausted iterators rather than replacing them with fillers.
        iterators = [iter(it) for it in self.streams]
        while True:
            while iterators:
                try:
                    acc = next(iterators[-1])
                    break
                except StopIteration:
                    del iterators[-1]
            for i in range(len(iterators) - 2, -1, -1):
                try:
                    acc += next(iterators[i])
                except StopIteration:
                    del iterators[i]
            if not iterators:
                break
            yield acc

class SliceStream(Stream):
    def __init__(self, stream, start, stop, step):
        # Step cannot be 0.
        assert(step is None or step > 0)
        self.stream = stream
        self.start = start or 0
        self.stop = stop
        self.step = step or 1
        # Negative values are unsupported.
        assert(self.start >= 0)
        assert(self.stop is None or self.stop >= 0)

    def __iter__(self):
        it = iter(self.stream)
        for _ in zip(range(self.start), it): pass
        indices = count() if self.stop is None else range(self.stop - self.start)
        for i, x in zip(indices, it):
            if i % self.step == 0:
                yield x
        return stream(it)


@stream
def const(value):
    while True:
        yield value

@stream
def repeat(f):
    while True:
        yield f()

count = stream(itertools.count)

@FunctionStream
def empty():
    return
    yield  # marks this as a generator function

@stream
def log(print_period=1):
    for i in count():
        print("Log:", i)
        for _ in range(print_period):
            yield

def defer(stream_fn):
    return FunctionStream(lambda: iter(stream_fn()))
