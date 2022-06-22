import array
import collections
import math
import numpy as np
import operator
import os
import pickle
import random
import time
from typing import overload

from .core import FunctionStream, const, count, empty, stream, Stream, repeat

# This is the default sample rate, but it may be modified by audio module to
# match what the audio device supports.
SAMPLE_RATE = 44100

def convert_time(time):
    if isinstance(time, float):
        return int(time * SAMPLE_RATE)
    return time

# db to gain, for amplitudes
def db(decibels):
    return 10**(decibels/20)

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


# Monkey-patch stream slicing, freezing, and recording onto Stream.
# Ideally, these would go in a subclass, but there are some unresolved problems there for Concat and Mix streams.

super_getitem = Stream.__getitem__

def AudioStream_getitem(self, index):
    # Unlike regular streams, audio streams support indexing and slicing by floats,
    # which are interpreted as seconds and converted to samples.
    if isinstance(index, slice):
        return super_getitem(self, slice(
            convert_time(index.start),
            convert_time(index.stop),
            convert_time(index.step)
        ))
    else:
        super_getitem(self, convert_time(index))

Stream.__getitem__ = AudioStream_getitem

super_hold = Stream.hold

def AudioStream_hold(self, duration):
    return super_hold(self, convert_time(duration))

Stream.hold = AudioStream_hold

def AudioStream_freeze(self, key=None, redo=False, verbose=False):
    return freeze(key, self, redo, verbose)

Stream.freeze = AudioStream_freeze

def AudioStream_record(self, key=None, redo=False):
    return record(key, self, redo)

Stream.record = AudioStream_record

def pan(stream, pos):
    if isinstance(pos, collections.abc.Iterable):
        return stream.map(lambda x, pos: frame(x * (1 - pos), x * pos), pos)
    return stream.map(lambda x: frame(x * (1 - pos), x * pos))

Stream.pan = pan

# Stream-controlled resampler. Think varispeed.
@stream
def resample(stream, rate):
    it = iter(stream)
    pos = 0
    sample = 0
    try:
        next_sample = next(it)
    except StopIteration as e:
        return e.value
    for advance in maybe_const(rate):
        pos += advance
        while pos > 1:
            sample = next_sample
            try:
                next_sample = next(it)
            except StopIteration as e:
                return e.value
            pos -= 1
        yield sample + (next_sample - sample) * pos

Stream.resample = resample

silence = const(0)
ones = const(1)

@stream
def mod(modulus):
    while True:
        yield from range(modulus)

def maybe_const(thing):
    if isinstance(thing, collections.abc.Iterable):
        return thing
    return const(thing)

@stream
def osc(freqs, phase=0):
    for freq in maybe_const(freqs):
        yield math.sin(phase)
        phase += 2*math.pi*freq/SAMPLE_RATE

# NOTE: Aliased. For versions that don't alias, see aa_{saw,sqr,tri}.
@stream
def saw(freqs, t=0):
    for freq in maybe_const(freqs):
        yield t*2 - 1
        t = (t + freq/SAMPLE_RATE) % 1

@stream
def sqr(freqs, t=0, duty=0.5):
    for freq in maybe_const(freqs):
        yield int(t < duty)*2 - 1
        t = (t + freq/SAMPLE_RATE) % 1

@stream
def tri(freqs, t=0):
    for freq in maybe_const(freqs):
        yield abs(t - 0.5)*4 - 1
        t = (t + freq/SAMPLE_RATE) % 1

@stream
def tbl(freqs, tables, phase=0):
    for freq, table in zip(maybe_const(freqs), tables):
        index = phase * len(table)
        prev = int(index)
        next = prev + 1
        frac = index - prev
        yield table[prev] * (1 - frac) + table[next % len(table)] * frac
        phase += freq/SAMPLE_RATE
        phase %= 1

@stream
def basic_envelope(length):
    length = convert_time(length)
    ramp_time = int(length * 0.1)
    for x in range(0, ramp_time):
        yield x/ramp_time
    for _ in range(length - ramp_time*2):
        yield 1
    for x in range(ramp_time-1, -1, -1):
        yield x/ramp_time

def m2f(midi):
    return 2**((midi - 69)/12) * 440

## TODO: EXPERIMENTAL - needs documentation & integration

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
def ramp(start, end, dur, hold=False):
    dur = convert_time(dur)
    for i in range(dur):
        yield start + (end - start)/dur*i
    if hold:
        while True:
            yield end

def adsr(attack, decay, sustain_time, sustain_level, release):
    attack, decay, sustain_time, release = map(convert_time, (attack, decay, sustain_time, release))
    return ramp(0, 1, attack) >> ramp(1, sustain_level, decay) >> const(sustain_level)[:sustain_time] >> ramp(sustain_level, 0, release)

# This function produces a stream of exactly length, by trimming or padding as needed.
# Hypothetically, might also want a function that strictly pads (like str.ljust()).
# TODO: Add in length metadata?
def fit(stream, length):
    return (stream >> silence)[:length]

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
            try:
                next_time, next_value = next(it)
            except StopIteration as e:
                return e.value
            next_time = convert_time(next_time)
        yield prev_value + (next_value - prev_value) * (time - prev_time)/(next_time - prev_time)

# Essentially a partial freeze of length 1.
# Useful for determining the number of channels automatically.
def peek(strm, default=None):
    it = iter(strm)
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
        for weight, strm in choices:
            acc += weight
            if acc >= x:
                return iter(strm)
        return iter(default)
    return FunctionStream(helper)

def flip(a, b):
    return branch([(0.5, a), (0.5, b)])

def normalize(strm):
    # Requires evaluating the whole stream to determine the max volume.
    # Works for any number of channels.
    print('Rendering...')
    t = time.time()
    a = np.array(list(strm))
    print('Done in', time.time() - t)
    peak = np.max(np.abs(a))
    return stream(a / peak)


class Mixer:
    """
    Supports dynamically connecting and disconnecting streams to output.
    This allows for a more imperative, ChucK-ish style.

    Example::

        @stream
        def example():
            out = Mixer()
            out <= osc(100)           # connect oscillator to output
            yield from out[:0.5]      # yield samples for 0.5 seconds

            handle = out <= osc(200)  # connect another oscillator, save handle
            yield from out[:0.5]      # yield for another 0.5 seconds

            out >= handle             # disconnect the last oscillator
            yield from out            # yield all the remaining output
    """
    def __init__(self, streams=[], fill=0):
        self.iterators = []
        for stream in streams:
            self <= stream
        self.fill = fill

    def __le__(self, stream):
        it = iter(stream)
        self.iterators.append(it)
        return it
    
    def __ge__(self, it):
        try:
            self.iterators.remove(it)
        except ValueError:
            # Iterator may have already been removed due to exhaustion.
            pass

    def __getitem__(self, item):
        assert(isinstance(item, slice))
        assert(item.start is None)
        assert(item.step is None)
        t = convert_time(item.stop)
        iterators = self.iterators
        fill = self.fill
        for _ in range(t):
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
                acc = fill
            yield acc
    
    def __iter__(self):
        # TODO: Reduce duplication between this, __getitem__(),
        #       and MixStream.__iter__().
        iterators = self.iterators
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

# Analagous to DAW timeline; takes a bunch of streams and their start times,
# and arranges them to start at those times and play simultaneously.
@stream
def arrange(items, fill=0):
    if not items:
        return empty
    items = sorted(items, key=lambda item: item[0])
    out = Mixer(fill=fill)
    last_time = 0
    for time, stream in items:
        yield from out[:time - last_time]
        out <= stream
        last_time = time
    yield from out

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
@stream
def additive(parts, phase=0):
    while True:
        yield sum(math.sin(phase*freq)*amplitude for amplitude, freq in parts)
        phase += 2*math.pi/SAMPLE_RATE

# Anti-aliased: these only generate harmonics up to half the sample rate.
def aa_sqr(freq):
    return additive([(4/math.pi/k, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)])

def aa_tri(freq):
    return additive([((-1)**((k-1)/2)*8/math.pi**2/k**2, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)])

def aa_saw(freq):
    return additive([((-1)**k*2/math.pi/k, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1)])

# Decorator for hot-swappable functions.
HOT_STREAMS = {}
def hot(f):
    HOT_STREAMS[f.__qualname__] = f
    return lambda: HOT_STREAMS[f.__qualname__]()


FROZEN_PATH = 'frozen'

@overload
def freeze(strm, verbose=False):
    ...
@overload
def freeze(key: str, strm, redo=False, verbose=False):
    ...
def freeze(key=None, strm=None, redo=False, verbose=False):
    """Freeze a stream and optionally save the result to a file. Assumes `stream` is finite.

    If the file already exists, load it instead of running the stream, unless redo=True.
    """
    if strm is None:
        # First overload.
        strm = key
        key = None
    if key is None:
        t = time.time()
        r = list(strm)
        if verbose:
            print("Done in", time.time() - t)
        return stream(r)
    os.makedirs(FROZEN_PATH, exist_ok=True)
    path = os.path.join(FROZEN_PATH, f'frozen_{key}.pkl')
    if not redo:
        try:
            # Considered using a default name generated via `hash(stream_fn.__code__)`, but this had too many issues.
            # (Hashes differently between session, if referenced objects are created in the session.)
            with open(path, 'rb') as f:
                return Stream(pickle.load(f))
        except FileNotFoundError:
            # File doesn't exist: stream hasn't been frozen before.
            pass
    t = time.time()
    it = iter(strm)
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
    if verbose:
        print("Done in", time.time() - t)
    with open(path, 'wb') as f:
        pickle.dump(items, f)
    return Stream(items)

# This is similar to frozen(), but it records the stream *as it plays* rather than forcing the entire stream ahead of time.
# This is a critical distinction for any stream that depends on external time-varying state, such as audio.input_stream.
# Conceptually, record() is a cross between frozen() and memoize().
@overload
def record(stream, verbose=False):
    ...
@overload
def record(key: str, stream, redo=False, verbose=False):
    ...
def record(key=None, stream=None, redo=False):
    if stream is None:
        # First overload.
        stream = key
        key = None
    if key is not None:
        os.makedirs(FROZEN_PATH, exist_ok=True)
        path = os.path.join(FROZEN_PATH, f'record_{key}.pkl')
        if not redo:
            try:
                with open(path, 'rb') as f:
                    return pickle.load(f)
            except FileNotFoundError:
                # File doesn't exist: stream hasn't been recorded before.
                pass
    final_stream = None
    # After the initial record finishes, we want to replay the
    # stored stream (rather than recording again or appending).
    def helper():
        if final_stream:
            return iter(final_stream)
        else:
            recorded = []
            def finish(_):
                nonlocal final_stream
                final_stream = Stream(recorded)
                if key is not None:
                    with open(path, 'wb') as f:
                        pickle.dump(final_stream, f)
                return empty
            return iter(stream.map(lambda x: recorded.append(x) or x).bind(finish))
    return FunctionStream(helper)


# Functions for generating compositions from directly from waveform functions.
# Examples:
#     bytebeat(lambda t: ((t >> 10) & 42) * t, 8000)
#     kilobeat(lambda t: sin(2*math.pi*300*t))

def floatbeat(fn):
    return count().map(fn)

def bytebeat(fn, sample_rate=None):
    stream = floatbeat(lambda t: (fn(t) % 255) / 255.0 * 2 - 1)
    if sample_rate is not None:
        stream = stream.resample(sample_rate / SAMPLE_RATE)
    return stream

def kilobeat(fn):
    return floatbeat(lambda t: fn(t / SAMPLE_RATE))
