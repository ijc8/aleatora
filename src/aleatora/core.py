# Aleatora is a music composition framework built around streams.
# In Python terms, streams are essentially rich iterables. As iterables, they are things which can construct iterators.
# A stream may be called upon to produce many iterators, each of which may yield a new sequence of values.
# Streams may or may not terminate, and they may or may not produce the same sequence of values on each iteration.
# Streams can be specified directly, by defining a class that implements __iter__ or by defining a generator function.
# Or, streams can be constructed out of other streams using the many functions that operate on streams, including overloaded operators.

import collections
import inspect
import itertools
import math
import operator


def _make_stream_op(op, reversed=False):
    if reversed:
        def fn(self, other):
            # No need to handle the iterable case, because it will be handled by the non-reversed version.
            return self.map(lambda v: op(other, v))
        return fn
    def fn(self, other):
        if isinstance(other, collections.Iterable):
            return self.zip(other).map(lambda p: op(*p))
        return self.map(lambda v: op(v, other))
    return fn

def stream(thing):
    if inspect.isgeneratorfunction(thing):
        return lambda *args, **kwargs: FunctionStream(lambda: thing(*args, **kwargs))
    elif isinstance(thing, collections.Iterable):
        return Stream(thing)

class Stream(collections.Iterable):
    def __init__(self, iterable):
        self.iterable = iterable
    
    def __iter__(self):
        return iter(self.iterable)

    def __len__(self):
        raise ValueError("Length unknown")

    def maxlen(self):
        return math.inf
    
    def minlen(self):
        return 0

    # `a >> b` means `a` followed by `b`: sequential composition.
    # For streams of audio samples, this is akin to splicing tape together, or arranging tracks horizontally in a DAW.
    def __rshift__(self, other):
        return ConcatStream((self, other))
    
    def __rrshift__(self, other):
        return ConcatStream((other, self))

    # The other operators behave differently with streams and other types.
    # If `other` is iterable, these operators will perform the operation element-wise along the stream and the other iterable.
    # If one argument is not a stream, the operators perform the same option (e.g. `* 2`) to each element along the one stream.

    # `a + b` means `a` and `b` at the same time.
    # For streams of audio samples, this is akin to mixing two tapes down to one, or arranging tracks vertically in a DAW.
    # Unlike *, /, etc., this operator keeps going until *both* streams have ended.
    def __add__(self, other):
        if isinstance(other, collections.Iterable):
            return MixStream([self, other])
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
    __rsub__ = _make_stream_op(operator.add, reversed=True)

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
    def map(self, fn):
       for x in self:
           yield fn(x)

    @stream
    def each(self, fn):
        for x in self:
            fn(x)
            yield x

    def zip(self, *others):
        return Stream(zip(self, *others))

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
    def cycle(self):
        while True:
            yield from self
    
    @stream
    def hold(self, duration):
        for x in self:
            for _ in range(duration):
                yield x

    @stream
    def reverse(self):
        # NOTE: Naturally, this requires evaluating the entire stream.
        # Calling this on an infinite stream will not result in a good time.
        return lambda: iter(list(self)[::-1])
    
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
            acc = 0
            for i in range(len(iterators) - 1, -1, -1):
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
        for _ in zip(it, range(self.start)): pass
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

@stream
def mod(modulus):
    while True:
        yield from range(modulus)

@FunctionStream
def empty():
    return
    yield  # marks this as a generator function


# Audio stuff (TODO: separate module)

# This is the default sample rate, but it may be modified by audio module to
# match what the audio device supports.
SAMPLE_RATE = 44100

silence = const(0)
ones = const(1)

@stream
def osc(freq, phase=0):
    while True:
        yield math.sin(phase)
        phase += 2*math.pi*freq/SAMPLE_RATE

# NOTE: Aliased. For versions that don't alias, see aa_{saw,sqr,tri}.
@stream
def saw(freq, t=0):
    while True:
        yield t*2 - 1
        t = (t + freq/SAMPLE_RATE) % 1

@stream
def sqr(freq, t=0):
    while True:
        yield int(t < 0.5)*2 - 1
        t = (t + freq/SAMPLE_RATE) % 1

@stream
def tri(freq, t=0):
    while True:
        yield abs(t - 0.5)*2 - 1
        t = (t + freq/SAMPLE_RATE) % 1

def basic_envelope(length):
    length = convert_time(length)
    ramp_time = int(length * 0.1)
    for x in range(0, ramp_time):
        yield x/ramp_time
    for _ in range(length - ramp_time*2):
        yield 1
    for x in range(ramp_time-1, -1, -1):
        yield x/ramp_time

def convert_time(time):
    if isinstance(time, float):
        return int(time * SAMPLE_RATE)
    return time

def m2f(midi):
    return 2**((midi - 69)/12) * 440

## TODO: EXPERIMENTAL - needs documentation & integration

@stream
def fm_osc(freq_stream, phase=0):
    for freq in freq_stream:
        yield math.sin(phase)
        phase += 2*math.pi*freq/SAMPLE_RATE

@stream
def glide(freq_stream, hold_time, transition_time, start_freq=0):
    tt = convert_time(transition_time)
    for freq in freq_stream:
        tt = convert_time(transition_time)
        transition = (count()[:tt] / tt) * (freq - start_freq) + start_freq
        hold = const(freq)[:hold_time]
        yield from transition >> hold
        start_freq = freq

def basic_sequencer(note_stream, bpm=80):
    # Assumes quarters have the beat.
    return note_stream.map(lambda n: sqr(m2f(n[0])) * basic_envelope(60.0 / bpm * n[1] * 4)).join()

@stream
def adsr(attack, decay, sustain_time, sustain_level, release):
    attack, decay, sustain_time, release = map(convert_time, (attack, decay, sustain_time, release))
    yield from (count() / attack())[:attack]  # Attack
    yield from (count()/decay * (1 - sustain_level) + sustain_level)[:decay]/decay  # Decay
    yield from (ones * sustain_level)[:sustain_time]  # Sustain
    yield from ((1 - count(1)/release) * sustain_level)[:release]  # Release

# This function produces a stream of exactly length, by trimming or padding as needed.
# Hypothetically, might also want a function that strictly pads (like str.ljust()).
# TODO: Add in length metadata?
def fit(stream, length):
    return (stream >> silence)[:length]

@stream
def pulse(freq, duty, t=0):
    while True:
        yield int(t < duty)*2 - 1
        t = (t + freq/SAMPLE_RATE) % 1

# TODO: conslidate? maybe introduce some constant-to-iterable helper function?
@stream
def fm_pulse(freqs, duty, t=0):
    for freq in freqs:
        yield int(t < duty)*2 - 1
        t = (t + freq/SAMPLE_RATE) % 1

rand = repeat(random.random)

def resample_list(list, rate, index=0):
    index = index % len(list)
    while True:
        integer = int(index)
        fraction = index - integer
        start = list[integer]
        end = list[(integer + 1) % len(list)]
        interp = start + (end - start) * fraction
        yield interp
        index += rate


# Stream-controlled resampler. Think varispeed.
@stream
def resample(stream, advance_stream):
    it = iter(stream)
    pos = 0
    sample = 0
    next_sample = next(it)
    for advance in advance_stream:
        pos += advance
        while pos > 1:
            sample = next_sample
            next_sample = next(it)
            pos -= 1
        yield sample + (next_sample - sample) * pos

# Linearly interpolate a series of points of the form [(time, value), (time, value)] into a "filled in" sequence of values.
@stream
def interp(stream):
    it = iter(stream)
    time = 0
    next_time = next_value = 0
    while True:
        time += 1
        while time >= next_time:
            prev_time, prev_value = next_time, next_value
            next_time, next_value = next(it)
            next_time = convert_time(next_time)
        yield prev_value + (next_value - prev_value) * (time - prev_time)/(next_time - prev_time)

def freeze(stream):
    print("Rendering...")
    t = time.time()
    r = list(stream)
    print("Done in", time.time() - t)
    return stream(r)

# Essentially a partial freeze of length 1.
# Useful for determining the number of channels automatically.
def peek(stream, default=None):
    it = iter(stream)
    try:
        x = next(it)
    except StopIteration:
        return (default, empty)
    # "Unpeek".
    return (x, stream([x]) >> it)

def branch(choices, default=empty):
    # choices is list [(weight, stream)]
    def helper():
        x = random.random()
        acc = 0
        for weight, stream in choices:
            acc += weight
            if acc >= x:
                return stream()
        return default()
    return FunctionStream(helper)

def flip(a, b):
    return branch([(0.5, a), (0.5, b)])

def pan(stream, pos):
    return stream.map(lambda x: (x * (1 - pos), x * pos))

def normalize(stream):
    # Requires evaluating the whole stream to determine the max volume.
    # Works for any number of channels.
    print('Rendering...')
    t = time.time()
    a = np.array(list(stream))
    print('Done in', time.time() - t)
    peak = np.max(np.abs(a))
    return stream(a / peak)

# Analagous to DAW timeline; takes a bunch of streams and their start times, and arranges them in a reasonably efficient way.
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
def cons(item, stream):
    return [item] >> stream

@stream
def just(item):
    yield item

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


FROZEN_PATH = 'frozen'

# Freeze a stream and save the result to a file.
# If the file already exists, load it instead of running the stream.
# Like freeze(), assumes `stream` is finite.
@stream
def frozen(name, stream, redo=False, include_return=False):
    os.makedirs(FROZEN_PATH, exists_ok=True)
    if not redo:
        try:
            # Considered using a default name generated via `hash(stream_fn.__code__)`, but this had too many issues.
            # (Hashes differently between session, if referenced objects are created in the session.)
            with open(os.path.join(FROZEN_PATH, f'frozen_{name}.pkl'), 'rb') as f:
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
    os.makedirs(FROZEN_PATH, exists_ok=True)
    if not redo:
        try:
            with open(os.path.join(FROZEN_PATH, f'record_{name}.pkl'), 'rb') as f:
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







## OLD:

# import array
# import inspect
# import math
# import time
# import operator
# import random
# import os
# import pickle

# import numpy as np

# # Preliminary magic for introspection.
# # This stuff is used by the assistant to list all streams, stream-creating functions, and instruments.

# # Registry of stream-creating functions.
# # There is no registry for streams themselves, because they can be identified by type (`isinstance(x, Stream)`).
# stream_registry = {}

# def make_namer(fn):
#     def closure(*args, **kwargs):
#         args = inspect.signature(fn).bind(*args, **kwargs).arguments
#         return f"{fn.__name__}({', '.join(f'{name}={value}' for name, value in args.items())})"
#     return closure

# # If `json` is a string, indicate a single parameter that should be sent to the assistant.
# # If `json` is any other iterable, indicate multiple parameters instead (sent in an object).
# def make_inspector(fn, json=None):
#     def closure(*args, **kwargs):
#         ba = inspect.signature(fn).bind(*args, **kwargs)
#         ba.apply_defaults()
#         d = {
#             "name": fn.__name__,
#             "parameters": ba.arguments,
#         }
#         if json is not None:
#             if isinstance(json, str):
#                 d["json"] = ba.arguments[json]
#             else:
#                 d["json"] = {param: ba.arguments[param] for param in json}
#         return d
#     return closure

# def register_stream(f, **kwargs):
#     if f.__module__ not in stream_registry:
#         stream_registry[f.__module__] = {}
#     f.metadata = kwargs
#     stream_registry[f.__module__][f.__qualname__] = f
#     return f

# # This wraps primitive streams (functions) and gives them namers/inspectors.
# # Namers/inspectors use Python's introspection features by default, but can be overriden for custom displays.
# # Assumes the decorated function is lazily recursive.
# # TODO: merge with @stream?
# def raw_stream(f=None, namer=None, inspector=None, register=True, json=None, **kwargs):
#     def wrapper(f):
#         nonlocal namer, inspector
#         namer = namer or make_namer(f)
#         inspector = inspector or make_inspector(f, json=json)
#         if register:
#             register_stream(f, **kwargs)
#         return lambda *args, **kwargs: NamedStream(namer, f(*args, **kwargs), args, kwargs, inspector)
#     if f:
#         return wrapper(f)
#     return wrapper

# # This is for naming streams that already return other streams (rather than beng lazily recursive).
# # NOTE: The NamedStream outer layer is only present at the start. Wrapping the entire stream creates excessive overhead.
# def stream(f=None, namer=None, inspector=None, register=True, json=None, **kwargs):
#     def wrapper(f):
#         nonlocal namer, inspector
#         namer = namer or make_namer(f)
#         inspector = inspector or make_inspector(f, json=json)
#         if register:
#             register_stream(f, **kwargs)
#         def inner(*args, **kwargs):
#             init_stream = f(*args, **kwargs)
#             def _inspector(*args, **kwargs):
#                 d = inspector(*args, **kwargs)
#                 d['implementation'] = init_stream
#                 return d
#             return NamedStream(namer, init_stream, args, kwargs, _inspector)
#         return inner
#     if f:
#         return wrapper(f)
#     return wrapper
