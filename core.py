import numpy as np

import array
import inspect
import math
import time
import operator
import random
import pickle


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


# Preliminary magic for introspection.
# This stuff is used by the assistant to list all streams, stream-creating functions, and instruments.

# Registry of stream-creating functions.
# There is no registry for streams themselves, because they can be identified by type (`isinstance(x, Stream)`).
stream_registry = {}

def make_namer(fn):
    def closure(*args, **kwargs):
        args = inspect.signature(fn).bind(*args, **kwargs).arguments
        return f"{fn.__name__}({', '.join(f'{name}={value}' for name, value in args.items())})"
    return closure

# If `json` is a string, indicate a single parameter that should be sent to the assistant.
# If `json` is any other iterable, indicate multiple parameters instead (sent in an object).
def make_inspector(fn, json=None):
    def closure(*args, **kwargs):
        ba = inspect.signature(fn).bind(*args, **kwargs)
        ba.apply_defaults()
        d = {
            "name": fn.__name__,
            "parameters": ba.arguments,
        }
        if json is not None:
            if isinstance(json, str):
                d["json"] = ba.arguments[json]
            else:
                d["json"] = {param: ba.arguments[param] for param in json}
        return d
    return closure

def register_stream(f, **kwargs):
    if f.__module__ not in stream_registry:
        stream_registry[f.__module__] = {}
    f.metadata = kwargs
    stream_registry[f.__module__][f.__qualname__] = f
    return f

# This wraps primitive streams (functions) and gives them namers/inspectors.
# Namers/inspectors use Python's introspection features by default, but can be overriden for custom displays.
# Assumes the decorated function is lazily recursive.
# TODO: merge with @stream?
def raw_stream(f=None, namer=None, inspector=None, register=True, json=None, **kwargs):
    def wrapper(f):
        nonlocal namer, inspector
        namer = namer or make_namer(f)
        inspector = inspector or make_inspector(f, json=json)
        if register:
            register_stream(f, **kwargs)
        return lambda *args, **kwargs: NamedStream(namer, f(*args, **kwargs), args, kwargs, inspector)
    if f:
        return wrapper(f)
    return wrapper

# This is for naming streams that already return other streams (rather than beng lazily recursive).
# NOTE: The NamedStream outer layer is only present at the start. Wrapping the entire stream creates excessive overhead.
def stream(f=None, namer=None, inspector=None, register=True, json=None, **kwargs):
    def wrapper(f):
        nonlocal namer, inspector
        namer = namer or make_namer(f)
        inspector = inspector or make_inspector(f, json=json)
        if register:
            register_stream(f, **kwargs)
        def inner(*args, **kwargs):
            init_stream = f(*args, **kwargs)
            def _inspector(*args, **kwargs):
                d = inspector(*args, **kwargs)
                d['implementation'] = init_stream
                return d
            return NamedStream(namer, init_stream, args, kwargs, _inspector)
        return inner
    if f:
        return wrapper(f)
    return wrapper

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

    def __sub__(self, other):
        return self + -other
    
    def __rsub__(self, other):
        return -self + other

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

    # Unary operators
    def __neg__(self): return self.map(operator.neg)
    def __pos__(self): return self.map(operator.pos)
    def __abs__(self): return self.map(operator.abs)
    def __invert__(self): return self.map(operator.invert)

    # The bitwise operators are omitted so that I may repurpose them, as in the case of `>>` above.

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

    @register_stream
    def map(self, fn):
       return MapStream(self, fn)
    
    @register_stream
    def zip(self, *others):
        return ZipStream((self,) + others)

    @raw_stream
    def filter(self, predicate):
        def closure():
            stream = self
            while True:
                result = stream()
                if isinstance(result, Return):
                    return result
                value, stream = result
                if not predicate(value):
                    continue
                return (value, stream.filter(predicate))
        return closure
    
    # Monadic bind.
    # Like concat, but the second stream is not created until it is needed, and it has access to the return value of the first stream.
    # This allows for a useful definition of 'split', for example (see the `streaming` library in Haskell).
    @raw_stream
    def bind(self, fn):
        def closure():
            result = self()
            if isinstance(result, Return):
                return fn(result.value)()
            value, stream = result
            return (value, stream.bind(fn))
        return closure
    
    @raw_stream
    def join(self):
        def closure():
            result = self()
            if isinstance(result, Return):
                return result
            value, stream = result
            return (value >> stream.join())()
        return closure

    @stream
    def cycle(self):
        cycled = ConcatStream(())
        cycled.streams = (self, cycled)
        return cycled

    def __str__(self):
        return "Mystery Stream"

    def inspect(self):
        return {"name": str(self), "parameters": {}}


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

    def __str__(self):
        return ' >> '.join(map(str, self.streams))

    def inspect(self):
        return {
            "name": "concat",
            "parameters": {},
            "children": {
                "streams": self.streams,
                "direction": "left-right",
                "separator": ">>",
            }
        }

concat = ConcatStream # rename the class?


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

    def __str__(self):
        return ' + '.join(map(str, self.streams))

    def inspect(self):
        return {
            "name": "mix",
            "parameters": {},
            "children": {
                "streams": self.streams,
                "direction": "top-down",
                "separator": "+",
            }
        }

mix = MixStream  # rename the class?


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

    def __str__(self):
        return f"{self.stream}.map({self.fn})"

    def inspect(self):
        return {
            "name": "map",
            "parameters": {"fn": self.fn},
            "children": {
                "streams": (self.stream,),
                "direction": "top-down",
                "separator": "",
            }
        }


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

    def __str__(self):
        return f"ZipStream({', '.join(map(str, self.streams))})"
    
    def inspect(self):
        return {
            "name": "zip",
            "parameters": {},
            "children": {
                "streams": self.streams,
                "direction": "top-down",
                "separator": ",",
            }
        }


class SliceStream(Stream):
    def __init__(self, stream, start, stop, step):
        # TODO: should start (drop) be eager?
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
            if self.stop is None:
                return SliceStream(siter.rest, 0, self.stop, self.step)()
            return SliceStream(siter.rest, 0, self.stop - self.start, self.step)()
        elif self.stop is None and self.step == 1:
            # Special case: no need to wrap this in a slice.
            return self.stream()
        elif (self.stop is None or self.stop > 0) and self.step == 1:
            # Common case: just return the next value.
            result = self.stream()
            if isinstance(result, Return):
                return result
            value, next_stream = result
            return (value, SliceStream(next_stream, 0, self.stop - 1 if self.stop is not None else None, 1))
        elif self.stop is None or self.stop > 0:
            # step != 1, so we have to skip some values.
            # (Could also implement this by calling a new SliceStream with start set to step.)
            siter = iter(self.stream)
            for _, value in zip(range(self.step), siter):
                pass
            if siter.returned:
                return siter.returned
            return (value, SliceStream(siter.rest, 0, max(self.stop - self.step, 0) if self.stop is not None else None, self.step))
        # We've reached the end of the slice.
        return Return(self.stream)

    def __str__(self):
        return f"{self.stream}[{self.start or ''}:{self.stop if self.stop is not None else ''}:{self.step if self.step != 1 else ''}]"

    def inspect(self):
        return {
            "name": "slice",
            "parameters": {"start": self.start, "stop": self.stop, "step": self.step},
            "children": {
                "streams": (self.stream,),
                "direction": "top-down",
                "separator": "",
            }
        }


class NamedStream(Stream):
    def __init__(self, namer, fn, args=None, kwargs=None, inspector=None):
        self.namer = namer
        self.args = args
        self.kwargs = kwargs
        self.inspector = inspector
        super().__init__(fn)

    def __str__(self):
        if isinstance(self.namer, str):
            return self.namer
        return self.namer(*self.args, **self.kwargs)

    def inspect(self):
        if self.inspector:
            return self.inspector(*self.args, **self.kwargs)
        else:
            return {"name": str(self), "parameters": {}}


# TODO: Deprecate in favor of Stream.cycle().
@stream
def cycle(stream):
    cycled = ConcatStream(())
    cycled.streams = (stream, cycled)
    return cycled

@raw_stream
def count(start=0):
    return lambda: (start, count(start+1))

@raw_stream
def mod(modulus, start=0):
    # We do the mod up-front rather than in the recursive call, in case the user passed start >= modulus.
    result = start % modulus
    return lambda: (result, mod(modulus, result + 1))

# @raw_stream
# def const(value):
#     def closure():
#         return (value, closure)
#     return closure

@raw_stream
def const(value):
    "Yield the same value forever."
    return lambda: (value, const(value))

silence = const(0)
ones = const(1)

# Note: Each memoization cell retains a reference to the next one,
# so memory usage will grow with the difference between the earliest
# externally-held cell and the latest evaluated cell.
@raw_stream
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

class ListStream(Stream):
    "A finite stream of precomputed values."

    def __init__(self, list, index=0):
        self.list = list
        self.index = index
    
    def __call__(self):
        if self.index < len(self.list):
            return (self.list[self.index], ListStream(self.list, self.index + 1))
        return Return()
    
    def __len__(self):
        return len(self.list) - self.index
    
    def __str__(self):
        return f"ListStream([...], index={self.index})"
    
    def inspect(self):
        return {
            "name": "list",
            "parameters": {"list": self.list, "index": self.index}
        }

class FrozenStream(ListStream):
    "Like a ListStream, except it also yields a final return value."

    def __init__(self, list, return_value=None, index=0):
        self.list = list
        self.return_value = return_value
        self.index = index
    
    def __call__(self):
        if self.index < len(self.list):
            return (self.list[self.index], FrozenStream(self.list, self.return_value, self.index + 1))
        return Return(self.return_value)
    
    def __str__(self):
        return f"FrozenStream([...], return_value={self.return_value}, index={self.index})"
    
    def inspect(self):
        return {
            "name": "frozen",
            "parameters": {"list": self.list, "return_value": self.return_value, "index": self.index}
        }


def list_to_stream(l):
    import warnings
    warnings.warn("list_to_stream is deprecated, use to_stream instead", DeprecationWarning)
    return ListStream(l)

def to_stream(x):
    if isinstance(x, Stream):
        return x
    if isinstance(x, np.ndarray):
        return ListStream(array.array('d', x))
    return ListStream(x)

# @stream
# def osc(freq):
#     return count().map(lambda t: math.sin(2*math.pi*t*freq/SAMPLE_RATE))

# Sometimes it's useful to specify the starting phase:
@raw_stream
def osc(freq, phase=0):
    return lambda: (math.sin(phase), osc(freq, phase + 2*math.pi*freq/SAMPLE_RATE))

# NOTE: Aliased.
@stream
def sqr(freq):
    return count().map(lambda t: int((t * freq/SAMPLE_RATE % 1) < 0.5) * 2 - 1)

def basic_envelope(length):
    length = convert_time(length)
    ramp_time = int(length * 0.1)
    ramp = np.linspace(0, 1, ramp_time)
    envelope = np.concatenate((ramp, np.ones(length - ramp_time*2), ramp[::-1]))
    return to_stream(envelope)


## Utilities that have more to do with audio than streams.
def convert_time(time):
    if isinstance(time, float):
        return int(time * SAMPLE_RATE)
    return time

def m2f(midi):
    return 2**((midi - 69)/12) * 440




## TODO: EXPERIMENTAL - needs documentation & integration

# TODO: define this in terms of a fold.
# TODO: expose the freq_stream for inspection.
#   This will probably require making this a class and rethinking how graph generation works.
@raw_stream
def fm_osc(freq_stream, phase=0):
    def closure():
        result = freq_stream()
        if isinstance(result, Return):
            return result
        freq, next_stream = result
        return (math.sin(phase), fm_osc(next_stream, phase + 2*math.pi*freq/SAMPLE_RATE))
    return closure

@raw_stream
def glide(freq_stream, hold_time, transition_time, start_freq=0):
    def closure():
        result = freq_stream()
        if isinstance(result, Return):
            return result
        freq, next_stream = result
        tt = convert_time(transition_time)
        transition = (count()[:tt] / tt) * (freq - start_freq) + start_freq
        hold = const(freq)[:hold_time]
        return (transition >> hold >> glide(next_stream, hold_time, transition_time, start_freq=freq))()
    return closure


@raw_stream
def lazy_concat(stream_of_streams):
    def closure():
        result = stream_of_streams()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (value >> lazy_concat(next_stream))()
    return closure

# def sqr_inst(pitch, duration):
#     return sqr(m2f(pitch)) * basic_envelope(60.0 / bpm * duration * 4)

def basic_sequencer(note_stream, bpm=80):
    # Assumes quarters have the beat.
    return lazy_concat(note_stream.map(lambda n: sqr(m2f(n[0])) * basic_envelope(60.0 / bpm * n[1] * 4)))


@stream
def adsr(attack, decay, sustain_time, sustain_level, release):
    attack, decay, sustain_time, release = map(convert_time, (attack, decay, sustain_time, release))
    return to_stream(np.concatenate((np.linspace(0, 1, attack, endpoint=False),
                                     np.linspace(1, sustain_level, decay, endpoint=False),
                                     np.ones(sustain_time) * sustain_level,
                                     np.linspace(0, sustain_level, release, endpoint=False)[::-1])))


# This function produces a stream of exactly length, by trimming or padding as needed.
# Hypothetically, might also want a function that strictly pads (like str.ljust()).
# Could return another object with length metadata, or make this a method and override it for some kinds of streams.
def fit(stream, length):
    return (stream >> silence)[:length]


# # foldr, not foldl.
# @stream("fold")
# def fold(stream, f, acc):
#     def closure():
#         result = stream()
#         if isinstance(result, Return):
#             return acc
#         x, next_stream = result
#         return f(x, fold(next_stream, f, acc))
#     return closure

# scanl, not scanr
@raw_stream
def scan(stream, f, acc):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return acc
        x, next_stream = result
        next_acc = f(x, acc)
        return (acc, scan(next_stream, f, next_acc))
    return closure

@stream
def pulse(freq, duty):
    return count().map(lambda t: int((t * freq/SAMPLE_RATE % 1) < duty) * 2 - 1)

@stream
def fm_pulse(freq_stream, duty):
    return scan(freq_stream, lambda x, y: x+y, 0).map(lambda phase: int(((phase/SAMPLE_RATE) % 1) < duty) * 2 - 1)

# NOTE: Aliased.
@stream
def tri(freq):
    return count().map(lambda t: abs((t * freq/SAMPLE_RATE % 1) - 0.5) * 4 - 1)


rand = NamedStream("rand", lambda: (random.random(), rand))


class Wavetable(Stream):
    def __init__(self, list, rate, index=0):
        self.list = list
        self.rate = rate
        self.index = index % len(list)
    
    def __call__(self):
        index = int(self.index)
        frac = self.index - index
        start = self.list[index]
        end = self.list[(index + 1) % len(self.list)]
        interp = start + (end - start) * frac
        return (interp, Wavetable(self.list, self.rate, self.index + self.rate))


# Stream-controlled resampler. Think varispeed.
# TODO: Debug. Compared with Wavetable, which interpolates the same way, the results here are slightly off.
@raw_stream
def resample(stream, advance_stream, pos=0, sample=None, next_sample=0):
    def closure():
        nonlocal stream, pos, sample, next_sample
        result = advance_stream()
        if isinstance(result, Return):
            return result
        advance, next_advance_stream = result
        pos += advance
        while pos >= 0:
            result = stream()
            if isinstance(result, Return):
                return result
            sample = next_sample
            next_sample, stream = result
            pos -= 1
        interpolated = (next_sample - sample) * (pos + 1) + sample
        return (interpolated, resample(stream, next_advance_stream, pos, sample, next_sample))
    return closure


@raw_stream
def interp(stream, time=0, prev_time=None, prev_value=None, next_time=0, next_value=0):
    # TODO: adopt a consistent policy re. this kind of convenience conversion
    if not isinstance(stream, Stream):
        stream = to_stream(stream)
    # TODO: rewrite this more simply (and probably more efficiently); see glide(), example.
    def closure():
        nonlocal stream, time, prev_time, prev_value, next_time, next_value
        time += 1
        while time >= next_time:
            result = stream()
            if isinstance(result, Return):
                return result
            prev_time, prev_value = next_time, next_value
            (next_time, next_value), stream = result
            next_time = convert_time(next_time)
        interpolated = (next_value - prev_value) * (time - prev_time)/(next_time-prev_time) + prev_value
        return (interpolated, interp(stream, time, prev_time, prev_value, next_time, next_value))
    return closure


def freeze(stream):
    print('Rendering...')
    t = time.time()
    r = list(stream)
    print('Done in', time.time() - t)
    return NamedStream(f"freeze({str(stream)})", to_stream(r))


# Essentially a partial freeze of length 1.
# Useful for determining the number of channels automatically.
def peek(stream, default=None):
    result = stream()
    if isinstance(result, Return):
        return (default, Stream(lambda: result))
    x, rest = result
    # "Unpeek". Overhead disappears after first sample.
    return (x, to_stream([x]) >> rest)

@raw_stream
def branch(choices, default=empty):
    # choices is list [(weight, stream)]
    def closure():
        x = random.random()
        acc = 0
        for weight, stream in choices:
            acc += weight
            if acc >= x:
                return stream()
        return default()
    return closure

@stream
def flip(a, b):
    return branch([(0.5, a), (0.5, b)])

@stream
def pan(stream, pos):
    return stream.map(lambda x: (x * (1 - pos), x * pos))

# TODO: Make this more elegant.
# e.g. variant of ZipStream that yields a special type (with overloaded arithmetic) rather than tuples.
@stream
def stereo_add(self, other):
    return ZipStream((self, other)).map(lambda p: (p[0][0] + p[1][0], p[0][1] + p[1][1]))

def normalize(stream):
    # Requires evaluating the whole stream to determine the max volume.
    # Works for any number of channels.
    print('Rendering...')
    t = time.time()
    l = list(stream)
    print('Done in', time.time() - t)
    a = np.array(l)
    peak = np.max(np.abs(a))
    return to_stream(a / peak)

# Analagous to DAW timeline; takes a bunch of streams and their start times, and arranges them in a reasonably efficient way.
@stream
def arrange(items):
    if not items:
        return empty
    items = sorted(items, key=lambda item: item[0], reverse=True)
    last_start_time, last_stream = items[0]
    out = lambda r: r + last_stream
    prev_start_time = last_start_time
    for start_time, stream in items[1:]:
        # Sometimes I really wish Python had `let`...
        out = (lambda start, stream, prev: (lambda r: (r + stream)[:start].bind(prev)))(prev_start_time - start_time, stream, out)
        prev_start_time = start_time
    return silence[:last_start_time][:prev_start_time].bind(out)

# More new stuff (3/2):
@raw_stream
def cons(item, stream):
    return lambda: (item, stream)

def just(item):  # rename so `just` can just return a value?
    return cons(item, empty)

@stream
def events_in_time(timed_events, filler=None):
    stream = empty
    last_time = 0
    for time, event in timed_events:
        stream = stream >> const(filler)[:time - last_time] >> just(event)
        last_time = time + 1  # account for the fact that just(item) has length 1.
    return stream

# Simple additive synthesis: takes in [(amplitude, frequency)].
@raw_stream
def additive(parts, phase=0):
    return lambda: (sum(math.sin(phase*freq)*amplitude for amplitude, freq in parts), additive(parts, phase + 2*math.pi/SAMPLE_RATE))

# Anti-aliased: these only generate harmonics up to half the sample rate.
@stream
def aa_sqr(freq):
    return additive([(4/math.pi/k, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)])

@stream
def aa_tri(freq):
    return additive([((-1)**((k-1)/2)*8/math.pi**2/k**2, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)])


@stream
def aa_saw(freq):
    return additive([((-1)**k*2/math.pi/k, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1)])


# `w` for 'wrap'. a convenience function: lazify; ensure that a stream is recreated at play time.
# handy for livecoding (can affect a cycle by changing a variable/function live), and for streams that employ nondeterminism (like pluck with randbits) on creation.
def w(f):
    return Stream(lambda: f()())

# Freeze a stream and save the result to a file.
# If the file already exists, load it instead of running the stream.
# Like freeze(), assumes `stream` is finite.
@stream
def frozen(name, stream, redo=False, include_return=False):
    # Considered using a default name generated via `hash(stream_fn.__code__)`, but this had too many issues.
    # (Hashes differently between session, if referenced objects are created in the session.)
    if not redo:
        try:
            with open(f'frozen_{name}.pkl', 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            # File doesn't exist: stream hasn't been frozen before.
            redo = True
    if redo:
        it = iter(stream)
        # Try to freeze into an array, until we encounter an object that cannot be converted to float.
        items = array.array('d')
        for item in it:
            try:
                items.append(item)
            except TypeError:
                # Non-float item; switch from array to list.
                items = list(items)
                items.append(item)
                items.extend(it)
                break
        if include_return:
            # NOTE: This fails if the return value is not pickleable; as most streams are not pickleable, this will usually fail with slice.
            stream = FrozenStream(items, it.returned)
        else:
            stream = ListStream(items)
        with open(f'frozen_{name}.pkl', 'wb') as f:
            pickle.dump(stream, f)
        return stream

# This is similar to frozen(), but it records the stream *as it plays* rather than forcing the entire stream ahead of time.
# This is a critical distinction for any stream that depends on external time-varying state, such as audio.input_stream.
# Conceptually, record() is a cross between frozen() and memoize().
@stream
def record(name, stream, redo=False, include_return=False):
    if not redo:
        try:
            with open(f'record_{name}.pkl', 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            # File doesn't exist: stream hasn't been recorded before.
            redo = True
    if redo:
        final_stream = None
        # After the initial record finishes, we want to replay the
        # stored stream (rather than recording again or appending).
        def closure():
            if final_stream:
                return final_stream()
            else:
                recorded = []
                def finish(result):
                    nonlocal final_stream
                    if include_return:
                        final_stream = FrozenStream(recorded, result)
                    else:
                        final_stream = ListStream(recorded)
                    with open(f'record_{name}.pkl', 'wb') as f:
                        pickle.dump(final_stream, f)
                    return lambda: Return(result)
                return stream.map(lambda x: recorded.append(x) or x).bind(finish)()
        return closure

@stream
def log_stream(print_period=1):
    def maybe_print(x):
        if x % print_period == 0:
            print("Log:", x)
        return 0
    return count().map(maybe_print)


# Helper function to reduce boilerplate in the class definition below.
def make_frame_op(op, reversed=False):
    if reversed:
        def fn(self, other):
            if isinstance(other, frame):
                return frame(map(op, other, self))
            return frame(op(other, x) for x in self)
        return fn
    def fn(self, other):
        if isinstance(other, frame):
            return frame(map(op, self, other))
        return frame(op(x, other) for x in self)
    return fn

# Container for multiple values. Operators are overloaded for element-wise computation.
# Created with samples in mind (to make it easier to work with stereo and beyond), but can be used with any types.
# (e.g., frame('hell', 'good') + frame('o', 'bye') == frame('hello', 'goodbye'))
# NOTE: Could make this faster for the stereo case by specializing for the 2-channel frame.
class frame(tuple):
    __add__ = make_frame_op(operator.add)
    __radd__ = make_frame_op(operator.add, reversed=True)
    __sub__ = make_frame_op(operator.sub)
    __rsub__ = make_frame_op(operator.sub, reversed=True)
    __mul__ = make_frame_op(operator.mul)
    __rmul__ = make_frame_op(operator.mul, reversed=True)
    __matmul__ = make_frame_op(operator.matmul)
    __rmatmul__ = make_frame_op(operator.matmul, reversed=True)
    __truediv__ = make_frame_op(operator.truediv)
    __rtruediv__ = make_frame_op(operator.truediv, reversed=True)
    __floordiv__ = make_frame_op(operator.floordiv)
    __rfloordiv__ = make_frame_op(operator.floordiv, reversed=True)
    __mod__ = make_frame_op(operator.mod)
    __rmod__ = make_frame_op(operator.mod, reversed=True)
    __pow__ = make_frame_op(operator.pow)
    __rpow__ = make_frame_op(operator.pow, reversed=True)
    __lshift__ = make_frame_op(operator.lshift)
    __rlshift__ = make_frame_op(operator.lshift, reversed=True)
    __rshift__ = make_frame_op(operator.rshift)
    __rrshift__ = make_frame_op(operator.rshift, reversed=True)
    __and__ = make_frame_op(operator.and_)
    __rand__ = make_frame_op(operator.and_, reversed=True)
    __xor__ = make_frame_op(operator.xor)
    __rxor__ = make_frame_op(operator.xor, reversed=True)
    __or__ = make_frame_op(operator.or_)
    __ror__ = make_frame_op(operator.or_, reversed=True)
    def __neg__(self): return frame(map(operator.neg, self))
    def __pos__(self): return frame(map(operator.pos, self))
    def __abs__(self): return frame(map(operator.abs, self))
    def __invert__(self): return frame(map(operator.invert, self))

    def __new__(cls, *args):
        if len(args) > 1:
            # Multiple arguments: put them all in a frame.
            return tuple.__new__(cls, args)
        elif args:
            # One argument: assume it's a sequence that should be converted to a frame.
            return tuple.__new__(cls, args[0])
        else:
            return tuple.__new__(cls)

    def __repr__(self):
        return f"frame{super().__repr__()}"

    def __str__(self):
        return f"frame{super().__str__()}"

@stream
def pan(stream, pos):
    return stream.map(lambda x: frame(x * (1 - pos), x * pos))

@stream
def modpan(stream, pos_stream):
    return ZipStream((stream, pos_stream)).map(lambda p: frame(p[0] * (1 - p[1]), p[0] * p[1]))

@raw_stream
def zoh(stream, hold_time, prev_value=None, pos=0):
    # NOTE: hold_time must be an int
    def closure():
        if pos < 0:
            return (prev_value, zoh(stream, hold_time, prev_value, pos + 1))
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (value, zoh(next_stream, hold_time, value, pos - hold_time + 1))
    return closure

# TODO: Perhaps come up with another name for this, if it's worth keeping.
# def repeat(stream, n):
#     return ConcatStream([stream] * n)

# This is a function that can split a stream into multiple streams that will yield the same values.
# The tricky part is ensuring that we don't keep around excess memoized results.
# That is why this is wrapped in a lambda: consider the memory implications of the simpler definition,
# `splitter = lambda stream, receiver: receiver(memoize(stream))`
# The problem is that (assuming the result of splitter is stored) it retains a reference to the head of the memoize chain,
# which will keep the entire memoize chain in memory until that outer reference expires.
@stream
def splitter(stream, receiver):
    return lambda: receiver(memoize(stream))()

# NOTE: `return receiver(lambda: memoize(stream)())` would instead memoize separately for each invocation in the receiver - defeating the purpose of the splitter.
# also, should rename this 'tee'.

@stream
def repeat(f):
    @Stream
    def closure():
        return (f(), closure)
    return closure

