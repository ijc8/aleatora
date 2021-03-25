from core import *

import numpy as np

import math


# For reference:
# https://www.musicdsp.org/en/latest/Filters/142-state-variable-filter-chamberlin-version.html
# Seems unstable at 1/2 of Nyquist (1/4 of sampling rate)
def svf_block(input, sample_rate, f, q):
    """Chamberlin state-variable filter.

    input: input array
    sample_rate: sample rate
    f: center frequency
    q: resonance parameter
    """

    # q goes from .5 to infinity; q1 goes from 2 to 0.
    q1 = 1/q
    #f1 = 2*math.pi*f/sample_rate
    # ideal tuning:
    f1 = 2*math.sin(math.pi * f / sample_rate)

    low, high, band, notch = np.zeros((4, len(input)))

    d1, d2 = 0, 0
    for i in range(len(input)):
        low[i] = d2 + f1 * d1
        high[i] = input[i] - low[i] - q1*d1
        band[i] = f1 * high[i] + d1
        notch[i] = high[i] + low[i]

        # store delays
        d1 = band[i]
        d2 = low[i]

    return low, high, band, notch

@raw_stream
def svf_proto(stream, f, q, prev_low=0, prev_band=0):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        x, next_stream = result

        f1 = 2*math.sin(math.pi * f / SAMPLE_RATE)
        low = prev_low + f1 * prev_band
        high = x - low - 1/q * prev_band
        band = f1 * high + prev_band
        # notch = high + low
        return ((low, high, band), svf(next_stream, f, q, low, band))
    return closure

@raw_stream
def svf(stream, f_stream, q, prev_low=0, prev_band=0):
    assert(q >= 0.5)
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        x, next_stream = result

        result = f_stream()
        if isinstance(result, Return):
            return result
        f, next_f_stream = result

        # f1 = 2*math.sin(math.pi * f / SAMPLE_RATE)
        f1 = 2*math.pi*f/SAMPLE_RATE
        low = prev_low + f1 * prev_band
        high = x - low - 1/q * prev_band
        band = f1 * high + prev_band
        # notch = high + low
        return ((low, high, band), svf(next_stream, next_f_stream, q, low, band))
    return closure

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
        def f(x):
            nonlocal index
            buf[index] = x
            y = x + amp * buf[(index - delay) % len(buf)]
            index = (index + 1) % len(buf)
            return y
    else:
        # Feedback (note that a delay of 0 would be invalid here, as it would cause a zero-delay cycle).
        delay = -delay
        buf = [0] * (delay + 1)
        index = 0
        def f(x):
            nonlocal index
            y = x + amp * buf[(index - delay) % len(buf)]
            buf[index] = y
            index = (index + 1) % len(buf)
            return y
    return stream.map(f)

# More generic:
def feed(stream, buffer_size, fn):
    buf = [0] * buffer_size
    index = 0
    def f(x):
        nonlocal index
        y, b = fn(x, buf, index)
        buf[index] = b
        index = (index + 1) % len(buf)
        return y
    return stream.map(f)


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
    return filters.feed(stream.zip(delay_stream), max_delay + 1, fn)


# play(bpf(rand, 1000 + 500 * osc(0.1), 5))
# play(bpf(rand, 2000 + 500 * (osc(1000) + osc(0.1)), 100))
# play(notch(rand, 1000 + 500 * osc(0.1), 0.5))