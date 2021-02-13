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

# 1/23/2021

def fm(envelope, freq, mod_freq, mod_idx1, mod_idx2):
    # P3 = length of envelope
    # P5 = freq
    # P6 = mod_freq
    # P7 = mod_idx1
    # P8 = mod_idx2
    dev1 = mod_idx1 * mod_freq
    dev2 = (mod_idx2 - mod_idx1) * mod_freq
    return fm_osc(freq + (dev1 + dev2 * envelope) * osc(mod_freq)) * envelope

brass_env = lambda dur: adsr(dur/6, dur/6, dur/2, 3/4, dur/6)
play(fm(brass_env(.6), 440, 440, 0, 5))
brass_inst = lambda n: fm(brass_env(n[1]), m2f(n[0]), m2f(n[0]), 0, 5)
play(sequence(tones, brass_inst, bpm=200))

import graph
graph.plot(brass_env(.5))

# not too bad, actually!

woodwind_env = lambda dur: adsr(dur/5, 0, dur*7/10, 1, dur/10)
play(fm(woodwind_env(.6), 900, 300, 0, 2))
woodwind_inst = lambda n: fm(woodwind_env(n[1]), m2f(n[0]), m2f(n[0])/3 + .5, 0, 2)
play(sequence(tones, lambda n: woodwind_inst((n[0] + 12, n[1])), bpm=200))

# 1/25/2021

bell_env = lambda d: count().map(lambda i: 1-math.log10(1 + 9*(i/44100)/d))[:d]
graph.plot(bell_env(15.0))
play(fm(bell_env(15.0), 200, 280, 0, 10))

bell_inst = lambda n: fm(bell_env(n[1]), m2f(n[0]), m2f(n[0])*1.4, 0, 10)
play(sequence(tones, bell_inst, bpm=200))

drum_env = bell_env
drum_env = lambda d: adsr(d/4, d/4, 0, 0.1, d/2)
drum_env = lambda d: interp([(0, 0.9), (d/8, 0.9), (d/4, 1), (d/2, 0.1), (d, 0)])

graph.plot(drum_env(.2))
play(fm(drum_env(.2), 200, 280, 0, 2))
drum_inst = lambda n: fm(drum_env(n[1]), m2f(n[0]), m2f(n[0])*1.4, 0, 2)
play(sequence(tones, drum_inst, bpm=200))

# Neat; can switch out which drum_env is used during playback! Livecoding-ish.

# To do this right, need separate envelopes for amplitude and mod index.
# In the meantime, this is funky:
wooddrum_env = bell_env
play(fm(wooddrum_env(.2), 80, 55, 0, 25))
wooddrum_inst = lambda n: fm(wooddrum_env(n[1]), m2f(n[0]), m2f(n[0])*11/16, 0, 25)
play(sequence(tones, wooddrum_inst, bpm=200))
play(silence)

# 1/26/2021

def fm(envelope, freq, mod_freq, mod_idx1, mod_idx2, mod_envelope=None):
    # P3 = length of envelope
    # P5 = freq
    # P6 = mod_freq
    # P7 = mod_idx1
    # P8 = mod_idx2
    dev1 = mod_idx1 * mod_freq
    dev2 = (mod_idx2 - mod_idx1) * mod_freq
    if mod_envelope is None:
        mod_envelope = envelope
    return fm_osc(freq + (dev1 + dev2 * mod_envelope) * osc(mod_freq)) * envelope

wooddrum_env = drum_env
wooddrum_mod_env = lambda d: interp([(0, 1), (.2/8, 0), (d, 0)])
graph.plot(wooddrum_env(.2))
play(cycle(fm(wooddrum_env(.2), 80, 55, 0, 25, wooddrum_mod_env(.2))))
wooddrum_inst = lambda n: fm(wooddrum_env(n[1]), m2f(n[0]), m2f(n[0])*11/16, 0, 25, wooddrum_mod_env(n[1]))
play(sequence(tones, lambda n: wooddrum_inst((n[0] - 12, n[1])), bpm=200))
play(silence)

# Hm. 25 seems a bit wide?
# Ah, I think the envelopes should not be proportional to note duration, because it's percussion.
# More tomorrow.

# 1/28/2021
# Let's regroup:
from core import *
from audio import *
import graph

def make_instrument(oscillator, envelope):
    return lambda n: oscillator(m2f(n[0])) * envelope(n[1])

def to_stream(x):
    if isinstance(x, Stream):
        return x
    return list_to_stream(x)

def sequence(notes, instrument, bpm=80):
    return lazy_concat(to_stream(notes).map(lambda n: instrument((n[0], 60.0 / bpm * n[1]))))

def fm(envelope, freq, mod_freq, mod_idx1, mod_idx2, mod_envelope=None):
    dev1 = mod_idx1 * mod_freq
    dev2 = (mod_idx2 - mod_idx1) * mod_freq
    if mod_envelope is None:
        mod_envelope = envelope
    return fm_osc(freq + (dev1 + dev2 * mod_envelope) * osc(mod_freq)) * envelope

tones0 = [(70, 1), (70, 1), (70, 1)]
tones1 =  [(70, 1), (69, 2), (68, 2), (65, 1), (63, 1), (61, 2)]
tones2 = [(63, 1), (65, 1), (66, 2), (63, 1), (61, 1), (60, 2), (61, 1), (63, 1), (65, 2)]
tones = tones0 + tones1 + tones2

brass_env = lambda dur: adsr(dur/6, dur/6, dur/2, 3/4, dur/6)
woodwind_env = lambda dur: adsr(dur/5, 0, dur*7/10, 1, dur/10)
bell_env = lambda d: count().map(lambda i: 1-math.log10(1 + 9*(i/44100)/d))[:d]
drum_env = lambda d: interp([(0, 0.9), (d/8, 0.9), (d/4, 1), (d/2, 0.1), (d, 0)])
wooddrum_env = drum_env
wooddrum_mod_env = lambda d: interp([(0, 1), (.2/8, 0), (d, 0)])

brass_inst = lambda n: fm(brass_env(n[1]), m2f(n[0]), m2f(n[0]), 0, 5)
woodwind_inst = lambda n: fm(woodwind_env(n[1]), m2f(n[0]), m2f(n[0])/3 + .5, 0, 2)
bell_inst = lambda n: fm(bell_env(n[1]), m2f(n[0]), m2f(n[0])*1.4, 0, 10)
drum_inst = lambda n: fm(drum_env(n[1]), m2f(n[0]), m2f(n[0])*1.4, 0, 2)
wooddrum_inst = lambda n: fm(wooddrum_env(n[1]), m2f(n[0]-12), m2f(n[0]-12)*11/16, 0, 25, wooddrum_mod_env(n[1]))

play(sequence(tones, lambda n: woodwind_inst((n[0], n[1])), bpm=200))
play(silence)

# Now, here's a wacky idea. What if we change the instrument over time?
# Of course, we could write a special-purpose version of sequence that expects a stream of instruments.
# Something like:
def stream_sequence(notes, instrument_stream, bpm=80):
    return lazy_concat(ZipStream((instrument_stream, to_stream(notes)))
            .map(lambda p: p[0]((p[1][0], 60.0 / bpm * p[1][1]))))

play(stream_sequence(tones, cycle(to_stream([drum_inst, wooddrum_inst])), bpm=200))

# Funky.
# But more generally, can we provide a nice way to schedule these kinds of changes with streams,
# even for functions that weren't expecting to get streams?
# My (hacky) idea: a stream that latches onto another and goes along for the ride, but updates external state.
# For the updates, perhaps it can use another stream.
# Like so:
def bind(stream, state_stream):
    def update(p):
        value, state = p
        nonlocal self
        self.state = state
        foo = state
        return value
    self = ZipStream((stream, state_stream)).map(update)
    return self

bound = bind(to_stream(tones), cycle(to_stream([drum_inst, wooddrum_inst])))
play(sequence(bound, lambda n: bound.state(n), bpm=200))

# bind causes streaming to produce side effects
# bind's other half is the stream that always returns external state;
# that is, a function that causes side effects to produce streams.

# This duo probably isn't the right way to build autonomous compositions,
# but I suspect it will be very useful for livecoding, interactive compositions, etc.

# 1/30/21

play(silence)
play(cycle(wooddrum_inst((60, 1/2))))
addplay(cycle(wooddrum_inst((63, 1/4))))
volume(0.2)
# This is wild:
play(cycle(wooddrum_inst((67, 1)))/2)
# It's becuase 1 is an integer, and is interpreted as a number of samples.

play(cycle(wooddrum_inst((60, 1/2))))
addplay(cycle(wooddrum_inst((63, 1/4))))
addplay(cycle(wooddrum_inst((67, 1.))))
addplay(cycle(wooddrum_inst((69, 1.))))
addplay(cycle(wooddrum_inst((70, 1.5))))
play(silence)

# Fun.
from rhythm import *
sound = wooddrum_inst((70, 1/2))
play(cycle(beat('xxx.xx.x.xx.', sound)), cycle(beat('x.xx.xxx.xx.', sound)))

def clapping():
    pattern = 'xxx.xx.x.xx.'
    # To make each offset repeat 8 times before proceeding, just do `pattern *= 8`.
    clap = wooddrum_inst((70, 3/4))
    return ZipStream((cycle(beat(pattern, clap, bpm=300)), cycle(beat(pattern + '.', clap, bpm=300))))

play(silence)
play(clapping())

# 2/1/21

from rhythm import *
sound = wooddrum_inst((70, 1/2))
play(cycle(beat('xxx.xx.x.xx.', sound)), cycle(beat('x.xx.xxx.xx.', sound)))

def clapping():
    pattern = 'xxx.xx.x.xx.' * 8
    clap = wooddrum_inst((70, 3/4))/2
    # Mark the beginning of each new offset:
    click = wooddrum_inst((94, 1/4))/2
    return ZipStream((cycle(beat(pattern, clap, bpm=300) + click), cycle(beat(pattern + '.', clap, bpm=300))))

# What about something that can 'control-rate-ify' an audio signal?
# i.e., compute 1/n as many values, but hold each value for n samples.
# Here's something in the ballpark:
play(resample(osc(440*10), const(1/10)))
# This stretches out a 4400 Hz sine wave into a (bad, linearly interpolated) 440 Hz one.
graph.plot(resample(osc(440*10)[:0.01], const(1/10)))
# Something funky going on here.

import core

@raw_stream()
def change_rate(stream, factor):
    def wrapper():
        # TODO: use `with` here?
        old = core.SAMPLE_RATE
        try:
            core.SAMPLE_RATE *= factor
            result = stream()
            if isinstance(result, Return):
                return result
            value, next_stream = result
            return (value, change_rate(next_stream, factor))
        finally:
            core.SAMPLE_RATE = old
    return wrapper

# Here we have a thing that puts all the computations of a stream in a bubble with a different apparent sample rate.
play(change_rate(osc(440), 8))
# Could combine with resample or a ZOH version to produce the desired effect.

# 2/2/21
from core import *
from audio import *
from prof import profile

profile.reset()
play(profile('changed', change_rate(osc(440), 8))[:1.0])
play(profile('original', osc(440))[:1.0])
profile.dump()

def undersample(stream, factor):
    return resample(change_rate(stream, 1/factor), const(1/factor))

setup()
play(silence)
play(osc(440))
play(undersample(osc(440), 1))
play(undersample(osc(440), 2))
play(undersample(osc(440), 4))
play(undersample(osc(440), 8))
play(undersample(osc(440), 16))
play(undersample(osc(440), 32))
play(undersample(osc(440), 64))
play(undersample(osc(440), 128))
play(undersample(osc(440), 256))
play(undersample(osc(440), 512))

profile.reset()
play(profile('original', osc(440))[:1.0])
play(profile('changed', undersample(osc(440), 128))[:1.0])
profile.dump()

# Interesting; looks like resample itself (or resample + change_rate) is slower than osc, so no benefit from undersampling.
# Let's try a simpler procedure.

def zoh(stream, factor):
    # NOTE: factor must be an int.
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (const(value)[:factor] >> zoh(next_stream, factor))()
    return closure

def undersample(stream, factor):
    return zoh(change_rate(stream, 1/factor), factor)

# Hm; this version is much slower!

def zoh(stream, factor):
    # NOTE: factor must be an int.
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (value, list_to_stream([value] * (factor-1)) >> zoh(next_stream, factor))
    return closure

# Slightly better, but still worse than resample!
# Is concat the issue?

def zoh(stream, hold_time, prev_value=None, pos=0):
    # NOTE: hold_time must be an int
    def closure():
        if pos < 0:
            return (prev_value, zoh(stream, hold_time, prev_value, pos + 1))
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (value, zoh(next_stream, hold_time, value, pos - hold_time))
    return closure

# ^ This is buggy in a way that produces an interesting pitch sequence as hold_time is incremented.
# Ah, it's holding for one sample too many.

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

# Now this is faster than resample. Interesting.

profile.reset()
list(profile('original', osc(440))[:10.0] >>
    profile('/1', undersample(osc(440), 1))[:10.0] >>
    profile('/2', undersample(osc(440), 2))[:10.0] >>
    profile('/16', undersample(osc(440), 16))[:10.0] >>
    profile('/128', undersample(osc(440), 128))[:10.0])
profile.dump()

# Also interesting: these do look better than just osc, and the budget percentage goes down noticeably when Python isn't responsible for playing the samples (just computing them).
# Perhaps, for the assistant, it will be worthwhile to send chunks of samples to the client for playback?

# 2/3/21
import core
from core import *
from audio import *
from prof import profile

def change_rate(stream, factor):
    def wrapper():
        # TODO: use `with` here?
        old = core.SAMPLE_RATE
        try:
            core.SAMPLE_RATE *= factor
            result = stream()
            if isinstance(result, Return):
                return result
            value, next_stream = result
            return (value, change_rate(next_stream, factor))
        finally:
            core.SAMPLE_RATE = old
    return wrapper

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

def undersample(stream, factor):
    return zoh(change_rate(stream, 1/factor), factor)

play(silence)
profile.reset()
list(profile('original', osc(440))[:10.0] >>
    profile('/1', undersample(osc(440), 1))[:10.0] >>
    profile('/2', undersample(osc(440), 2))[:10.0] >>
    profile('/16', undersample(osc(440), 16))[:10.0] >>
    profile('/128', undersample(osc(440), 128))[:10.0])
profile.dump()

# Now, without the change_rate layer:
profile.reset()
list(profile('original', osc(440))[:10.0] >>
    profile('/1', zoh(osc(440), 1))[:10.0] >>
    profile('/2', zoh(osc(440*2), 2))[:10.0] >>
    profile('/16', zoh(osc(440*16), 16))[:10.0] >>
    profile('/128', zoh(osc(440*128), 128))[:10.0])
profile.dump()

# Doesn't seem to make much difference.
# (Held off on making these @raw_streams while investigating performance.)

# Ooh check it out: can use this to explicitly go from continuous to discrete.
play(fm_osc(440 + 100*Stream(zoh(osc(10000), 10000))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 100))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 3000))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 4000))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 5000))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 6000))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 7000))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 8000))))
play(fm_osc(440 + 100*Stream(undersample(osc(1), 15000))))

# Same kind of effect with resample:
play(resample(osc(440), 1 + .2*osc(1)))
play(resample(sqr(440), 1 + .2*Stream(undersample(osc(1), 2800))))

import wav
s = list_to_stream(wav.load_mono('samples/a.wav')[40000:90000])
import graph
graph.plot(s)
play(s)
play(resample(cycle(s), 1 + .4*osc(1.2)))
play(resample(cycle(s), 1 + .4*Stream(undersample(osc(1.2), 3000))))
# Fun! Should try this with "Glooo, o o o o o, o o o o o, o o o o oooorr ia "


# 2/5
from core import *
from audio import *
from prof import profile

# Naive implementation: no flattening
def my_concat(a, b):
    def closure():
        result = a()
        if isinstance(result, Return):
            return b()
        value, next_a = result
        return (value, my_concat(next_a, b))
    return closure

profile.reset()
list(profile('c', silence[:100.0] >> silence[:100.0]))
list(profile('m', my_concat(silence[:100.0], silence[:100.0])))
profile.dump()

# Looks like the current concat is fine.
# And, of course, it's better in this situation:
s = silence[:100.0]
profile.reset()
list(profile('c', s >> s >> s))
list(profile('m1', my_concat(s, my_concat(s, s))))
list(profile('m2', my_concat(my_concat(s, s), s)))
profile.dump()
# How curious. The differences here are marginal...

def arrange(items):
    # items :: [(start_time, end_time (may be None), stream)]
    # The main issue here is avoiding the cost of + when waiting for another stream's start_time.
    pass # TODO tomorrow

# Naively: (silence[:start_time0] >> stream0) + (silence[:start_time1] >> stream1) + (silence[:start_time2] >> stream2) etc.
# I think we can do better by using the fact that SliceStream returns the rest of the stream.
# something like silence[:start_time0] >> stream0[:start_time1].bind(lambda rest: rest + stream1) etc.

# 2/6

# Splicing a stream into the middle of another one.
# Monadic bind:
@raw_stream
def bind(a, b):
    def closure():
        result = a()
        if isinstance(result, Return):
            return b(result.value)()
        value, next_a = result
        return (value, bind(next_a, b))
    return closure

stream = osc(440)[:2.0]
splice = osc(660)[:1.0]
play(bind(stream[:1.0], lambda rest: splice >> rest))

# Naive first pass
def arrange(items):
    def give_me_a_new_scope_please(start_time, end_time, stream):
        return lambda rest: rest + (stream[:end_time-start_time] if end_time else stream)

    items = sorted(items, key=lambda item: item[0])
    out = silence
    for start_time, end_time, stream in items:
        out = bind(out[:start_time], give_me_a_new_scope_please(start_time, end_time, stream))
    return out

s = arrange([(1.0, 2.0, osc(440)),
             (3.0, 3.5, osc(660))])
s.inspect()
play(s)

# Generates something like
# bind(bind(bind(silence[:start_time0], \r -> r + stream0)[:start_time1], \r -> r + stream1)[:start_time2], \r -> r + stream2)
# All of the binds are nested at the start.
# Instead, we want:
# bind(silence[:start_time0], \r -> r + bind(stream0[:start_time1-start_time0], \r -> r + bind(stream1[:start_time2-start_time1], \r -> r + stream2)))
# or with the `r +`s inside the binds; don't think it should matter much.
# tomorrow!

# 2/8

# I'll get back to arrange() soon.
# But first: how can we signal back from low-level to high-level?
# Imagine there's some stream going on that builds off of old state
# such that it can't just be generated in pieces at a higher level
# but we still want to mark higher-level divisions within.
# How can we do that?
# Could return tuples, as in (actual_value, flag_value)
# or we could intersperse another kind of special value - kind of like Return - to signal events
# call it Event
# then other operations could either look for or ignore Events.
# ex: turn this

def make_instrument(oscillator, envelope):
    return lambda n: oscillator(m2f(n[0])) * envelope(n[1])

inst = make_instrument(lambda f: sqr(f)/4 + tri(f)*3/4, basic_envelope)

def sequence(notes, instrument, bpm=80):
    return lazy_concat(to_stream(notes).map(lambda n: instrument((n[0], 60.0 / bpm * n[1]))))

# into this

class Event:
    def __init__(self, value):
        self.value = value
    
    def __repr__(self):
        return f"Event({self.value!r})"

def sequence(notes, instrument, bpm=80):
    return lazy_concat(to_stream(notes).map(lambda n: to_stream([Event(("noteon", n[0], n[1]))]) >> instrument((n[0], 60.0 / bpm * n[1]))))

# Then:

list(sequence([(60, 1/2048), (67, 1/2048)], inst))

# TODO: bring this into core as Stream.filter.
def sfilter(stream, predicate):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        if not predicate(value):
            # Skip.
            return sfilter(next_stream, predicate)()
        return (value, sfilter(next_stream, predicate))
    return closure
        

def strip_events(stream):
    return sfilter(stream, lambda x: not isinstance(x, Event))

play(strip_events(sequence([(60, 1), (67, 1)], inst)))

# And now, another example:

# Split a stream when a predicate is matched.
def split(stream, predicate):
    def closure():
        result = stream()
        # Convention: if the stream terminates before it's split,
        # wrap the Return again, so the function after the bind sees one Return.
        # Alteratively, could return an "empty" stream with just that value.
        # That way, the function bound after the split will always get a Stream.
        # (This is like asking: should 'abc'.split('d', 1) return ['abc'] or ['abc', '']?)
        if isinstance(result, Return):
            return Return(result)
        value, next_stream = result
        # Like str.split, this consumes the split value.
        # It may be useful to have a variant that either
        # 1) keeps the split value in the stream before or after the split, or
        # 2) passes the split value into the next function (`Return((value, next_stream))`)
        if predicate(value):
            return Return(next_stream)
        return (value, split(next_stream, predicate))
    return closure

s = sequence([(60, 1), (67, 1)], inst)
# Note the [1:], which discards the first Event.
interlaced = bind(split(s[1:], lambda x: isinstance(x, Event)), lambda rest: osc(40)[:0.5] >> rest)
play(strip_events(s))
play(interlaced)

# The more efficient arrange will have to wait until tomorrow.
# Also, should move to_stream, bind, filter, split into core.


# 2/10/21
# From before:
def arrange(items):
    def give_me_a_new_scope_please(start_time, end_time, stream):
        return lambda rest: rest + (stream[:end_time-start_time] if end_time else stream)

    items = sorted(items, key=lambda item: item[0])
    out = silence
    for start_time, end_time, stream in items:
        out = bind(out[:start_time], give_me_a_new_scope_please(start_time, end_time, stream))
    return out

# Generates
# bind(bind(bind(silence[:start_time0], \r -> r + stream0[:end_time0])[:start_time1], \r -> r + stream1[:end_time1])[:start_time2], \r -> r + stream2[:end_time2])
# Instead, we want:
# bind(silence[:start_time0], \r -> bind((r + stream0[:end_time0-start_time0])[:start_time1-start_time0], \r -> bind((r + stream1[:end_time1-start_time1])[:start_time2-start_time1], \r -> r + stream2[:end_time2-start_time2])))
# or with the `r +`s inside the binds.

def arrange(items):
    items = sorted(items, key=lambda item: item[0], reverse=True)
    last_start_time, last_end_time, last_stream = items[0]
    out = lambda r: r + last_stream[:last_end_time-last_start_time]
    prev_start_time = last_start_time
    for start_time, end_time, stream in items[1:]:
        print(last_start_time, start_time, end_time)
        # Sometimes I really wish Python had `let`...
        out = (lambda start, end, stream, prev: (lambda r: bind((r + stream[:end])[:start], prev)))(prev_start_time - start_time, end_time - start_time, stream, out)
        prev_start_time = start_time
    return bind(silence[:prev_start_time], out)

s = arrange([(1.0, 2.0, osc(440)),
             (3.0, 3.5, osc(660))])
s.inspect()
play(s)
play()

# Should this go on forever, or stop once all arranged streams have started and stopped?
# Here's the stopping version:

def arrange(items):
    items = sorted(items, key=lambda item: item[0], reverse=True)
    last_start_time, last_end_time, last_stream = items[0]
    out = lambda r: r + last_stream[:last_end_time-last_start_time]
    prev_start_time = last_start_time
    for start_time, end_time, stream in items[1:]:
        print(last_start_time, start_time, end_time)
        # Sometimes I really wish Python had `let`...
        out = (lambda start, end, stream, prev: (lambda r: bind((r + stream[:end])[:start], prev)))(prev_start_time - start_time, end_time - start_time, stream, out)
        prev_start_time = start_time
    return bind(silence[:last_start_time][:prev_start_time], out)


# 2/12/21

def arrange(items):
    items = sorted(items, key=lambda item: item[0], reverse=True)
    last_start_time, last_end_time, last_stream = items[0]
    out = lambda r: r + last_stream[:last_end_time-last_start_time]
    prev_start_time = last_start_time
    for start_time, end_time, stream in items[1:]:
        print(last_start_time, start_time, end_time)
        if end_time:
            stream = stream[:end_time - start_time]
        # Sometimes I really wish Python had `let`...
        out = (lambda start, stream, prev: (lambda r: bind((r + stream)[:start], prev)))(prev_start_time - start_time, stream, out)
        prev_start_time = start_time
    return bind(silence[:last_start_time][:prev_start_time], out)

s = arrange([(0.5, 2.0, osc(440)),
             (1.0, 2.5, osc(660)),
             (3.0, 3.5, osc(880)),
             (3.0, None, osc(1100))])
play(s/2)
play()

# Finally promoted to core!
