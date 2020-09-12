import math
import numpy as np
import pyaudio
import time


SAMPLE_RATE = 44100


class Stream:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self):
        return self.fn()

    def __rshift__(self, other):
        return concat(self, other)

    def __iter__(self):
        return StreamIterator(self)

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


def stream(f):
    return lambda *args, **kwargs: Stream(f(*args, **kwargs))


# The basics.
@stream
def concat(a, b):
    def closure():
        result = a()
        if isinstance(result, Return):
            return b()
        value, next_a = result
        return (value, concat(next_a, b))
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


# Synthesis functions.
silence = repeat(0)

def osc(freq):
    return count().map(lambda t: math.sin(2*math.pi*t*freq/SAMPLE_RATE))


# PyAudio stuff
def convert_time(time):
    if isinstance(time, float):
        return int(time * SAMPLE_RATE)
    return time

def callback(in_data, frame_count, time_info, status):
        audio = np.zeros(frame_count, dtype=np.float32)
        flag = pyaudio.paContinue
        for i, sample in zip(range(frame_count), callback.samples):
            audio[i] = sample
        if i < frame_count - 1:
            print("Finished playing.")
            flag = pyaudio.paComplete
        return (audio, flag)

# Blocking version; cleans up PyAudio and returns when the composition is finished.
def run(composition):
    callback.samples = iter(composition)
    buffer_size = 1024
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    frames_per_buffer=buffer_size,
                    rate=SAMPLE_RATE,
                    output=True,
                    stream_callback=callback)
    stream.start_stream()

    try:
        # Do whatever you want here.
        while stream.is_active():
            # print("Still going!")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Finishing early due to user interrupt.")

    stream.stop_stream()
    stream.close()
    p.terminate()

# Non-blocking version: setup() and play() are a pair. Works with the REPL.
def setup():
    callback.samples = silence
    buffer_size = 1024
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    frames_per_buffer=buffer_size,
                    rate=SAMPLE_RATE,
                    output=True,
                    stream_callback=callback)
    stream.start_stream()

def play(composition):
    callback.samples = iter(composition >> silence)


# Example:
#
# setup()
# play(osc(440)[:1.0] >> osc(660)[:1.0] >> osc(880)[:1.0])