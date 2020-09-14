import core
import functools
import numpy as np
import os

# TODO: move this stuff to core.py.
def concat(streams):
    return functools.reduce(lambda x, y: y >> x, list(streams)[::-1])

def m2f(midi):
    return 2**((midi - 69)/12) * 440

def cycle(stream):
    return stream >> (lambda: cycle(stream)())

def list_to_stream(l):
    @core.stream
    def streamer(index=0):
        def closure():
            if index == len(l):
                return core.Return()
            return (l[index], streamer(index+1))
        return closure
    return streamer()

def simple_envelope(length):
    if isinstance(length, float):
        length = int(length * core.SAMPLE_RATE)
    ramp_time = int(core.SAMPLE_RATE * 0.01)
    assert(length >= ramp_time * 2)
    ramp = np.linspace(0, 1, ramp_time)
    envelope = np.concatenate((ramp, np.ones(length - ramp_time*2), ramp[::-1]))
    return list_to_stream(envelope)

notes = [64, 66, 71, 73, 74, 66, 64, 73, 71, 66, 74, 73]
def loop(rate):
    dur = 60/72/6 * rate
    return cycle(concat((core.osc(m2f(note)) * simple_envelope(dur)) for note in notes))

piano_phase = (loop(rate=1) + loop(rate=1.01))/2

if __name__ == '__main__':
    core.run(piano_phase, buffer_size=8192)