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

@stream("svf_proto")
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

@stream("svf")
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

def notch_filter(stream, f, q):
    return svf(stream, f, q).map(lambda p: p[0] + p[1])

# play(bpf(rand, 1000 + 500 * osc(0.1), 5))
# play(bpf(rand, 2000 + 500 * (osc(1000) + osc(0.1)), 100))
# play(notch_filter(rand, 1000 + 500 * osc(0.1), 0.5))