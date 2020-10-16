import math
import numpy as np
import time
import operator
import functools


SAMPLE_RATE = 44100


# Helper function to reduce boilerplate.
def make_stream_op(op, reversed=False):
    if reversed:
        def fn(self, other):
            # No need to handle the Stream case, because it will be handled by the non-reversed version.
            return self.map(lambda v: op(other, v))
        return fn
    def fn(self, other):
        if isinstance(other, Stream):
            return stream_zip(self, other).map(lambda p: op(*p))
        return self.map(lambda v: op(v, other))
    return fn


class Stream:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self):
        return self.fn()

    def __iter__(self):
        return StreamIterator(self)

    ## Operators
    # `a >> b` means a followed by b. (In tape terms, splicing.)
    # NOTE: unfortunately, this is left-associative, so `a >> b >> c` will be less efficient than `a >> (b >> c)`.
    # This will be fixed in the next iteration by Stream subclasses.
    def __rshift__(self, other):
        return concat2(self, other)

    # `a >>= b` is the bind operator. For this operator, b is not a stream, but a function that returns a stream.
    def __irshift__(self, other):
        return bind(self, other)

    # The remaining operators behave differently with streams and other types.
    # If both arguments are streams, these operators will perform the operation element-wise along both streams.
    # If one argument is not a stream, the operators perform the same option (e.g. `* 2`) to each element along the one stream.

    # `a + b` means a and b at the same time. (In tape terms, mixing two tapes down to one.)
    # Unlike *, /, etc., this operator keeps going until *both* streams have ended.
    def __add__(self, other):
        if isinstance(other, Stream):
            return stream_add(self, other)
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
            result = drop(self, index)()
            if isinstance(result, Return):
                raise IndexError("stream index out of range")
            return result[0]
        elif isinstance(index, slice):
            return stream_slice(self, index.start, index.stop, index.step)

    def map(self, fn):
       return stream_map(self, fn)


# Tag for a stream's final return value.
class Return:
    def __init__(self, value=None):
        self.value = value


class StreamIterator:
    def __init__(self, stream):
        # Note that this can be read by the user after a for loop, to get at the rest of the stream.
        # (e.g. after `for i, x in zip(range(5), stream_iter):`; see drop() below for an example.)
        self.rest = stream
        self.last_value = None
        self.returned = None

    def __iter__(self):
        return self

    def __next__(self):
        result = self.rest()
        if isinstance(result, Return):
            self.returned = result
            raise StopIteration(result.value)
        self.last_value, self.rest = result
        return self.last_value


def stream(f):
    return lambda *args, **kwargs: Stream(f(*args, **kwargs))


## Basic stream operations.
@stream
def concat2(stream_a, stream_b):
    def closure():
        result = stream_a()
        if isinstance(result, Return):
            return stream_b()
        value, next_a = result
        return (value, concat2(next_a, stream_b))
    return closure

def concat(streams):
    return functools.reduce(lambda x, y: y >> x, list(streams)[::-1])

def cycle(stream):
    return stream >> (lambda: cycle(stream)())

@stream
def bind(stream_a, stream_fn_b):
    def closure():
        result = stream_a()
        if isinstance(result, Return):
            return stream_fn_b(result.value)()
        value, next_a = result
        return (value, bind(next_a, stream_fn_b))
    return closure

@stream
def count(start=0):
    return lambda: (start, count(start+1))

@stream
def repeat(value):
    return lambda: (value, repeat(value))

@stream
def stream_map(stream, fn):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (fn(value), stream_map(next_stream, fn))
    return closure

@stream
def stream_zip(*streams):
    def closure():
        results = [stream() for stream in streams]
        if any(isinstance(result, Return) for result in results):
            return Return(results)
        values = [result[0] for result in results]
        next_streams = [result[1] for result in results]
        return (values, stream_zip(*next_streams))
    return closure

@stream
def stream_add(stream_a, stream_b):
    def closure():
        result_a = stream_a()
        result_b = stream_b()
        if isinstance(result_a, Return):
            return result_b
        if isinstance(result_b, Return):
            return result_a
        value_a, next_a = result_a
        value_b, next_b = result_b
        return (value_a + value_b, stream_add(next_a, next_b))
    return closure

@stream
def take(stream, index):
    def closure():
        if index == 0:
            return Return()
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (value, take(next_stream, index-1))
    return closure

@stream
def drop(stream, index):
    def closure():
        siter = iter(stream)
        # Drop values up to index.
        for _ in zip(range(index), siter):
            pass
        if siter.returned:
            return siter.returned
        return siter.rest()
    return closure

# TODO: can this be rewritten in terms of zip, instead?
@stream
def compress(stream, selectors):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        sel_result = selectors()
        value, next_stream = result
        if isinstance(sel_result, Return):
            return Return(value)
        selector, next_selectors = sel_result
        if selector:
            return (value, compress(next_stream, next_selectors))
        return compress(next_stream, next_selectors)()
    return closure

def subsample(stream, step):
    return compress(stream, count().map(lambda x: x % step == 0))

@stream
def stream_slice(stream, start, stop, step):
    # This is only really relevant to audio streams:
    start = convert_time(start)
    stop = convert_time(stop)
    # This is gross, but if we have to do the None checks due to how slice() works, we might as well make use of them to minimize indirection.
    real_start = start not in (0, None)
    real_stop = stop is not None
    real_step = step not in (1, None)
    if real_start:
        if real_stop:
            if real_step:
                return subsample(drop(take(stream, stop), start), step)
            return drop(take(stream, stop), start)
        elif real_step:
            return subsample(drop(stream, start), step)
        return drop(stream, start)
    elif real_stop:
        if real_step:
            return subsample(take(stream, stop), step)
        return take(stream, stop)
    elif real_step:
        return subsample(stream, step)
    return stream


## Funkier stuff: memoizing streams, converting other sequences to Streams.
@stream
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

def list_to_stream(l):
    stream = Stream(lambda: Return())
    for v in l[::-1]:
        stream = (lambda x, r: Stream(lambda: (x, r)))(v, stream)
    return stream


## Synthesis functions.
silence = repeat(0)

def osc(freq):
    return count().map(lambda t: math.sin(2*math.pi*t*freq/SAMPLE_RATE))

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
