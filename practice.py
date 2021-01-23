# 1/20/2021

from core import *
from audio import *

# weird - bathroom fan has strong 440 component
play(osc(440))
play(silence)

# From core.py
def basic_sequencer(note_stream, bpm=80):
    # Assumes quarters have the beat.
    return lazy_concat(note_stream.map(lambda n: sqr(m2f(n[0])) * basic_envelope(60.0 / bpm * n[1] * 4)))

tones0 = [(70, 1), (70, 1), (70, 1)]
tones1 =  [(70, 1), (69, 2), (68, 2), (65, 1), (63, 1), (61, 2)]
tones2 = [(63, 1), (65, 1), (66, 2), (63, 1), (61, 1), (60, 2), (61, 1), (63, 1), (65, 2)]
tones = tones0 + tones1 + tones2
play(basic_sequencer(list_to_stream(tones), bpm=900))
#play(ConcatStream([sqr(m2f(tone)) for tone in tones]))

# Instrument: take (pitch, duration), return stream
# Oscillator: take pitch, return stream
# Envelope: take duration, return stream
def make_instrument(oscillator, envelope):
    return lambda n: oscillator(m2f(n[0])) * envelope(n[1])

# 1/22/2021
def to_stream(x):
    if isinstance(x, Stream):
        return x
    return list_to_stream(x)

def sequence(notes, instrument, bpm=80):
    return lazy_concat(to_stream(notes).map(lambda n: instrument((n[0], 60.0 / bpm * n[1]))))

inst = make_instrument(lambda f: sqr(f)/4 + tri(f)*3/4, basic_envelope)
play(sequence(tones, inst, bpm=200))

# BPM in context? `with`? how to make it lexical?

# FM envelope
# https://web.eecs.umich.edu/~fessler/course/100/misc/chowning-73-tso.pdf fig. 10
def fm(freq, mod_idx_mult, envelope, dev1=0):
    return fm_osc(freq + (dev1 + mod_idx_mult * envelope) * osc(freq)) * envelope

test0 = freeze(fm(440, 0, basic_envelope(2.0)))
play(test0)
test1 = freeze(fm(440, 1, basic_envelope(2.0)))
play(test1)
test2 = freeze(fm(440, 10, basic_envelope(2.0)))
play(test2)
test3 = freeze(fm(440, 50, basic_envelope(2.0)))
play(test3)
test4 = freeze(fm(440, 100, basic_envelope(2.0)))
play(test4)
test5 = freeze(fm(440, 500, basic_envelope(2.0)))
play(test5)
test6 = freeze(fm(440, 1000, basic_envelope(10.0)))
play(test6)