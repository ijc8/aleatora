import math
import numpy as np
import time
import operator


# This is the default sample rate, but it may be modified by audio module to
# match what the audio device supports.
SAMPLE_RATE = 44100


# Tag for a stream's final return value.
# (This allows to distinguish between a stream continuing, and a stream returning a final value which happens to look like continuation.)
class Return:
    def __init__(self, value=None):
        self.value = value


# Helper class for iterating over streams.
class StreamIterator:
    def __init__(self, stream):
        # Note that this can be read by the user after a for loop, to get at the rest of the stream.
        # (e.g. after `for i, x in zip(range(5), stream_iter):`; see drop() below for an example.)
        self.rest = stream
        self.returned = None

    def __iter__(self):
        return self

    def __next__(self):
        result = self.rest()
        if isinstance(result, Return):
            self.returned = result
            raise StopIteration(result.value)
        value, self.rest = result
        return value


# Helper function to reduce boilerplate in the class definition below.
def make_stream_op(op, reversed=False):
    if reversed:
        def fn(self, other):
            # No need to handle the Stream case, because it will be handled by the non-reversed version.
            return self.map(lambda v: op(other, v))
        return fn
    def fn(self, other):
        if isinstance(other, Stream):
            return ZipStream([self, other]).map(lambda p: op(*p))
        return self.map(lambda v: op(v, other))
    return fn

# The Stream class.
# This defines the Stream interface, serves as the parent for special kinds of streams,
# and this serves as the "default" kind of stream for black-boxes
class Stream:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self):
        return self.fn()

    def __iter__(self):
        return StreamIterator(self)

    ## Operators
    # `a >> b` means a followed by b. (In tape terms, splicing.)
    def __rshift__(self, other):
        return ConcatStream((self, other))

    # The remaining operators behave differently with streams and other types.
    # If both arguments are streams, these operators will perform the operation element-wise along both streams.
    # If one argument is not a stream, the operators perform the same option (e.g. `* 2`) to each element along the one stream.

    # `a + b` means a and b at the same time. (In tape terms, mixing two tapes down to one.)
    # Unlike *, /, etc., this operator keeps going until *both* streams have ended.
    def __add__(self, other):
        if isinstance(other, Stream):
            return MixStream([self, other])
        return self.map(lambda v: v + other)

    __radd__ = make_stream_op(operator.add, reversed=True)

    # `a * b` means a amplitude-modulated by b (order doesn't matter).
    # I don't know if this has a equivalent in tape, but in electronics terms this is a mixer.
    __mul__ = make_stream_op(operator.mul)
    __rmul__ = make_stream_op(operator.mul, reversed=True)
    __truediv__ = make_stream_op(operator.truediv)
    __rtruediv__ = make_stream_op(operator.truediv, reversed=True)
    __floordiv__ = make_stream_op(operator.floordiv)
    __rfloordiv__ = make_stream_op(operator.floordiv, reversed=True)

    # `a % b` and `a ** b` are perhaps a little exotic, but I don't see any reason to exclude them.
    __mod__ = make_stream_op(operator.mod)
    __rmod__ = make_stream_op(operator.mod, reversed=True)
    __pow__ = make_stream_op(operator.pow)
    __rpow__ = make_stream_op(operator.pow, reversed=True)

    # The bitwise operators so that I may repurpose them, as in the case of `>>` above.

    def __getitem__(self, index):
        if isinstance(index, int):
            # Open question: will this functionality (`stream[5]`) ever get used?
            for i, value in zip(range(index), self):
                pass
            if i < index - 1:
                raise IndexError("stream index out of range")
            return value
        elif isinstance(index, slice):
            return SliceStream(self, index.start, index.stop, index.step)

    def map(self, fn):
       return MapStream(self, fn)


class ConcatStream(Stream):
    def __init__(self, streams):
        self.streams = tuple(streams)

    def __call__(self):
        if not self.streams:
            return Return()
        elif len(self.streams) == 1:
            return self.streams[0]()
        elif isinstance(self.streams[0], ConcatStream):
            # Flatten to minimize layers
            return ConcatStream(self.streams[0].streams + self.streams[1:])()
        result = self.streams[0]()
        if isinstance(result, Return):
            return ConcatStream(self.streams[1:])()
        value, rest = result
        return (value, ConcatStream((rest,) + self.streams[1:]))

concat = ConcatStream


class MixStream(Stream):
    def __init__(self, streams):
        self.streams = []
        for stream in streams:
            if isinstance(stream, MixStream):
                # Merge in other mix streams to keep this flat and minimize layers.
                self.streams += stream.streams
            else:
                self.streams.append(stream)

    def __call__(self):
        if len(self.streams) == 1:
            return self.streams[0]()
        results = [stream() for stream in self.streams]
        continuing = [result for result in results if not isinstance(result, Return)]
        if not continuing:
            return Return(results)
        value = sum(x for x, _ in continuing)
        next_streams = [s for _, s in continuing]
        return (value, MixStream(next_streams))


class MapStream(Stream):
    def __init__(self, stream, fn):
        # Could consider flattening MapStreams via function composition.
        self.stream = stream
        self.fn = fn

    def __call__(self):
        result = self.stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (self.fn(value), MapStream(next_stream, self.fn))


class ZipStream(Stream):
    def __init__(self, streams):
        self.streams = streams

    def __call__(self):
        results = [stream() for stream in self.streams]
        if any(isinstance(result, Return) for result in results):
            return Return(results)
        values = [result[0] for result in results]
        next_streams = [result[1] for result in results]
        return (values, ZipStream(next_streams))


class SliceStream(Stream):
    def __init__(self, stream, start, stop, step):
        # Negative values are unsupported.
        assert(start is None or start >= 0)
        assert(stop is None or stop >= 0)
        # Additionally, step cannot be 0.
        assert(step is None or step > 0)
        self.stream = stream
        self.start = convert_time(start) or 0
        self.stop = convert_time(stop)
        self.step = convert_time(step) or 1

    def __call__(self):
        if self.start > 0:
            siter = iter(self.stream)
            # Drop values up to start.
            for _ in zip(range(self.start), siter):
                pass
            if siter.returned:
                return siter.returned
            return SliceStream(siter.rest, 0, self.stop, self.step)()
        elif self.stop is None and self.step == 1:
            # Special case: no need to wrap this in a slice.
            return self.stream()
        elif self.stop is None or self.stop > 0:
            siter = iter(self.stream)
            for _, value in zip(range(self.step), siter):
                pass
            if siter.returned:
                return siter.returned
            return (value, SliceStream(siter.rest, 0, self.stop - self.step, self.step))
        # We've reached the end of the slice.
        return Return(self.stream)


class NamedStream(Stream):
    def __init__(self, name, fn):
        self.name = name
        super().__init__(fn)


def cycle(stream):
    cycled = ConcatStream(())
    cycled.streams = (stream, cycled)
    return cycled

# This wraps primitive streams (functions) and optionally names them. Assumes the decorated function is lazily recursive.
def stream(name=None):
    if name:
        def wrapper(f):
            return lambda *args, **kwargs: NamedStream(name, f(*args, **kwargs))
    else:
        def wrapper(f):
            return lambda *args, **kwargs: Stream(f(*args, **kwargs))
    return wrapper

# This is for naming complex streams, which do not refer to themselves.
def namify(name, init_stream):
    @stream(name=name)
    def namer(stream):
        def closure():
            result = stream()
            if isinstance(result, Return):
                return result
            value, next_stream = result
            return (value, namer(next_stream))
        return closure
    return namer(init_stream)

# Decorator version
# NOTE: Unlike @stream, where specifying a name involves no additional layers of indirection,
#       this adds overhead because namify wraps an existing Stream (much like Map).
def name(name):
    def wrapper(f):
        def inner(*args, **kwargs):
            init_stream = f(*args, **kwargs)
            return namify(name, init_stream)
        return inner
    return wrapper


@stream("count")
def count(start=0):
    return lambda: (start, count(start+1))

@stream("repeat")
def repeat(value):
    return lambda: (value, repeat(value))

silence = namify("silence", repeat(0))

@stream("memoize")
def memoize(stream):
    called = False
    saved = None
    def closure():
        nonlocal called, saved
        if not called:
            called = True
            result = stream()
            if isinstance(result, Return):
                saved = result
            else:
                value, next_stream = result
                saved = (value, memoize(next_stream))
        return saved
    return closure

# The memoization is necessary here because there's no way to replay a Python iterator from an earlier point.
def iter_to_stream(iter):
    def closure():
        try:
            v = next(iter)
            return (v, closure)
        except StopIteration:
            return Return()
    return memoize(closure)

empty = Stream(lambda: Return())

def list_to_stream(l):
    # Constructs the whole stream immediately.
    stream = empty
    for v in l[::-1]:
        stream = (lambda x, r: Stream(lambda: (x, r)))(v, stream)
    return NamedStream("list", stream)

@name("osc")
def osc(freq):
    return count().map(lambda t: math.sin(2*math.pi*t*freq/SAMPLE_RATE))

def sqr(freq):
    return count().map(lambda t: int((t * freq/SAMPLE_RATE % 1) > 0.5) * 2 - 1)

def basic_envelope(length):
    length = convert_time(length)
    ramp_time = int(length * 0.1)
    ramp = np.linspace(0, 1, ramp_time)
    envelope = np.concatenate((ramp, np.ones(length - ramp_time*2), ramp[::-1]))
    return list_to_stream(envelope)


## Utilities that have more to do with audio than streams.
def convert_time(time):
    if isinstance(time, float):
        return int(time * SAMPLE_RATE)
    return time

def m2f(midi):
    return 2**((midi - 69)/12) * 440