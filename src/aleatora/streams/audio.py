import array
import math
import numpy as np
import operator
import os
import pickle
import random
import time

from .core import FunctionStream, const, count, empty, stream, Stream, repeat

# This is the default sample rate, but it may be modified by audio module to
# match what the audio device supports.
SAMPLE_RATE = 44100

def convert_time(time):
    if isinstance(time, float):
        return int(time * SAMPLE_RATE)
    return time

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


# Monkey-patch stream slicing.
# Ideally, this would go in a subclass, but there are some unresolved problems there for Concat and Mix streams.
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

def pan(stream, pos):
    return stream.map(lambda x: frame(x * (1 - pos), x * pos))

def modpan(stream, pos_stream):
    return stream.map(lambda x, pos: frame(x * (1 - pos), x * pos), pos_stream)

silence = const(0)
ones = const(1)

@stream
def mod(modulus):
    while True:
        yield from range(modulus)

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

def freeze(strm, verbose=False):
    if verbose:
        t = time.time()
    r = list(strm)
    if verbose:
        print("Done in", time.time() - t)
    return stream(r)

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

# Freeze a stream and save the result to a file.
# If the file already exists, load it instead of running the stream.
# Like freeze(), assumes `stream` is finite.
@stream
def frozen(name, stream, redo=False):
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
        stream = Stream(items)
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
                def finish(_):
                    nonlocal final_stream
                    final_stream = Stream(recorded)
                    with open(f'record_{name}.pkl', 'wb') as f:
                        pickle.dump(final_stream, f)
                    return empty
                return stream.map(lambda x: recorded.append(x) or x).bind(finish)()
        return closure

# TODO: This will need rework.
# This is a function that can split a stream into multiple streams that will yield the same values.
# The tricky part is ensuring that we don't keep around excess memoized results.
# That is why this is wrapped in a lambda: consider the memory implications of the simpler definition,
# `splitter = lambda stream, receiver: receiver(memoize(stream))`
# The problem is that (assuming the result of splitter is stored) it retains a reference to the head of the memoize chain,
# which will keep the entire memoize chain in memory until that outer reference expires.
@stream
def splitter(stream, receiver):
    return lambda: receiver(stream.memoize())()
