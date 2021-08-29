from .streams import maybe_const, SAMPLE_RATE, stream

import collections
import math


# For reference:
# https://www.musicdsp.org/en/latest/Filters/142-state-variable-filter-chamberlin-version.html
# Seems unstable at 1/2 of Nyquist (1/4 of sampling rate)

@stream
def svf(stream, freq, q):
    assert(q >= 0.5)
    low = band = 0
    for x, f in zip(stream, maybe_const(freq)):
        f1 = 2*math.sin(math.pi * f / SAMPLE_RATE)
        # Faster approximation:
        # f1 = 2*math.pi*f/SAMPLE_RATE
        low += f1 * band
        high = x - low - 1/q * band
        band += f1 * high
        yield (low, high, band)

def lpf(stream, f, q):
    return svf(stream, f, q).map(lambda p: p[0])

def hpf(stream, f, q):
    return svf(stream, f, q).map(lambda p: p[1])

def bpf(stream, f, q):
    return svf(stream, f, q).map(lambda p: p[2])

def notch(stream, f, q):
    return svf(stream, f, q).map(lambda p: p[0] + p[1])

@stream
def comb(stream, amp, delay):
    "Comb filter: delay >= 0 for feedforward, delay < 0 for feedback. Expects integer delay."
    if delay >= 0:
        # Feedforward
        buf = [0] * (delay + 1)
        index = 0
        for x in stream:
            buf[index] = x
            yield x + amp * buf[(index - delay) % len(buf)]
            index = (index + 1) % len(buf)
    else:
        # Feedback (note that a delay of 0 would be invalid here, as it would cause a zero-delay cycle).
        delay = -delay
        buf = [0] * (delay + 1)
        index = 0
        for x in stream:
            buf[index] = x + amp * buf[(index - delay) % len(buf)]
            yield buf[index]
            index = (index + 1) % len(buf)

# More generic:
def feed(stream, buffer_size, fn):
    buf = [0] * buffer_size
    index = 0
    for x in stream:
        y, b = fn(x, buf, index)
        yield y
        buf[index] = b
        index = (index + 1) % len(buf)


def var_comb(stream, amp, delay_stream, max_delay):
    def fn(p, buf, index):
        x, delay = p
        # Linear interpolation for fractional delays.
        index = (index - abs(delay)) % len(buf)
        iindex = int(index)
        a = index - iindex
        y = x + amp * ((1-a) * buf[iindex] + a * buf[(iindex + 1) % len(buf)])
        if delay >= 0:
            return y, x
        else:
            return y, y
    return feed(stream.zip(delay_stream), max_delay + 1, fn)


# play(bpf(rand, 1000 + 500 * osc(0.1), 5))
# play(bpf(rand, 2000 + 500 * (osc(1000) + osc(0.1)), 100))
# play(notch(rand, 1000 + 500 * osc(0.1), 0.5))
