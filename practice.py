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


# 2/15/21

from core import *
from audio import *
from midi import *

p = mido.open_input(mido.get_input_names()[1])

inst = polyphonifier(lambda f: osc(f) * basic_envelope(0.5))
play(inst(event_stream(p)))

play(polyphonic_osc_instrument(event_stream(p)))

# Want to give each monophonic instrument a stream of events, too - which it believes are all the events.
# Need to keep each voice around after the release, until it finishes on its own.
# Each voice needs a Stream whereby we control the state - set it just before asking for the next value.

def make_event_substream():
    substream = lambda: (substream.message, substream)
    substream.message = None
    return substream

f = open('hmmmm.txt', 'w')

def polyphonic_instrument(monophonic_instrument, stream, substreams={}, voices=[]):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        next_substreams = substreams
        next_voices = []
        acc = 0
        if event:
            if event.type == 'note_on':
                # print(len(voices), file=f)
                if event.note not in substreams:
                    next_substreams = substreams.copy()
                    substream = make_event_substream()
                    substream.message = event
                    next_substreams[event.note] = substream
                    new_voice = monophonic_instrument(substream)
                    result = new_voice()
                    if not isinstance(result, Return):
                        sample, new_voice = result
                        acc += sample
                        next_voices.append(new_voice)
                    substream.message = None
                # TODO: pass along retriggers
            elif event.type == 'note_off':
                if event.note in substreams:
                    substreams[event.note].message = event
                    next_substreams = substreams.copy()
                    del next_substreams[event.note]

        for voice in voices:
            result = voice()
            if not isinstance(result, Return):
                sample, next_voice = result
                acc += sample
                next_voices.append(next_voice)
        return (acc, polyphonic_instrument(monophonic_instrument, next_stream, next_substreams, next_voices))
    return closure

# aside: maybe we should process all available events in one sample, rather than polling for just one event per sample

def env_osc_instrument(stream, freq=0, phase=0, amp=0, delta_amp=0):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if not event:
            next_freq = freq
            next_delta_amp = delta_amp
        elif event.type == 'note_on':
            next_freq = m2f(event.note)
            next_delta_amp = 0.0001
        elif event.type == 'note_off':
            next_freq = freq
            next_delta_amp = -0.0001
        next_amp = max(0, min(1, amp + delta_amp))
        next_phase = phase + 2*math.pi*next_freq/SAMPLE_RATE
        return (next_amp * math.sin(next_phase), env_osc_instrument(next_stream, next_freq, next_phase, next_amp, next_delta_amp))
    return closure

play(env_osc_instrument(event_stream(p)))

play(polyphonic_instrument(env_osc_instrument, event_stream(p)))

# Ah, now the issue is that the monophonic instrument never ceases,
# so polyphonic_instrument just keeps accumulating (dead) voices...

# wow. made it to 103 concurrent voices before getting consistent stuttering.
# better than expected, especially with live playback
# let's finish this up tomorrow.
# some combination of retrig support (for existing voices) + having monophonic instruments with a 'die after release' option

# 2/17/21

# Retrigger support
def persistent_polyphonic_instrument(monophonic_instrument, stream, substreams={}, voices=[]):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        next_substreams = substreams
        next_voices = []
        acc = 0
        if event:
            if event.type == 'note_on':
                if event.note in substreams:
                    # Retrigger existing voice
                    substreams[event.note].message = event
                else:
                    # New voice
                    next_substreams = substreams.copy()
                    substream = make_event_substream()
                    substream.message = event
                    next_substreams[event.note] = substream
                    new_voice = monophonic_instrument(substream)
                    result = new_voice()
                    if not isinstance(result, Return):
                        sample, new_voice = result
                        acc += sample
                        next_voices.append(new_voice)
                    substream.message = None
            elif event.type == 'note_off':
                if event.note in substreams:
                    substreams[event.note].message = event

        for voice in voices:
            sample, next_voice = voice()
            acc += sample
            next_voices.append(next_voice)
        return (acc, persistent_polyphonic_instrument(monophonic_instrument, next_stream, next_substreams, next_voices))
    return closure

def env_osc_instrument(stream, freq=0, phase=0, amp=0, delta_amp=0):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if not event:
            next_freq = freq
            next_delta_amp = delta_amp
        elif event.type == 'note_on':
            next_freq = m2f(event.note)
            next_delta_amp = 0.0001
        elif event.type == 'note_off':
            next_freq = freq
            next_delta_amp = -0.0001
        next_amp = max(0, min(1, amp + delta_amp))
        next_phase = phase + 2*math.pi*next_freq/SAMPLE_RATE
        return (next_amp * math.sin(next_phase), env_osc_instrument(next_stream, next_freq, next_phase, next_amp, next_delta_amp))
    return closure

play(persistent_polyphonic_instrument(env_osc_instrument, event_stream(p)))


# Options:

def env_osc_instrument(stream, freq=0, phase=0, amp=0, delta_amp=0, persist=True):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if not event:
            next_freq = freq
            next_delta_amp = delta_amp
        elif event.type == 'note_on':
            next_freq = m2f(event.note)
            next_delta_amp = 0.0001
        elif event.type == 'note_off':
            next_freq = freq
            next_delta_amp = -0.0001
        next_amp = max(0, min(1, amp + delta_amp))
        next_phase = phase + 2*math.pi*next_freq/SAMPLE_RATE
        if not persist and next_amp == 0 and next_delta_amp < 0:
            return Return()
        return (next_amp * math.sin(next_phase), env_osc_instrument(next_stream, next_freq, next_phase, next_amp, next_delta_amp, persist))
    return closure

def poly(monophonic_instrument, stream, persist=False, substreams={}, voices=[]):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        next_substreams = substreams
        next_voices = []
        acc = 0
        # Clear old messages:
        for substream in substreams.values():
            substream.message = None
        if event:
            if event.type == 'note_on':
                # print(len(substreams), len(voices), file=f)
                if event.note in substreams:
                    # Retrigger existing voice
                    substreams[event.note].message = event
                else:
                    # New voice
                    next_substreams = substreams.copy()
                    substream = make_event_substream()
                    substream.message = event
                    next_substreams[event.note] = substream
                    new_voice = monophonic_instrument(substream, persist=persist)
                    # TODO: avoid duplication here?
                    result = new_voice()
                    if not isinstance(result, Return):
                        sample, new_voice = result
                        acc += sample
                        next_voices.append(new_voice)
            elif event.type == 'note_off':
                if event.note in substreams:
                    substreams[event.note].message = event
                    if not persist:
                        next_substreams = substreams.copy()
                        del next_substreams[event.note]

        for voice in voices:
            result = voice()
            if not isinstance(result, Return):
                sample, next_voice = result
                acc += sample
                next_voices.append(next_voice)
        return (acc, poly(monophonic_instrument, next_stream, persist, next_substreams, next_voices))
    return closure

play(poly(env_osc_instrument, event_stream(p), persist=False))

@raw_stream
def sfilter(stream, predicate):
    def closure():
        next_stream = stream
        while True:
            result = next_stream()
            if isinstance(result, Return):
                return result
            value, next_stream = result
            if predicate(value):
                return (value, sfilter(next_stream, predicate))
    return closure

list(sfilter(event_stream(p), lambda x: x is not None)[:5])

# Now with velocity

def better_instrument(stream, freq=0, phase=0, amp=0, delta_amp=0, persist=True):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if not event:
            next_freq = freq
            next_delta_amp = delta_amp
        elif event.type == 'note_on':
            next_freq = m2f(event.note)
            next_delta_amp = 1e-6 * event.velocity**2
        elif event.type == 'note_off':
            next_freq = freq
            next_delta_amp = -1e-4
        next_amp = max(0, min(1, amp + delta_amp))
        next_phase = phase + 2*math.pi*next_freq/SAMPLE_RATE
        if not persist and next_amp == 0 and next_delta_amp < 0:
            return Return()
        return (next_amp * math.sin(next_phase), better_instrument(next_stream, next_freq, next_phase, next_amp, next_delta_amp, persist))
    return closure

play(poly(better_instrument, event_stream(p), persist=True))

# Idea: ongoing (programmed) rhythm/melodic patterns, but user can control certain underlying pitches used in the program via keyboard
# (kind of a extension of the arpeggiator, with the clarification that the user's keypresses do not start anything, just change it)


# 2/18/2021

from gtts import gTTS
from io import BytesIO
from streamp3 import MP3Decoder
import numpy as np
from scipy import signal

from core import *
from audio import *

def speech(text):
    mp3_fp = BytesIO()
    tts = gTTS(text, lang='en')
    tts.write_to_fp(mp3_fp)
    decoder = MP3Decoder(mp3_fp.getvalue())
    assert(decoder.num_channels == 1)
    data = np.concatenate([np.frombuffer(chunk, dtype=np.int16).copy() for chunk in decoder]).astype(np.float) / np.iinfo(np.int16).max
    return list_to_stream(signal.resample(data, int(SAMPLE_RATE / decoder.sample_rate * len(data))))

s = speech("Hello world!")
play(s)

def repeat(stream, n):
    return ConcatStream([stream] * n)

def stutter(stream, size, repeats):
    return bind(repeat(stream[:size], repeats), lambda rest: stutter(rest, size, repeats) if rest else empty)

play(repeat(s, 3))
play(stutter(s, 0.1, 2))
play(stutter(s, 0.09, 5))
play(stutter(s, 0.07, 20))
play(stutter(s, 0.01, 20))

play(stutter(s, 0.07, 5) + stutter(list_to_stream(list(s)[::-1]), 0.09, 5))

play(stutter(s, 0.07, 10) + stutter(s, 0.005, 10))

# 2/19/2021

# Velocity should affect final volume, not just the attack time.
@raw_stream
def cool_instrument(stream, freq=0, phase=0, amp=0, velocity=0, persist=True):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if not event:
            next_freq = freq
            next_velocity = velocity
        elif event.type == 'note_on':
            next_freq = m2f(event.note)
            next_velocity = event.velocity
        elif event.type == 'note_off':
            next_freq = freq
            next_velocity = 0
        target_amp = next_velocity / 127
        delta_amp = 0
        if amp > target_amp:
            next_amp = max(target_amp, amp - 1e-4)
        else:
            next_amp = min(target_amp, amp + 1e-6 * next_velocity**2)
        next_phase = phase + 2*math.pi*next_freq/SAMPLE_RATE
        if not persist and next_amp == 0 and next_velocity == 0:
            return Return()
        return (next_amp * math.sin(next_phase), cool_instrument(next_stream, next_freq, next_phase, next_amp, next_velocity, persist))
    return closure

# Bring it back:
def make_event_substream():
    substream = lambda: (substream.message, substream)
    substream.message = None
    return substream

@raw_stream
def poly(monophonic_instrument, stream, persist=False, substreams={}, voices=[]):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        next_substreams = substreams
        next_voices = []
        acc = 0
        # Clear old messages:
        for substream in substreams.values():
            substream.message = None
        if event:
            if event.type == 'note_on':
                if event.note in substreams:
                    # Retrigger existing voice
                    substreams[event.note].message = event
                else:
                    # New voice
                    next_substreams = substreams.copy()
                    substream = make_event_substream()
                    substream.message = event
                    next_substreams[event.note] = substream
                    new_voice = monophonic_instrument(substream, persist=persist)
                    # TODO: avoid duplication here?
                    result = new_voice()
                    if not isinstance(result, Return):
                        sample, new_voice = result
                        acc += sample
                        next_voices.append(new_voice)
            elif event.type == 'note_off':
                if event.note in substreams:
                    substreams[event.note].message = event
                    if not persist:
                        next_substreams = substreams.copy()
                        del next_substreams[event.note]

        for voice in voices:
            result = voice()
            if not isinstance(result, Return):
                sample, next_voice = result
                acc += sample
                next_voices.append(next_voice)
        return (acc, poly(monophonic_instrument, next_stream, persist, next_substreams, next_voices))
    return closure

play(poly(cool_instrument, event_stream(p)))

# 3/3/2021

from core import *
from audio import *
# wavetable
# one period of 441 Hz at 44.1kHz sample rate
# period is 1/441 seconds. 44.1 samples/second * (1/441 seconds) = 100 samples
period = list(osc(441)[:100])
play(cycle(to_stream(period)))
# Yep, that sounds about right.
play()
# Alex Strong's December 1978 idea
# For now, we will mutate.
def decay_cycle(list):
    def f(t):
        value = list[t % len(list)]
        list[t % len(list)] = 0.5*(value + list[(t-1) % len(list)])
        return value
    return count().map(f)

play(decay_cycle(period[:]))
play()

# TODO: overload '-' operator.
period = list((rand + -0.5)[:100])
play(cycle(to_stream(period)))
play()
# You know. I never really thought about it, but the fact that the above works is remarkable. It doesn't matter that much /what/ is in the buffer; just that it repeats.
play(decay_cycle(list((rand*2 + -1)[:100])))
play()

randbits = NamedStream("randbits", lambda: (random.getrandbits(1), randbits))
play(decay_cycle(list((randbits*2 + -1)[:100])))

# Karplus, December 1979
def drum_cycle(list, b):
    def f(t):
        value = list[t % len(list)]
        list[t % len(list)] = (0.5 if random.random() < b else -0.5)*(value + list[(t-1) % len(list)])
        return value
    return count().map(f)

play(drum_cycle(list((randbits*2 + -1)[:800]), 0.6))
play(drum_cycle(list(ones[:800]), 0.6))
play()

# The "harmonic trick":
play(decay_cycle(list((randbits*2 + -1)[:100])*4))

def stretched_decay_cycle(list, S):
    def f(t):
        value = list[t % len(list)]
        if random.random() < 1/S:
            list[t % len(list)] = 0.5*(value + list[(t-1) % len(list)])
        return value
    return count().map(f)

play(stretched_decay_cycle(list((randbits*2 + -1)[:100]), 1))
# Period is about p + 1/(2S)
play(stretched_decay_cycle(list(osc(441/2)[:200]), 1.2))

def stretched_drum_cycle(list, b, S):
    def f(t):
        value = list[t % len(list)]
        sign = 1 if random.random() < b else -1
        if random.random() < 1/S:
            list[t % len(list)] = sign*0.5*(value + list[(t-1) % len(list)])
        else:
            list[t % len(list)] *= sign
        return value
    return count().map(f)

play(stretched_drum_cycle(list((randbits*2 + -1)[:800]), 0.6, 2))
play()

# My main issue (which also affects the feasibility of speeding up osc): how to get periods in between increments of p?


play(decay_cycle(list((randbits*2 + -1)[:300])))

# Hmm. I think the above may have implicitly been the Siegel variant.
def two_point_recurrence(y, c, d, g, h):
    def f(t):
        value = y[t % len(y)]
        y[t % len(y)] = c*y[(t-g) % len(y)] + d*y[(t-h) % len(y)]
        return value
    return count().map(f)

play(two_point_recurrence(list((randbits*2 + -1)[:300])*2, 0.5, 0.5, 300, 301))

def multiplicative_decay_stretching(S):
    return two_point_recurrence(list((randbits*2 + -1)[:300])*2, 1-1/(2*S), 1/(2*S), 300, 301)

play(multiplicative_decay_stretching(1))

def decay_cycle(y):
    def f(t):
        value = y[t % len(y)]
        y[t % len(y)] = 0.5*(value + y[(t-1) % len(y)])
        return value
    return count().map(f)

play(decay_cycle(list((randbits*2 + -1)[:SAMPLE_RATE // 55])))
play(resample(decay_cycle(list((randbits*2 + -1)[:8000 // 55])), const(8000/SAMPLE_RATE)))

# This version returns the new values immediately, effectively skipping the first period (the original wavetable)
def alt_decay_cycle(y):
    def f(t):
        value = 0.5*(y[t % len(y)] + y[(t-1) % len(y)])
        y[t % len(y)] = value
        return value
    return count().map(f)

play(decay_cycle(list((randbits*2 + -1)[:SAMPLE_RATE // 55])))
play(alt_decay_cycle(list((randbits*2 + -1)[:SAMPLE_RATE // 55])))

def pluck(p, s=1):
    return two_point_recurrence(list((randbits*2 + -1)[:p]), 1-1/(2*s), 1/(2*s), p, p+1)

play(decay_cycle(list((randbits*2 + -1)[:SAMPLE_RATE // 55])))
play(pluck(SAMPLE_RATE // 55, 0.6))
import graph
graph.plot(pluck(SAMPLE_RATE // 55, 0.6)[:1.0])
graph.plot(resample(decay_cycle(list((randbits*2 + -1)[:8000 // 55])), const(8000/SAMPLE_RATE))[:1.0])
play(pluck(SAMPLE_RATE // 55, 0.6)[:5.0])

class SampleRateContext:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate

    def __enter__(self):
        global SAMPLE_RATE
        self.old_sample_rate = SAMPLE_RATE
        SAMPLE_RATE = self.sample_rate
    
    def __exit__(self, *_):
        global SAMPLE_RATE
        SAMPLE_RATE = self.old_sample_rate

play(pluck(SAMPLE_RATE // 55, 0.6))
with SampleRateContext(8000):
    play(pluck(SAMPLE_RATE // 55, 0.6))

# Should this also wrap the execution of the stream itself?
def run_at_rate(sample_rate, function):
    with SampleRateContext(sample_rate):
        stream = function()
    return resample(stream, const(sample_rate/SAMPLE_RATE))

play(run_at_rate(8000, lambda: pluck(SAMPLE_RATE // 55, 1)))

message = [None]

def mono_guitar(stream, s=1, length=3.0, persist=False):
    assert(persist == False)
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if event: print(event)
        if event and event.type == 'note_on':
            message[0] = ("Woo", event.velocity, event.note)
            return (event.velocity / 127 * pluck(int(SAMPLE_RATE / m2f(event.note)), s=s)[:length])()
        return (0, mono_guitar(next_stream))
    return closure

from midi import *
p = mido.open_input(mido.get_input_names()[1])
play(mono_guitar(event_stream(p)))

play(80 / 127 * pluck(int(SAMPLE_RATE / m2f(60)))[:1.0])

play(poly(lambda *args, **kwargs: mono_guitar(*args, **kwargs, s=0.7))(event_stream(p)))
play()

# different filter: [1/2, 0, 1/2] instead of [1/2, 1/2]; fundamental is p instead of p+1/2
def variant(y):
    def f(t):
        value = y[t % len(y)]
        y[t % len(y)] = 0.5*(y[(t+1) % len(y)] + y[(t-1) % len(y)])
        return value
    return count().map(f)

play(decay_cycle(list((randbits*2 + -1)[:SAMPLE_RATE // 110])))
play(variant(list((randbits*2 + -1)[:SAMPLE_RATE // 110])))


# 3/5/2021

# Wavetables
from core import *
import numpy as np
play(osc(440))
def osc_by_table(freq, resolution=1024):
    sine_table = np.sin(np.linspace(0, 2*np.pi, resolution, endpoint=False))
    base_freq = SAMPLE_RATE / resolution
    return resample(cycle(to_stream(sine_table)), const(freq / base_freq))
play(osc_by_table(440))
# play(resample(cycle(to_stream(sine_table)), const(10)))
play(osc(40))
import graph
play(osc_by_table(440, resolution=2**12))
graph.plot(np.log10(np.abs(np.fft.rfft(list(osc(440)[:1.0])))))
graph.plot(np.log10(np.abs(np.fft.rfft(list(osc_by_table(440, resolution=2**16)[:1.0])))))
graph.plot((osc(440) + -osc_by_table(440, resolution=2**8))[:1.0])
# Curious: the mean error actually starts going up as resolution increases past 2**7
np.mean(np.abs(list((osc(440) + -osc_by_table(440, resolution=2**7))[:1.0])))
np.mean(np.abs(list((osc(440) + -osc_by_table(440, resolution=2**8))[:1.0])))
# Maybe because 44100/440 is close to 128?
# Indeed. The error trough appears to be at resolution=100, the closest integer to 44100/440.
np.mean(np.abs(list((osc(440) + -osc_by_table(440, resolution=99))[:1.0])))
np.mean(np.abs(list((osc(440) + -osc_by_table(440, resolution=100))[:1.0])))
np.mean(np.abs(list((osc(440) + -osc_by_table(440, resolution=101))[:1.0])))

@raw_stream
def resample_const(stream, rate, pos=0, sample=None, next_sample=0):
    def closure():
        nonlocal stream, pos, sample, next_sample
        pos += rate
        while pos >= 0:
            result = stream()
            if isinstance(result, Return):
                return result
            sample = next_sample
            next_sample, stream = result
            pos -= 1
        interpolated = (next_sample - sample) * (pos + 1) + sample
        return (interpolated, resample_const(stream, rate, pos, sample, next_sample))
    return closure

# Now, profiling.
# Normal osc vs raw stream osc vs resample vs resample_const.

@raw_stream
def raw_osc(freq, phase=0):
    def closure():
        return (math.sin(phase), raw_osc(freq, phase + 2*math.pi*freq/SAMPLE_RATE))
    return closure

sine_table = np.sin(np.linspace(0, 2*np.pi, 128, endpoint=False)).tolist()
from prof import profile
profile.reset()
_ = list((profile("osc", osc(440)) +
          profile("raw_osc", osc(440)) +
          profile("resample", resample(cycle(to_stream(sine_table)), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const", resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)))[:10.0])
profile.dump()

np.mean(np.abs(list((osc(440) + -resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE))[:1.0])))

# Results (one second):
# osc: 44100 calls (0 endings)
#      0.387us avg | 0.017s total | 1.70% of budget
# raw_osc: 44100 calls (0 endings)
#          0.388us avg | 0.017s total | 1.71% of budget
# resample: 44100 calls (0 endings)
#           1.085us avg | 0.048s total | 4.79% of budget
# resample_const: 44100 calls (0 endings)
#                 1.101us avg | 0.049s total | 4.86% of budget

# 10 seconds:
# osc: 441000 calls (0 endings)
#      0.122us avg | 0.054s total | 0.54% of budget
# raw_osc: 441000 calls (0 endings)
#          0.121us avg | 0.053s total | 0.53% of budget
# resample: 441000 calls (0 endings)
#           0.377us avg | 0.166s total | 1.66% of budget
# resample_const: 441000 calls (0 endings)
#                 0.318us avg | 0.140s total | 1.40% of budget

# Hm.
# What about a zero-order hold?
@raw_stream
def zoh(stream, rate, pos=0, sample=None):
    def closure():
        nonlocal stream, pos, sample
        pos += rate
        while pos >= 0:
            result = stream()
            if isinstance(result, Return):
                return result
            sample, stream = result
            pos -= 1
        return (sample, zoh(stream, rate, pos, sample))
    return closure

np.mean(np.abs(list((osc(440) + -zoh(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE))[:1.0])))

profile.reset()
_ = list((profile("osc", osc(440)) +
          profile("raw_osc", osc(440)) +
          profile("resample", resample(cycle(to_stream(sine_table)), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const", resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh", zoh(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)))[:10.0])
profile.dump()

# Hm. Only marginally lower. What if it took a list, instead?
class CycleListStream(Stream):
    def __init__(self, list, index=0):
        self.list = list
        self.index = index % len(list)
    
    def __call__(self):
        return (self.list[self.index], CycleListStream(self.list, self.index + 1))

np.mean(np.abs(list((osc(440) + -zoh(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE))[:1.0])))

# This vs. cycle?
profile.reset()
_ = list((profile("osc", osc(440)) +
          profile("raw_osc", osc(440)) +
          profile("resample", resample(cycle(to_stream(sine_table)), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const", resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh", zoh(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("resample cyclelist", resample(CycleListStream(sine_table), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const cyclelist", resample_const(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh cyclelist", zoh(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)))[:10.0])
profile.dump()

# Hm, that actually makes a significant difference.
# Well, cycle() does add concat overhead, and these are running their internal streams faster than 1.
# Let's try another thing:

class ZohWavetable(Stream):
    def __init__(self, list, rate, index=0):
        self.list = list
        self.rate = rate
        self.index = index % len(list)
    
    def __call__(self):
        return (self.list[int(self.index)], ZohWavetable(self.list, self.rate, self.index + self.rate))

profile.reset()
_ = list((profile("osc", osc(440)) +
          profile("raw_osc", osc(440)) +
          profile("resample", resample(cycle(to_stream(sine_table)), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const", resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh", zoh(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("resample cyclelist", resample(CycleListStream(sine_table), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const cyclelist", resample_const(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh cyclelist", zoh(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("ZohWavetable", ZohWavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE)))[:10.0])
profile.dump()

# Now we're talking. Results:
# osc: 441000 calls (0 endings)
#      0.135us avg | 0.060s total | 0.60% of budget
# raw_osc: 441000 calls (0 endings)
#          0.129us avg | 0.057s total | 0.57% of budget
# resample: 441000 calls (0 endings)
#           0.406us avg | 0.179s total | 1.79% of budget
# resample_const: 441000 calls (0 endings)
#                 0.342us avg | 0.151s total | 1.51% of budget
# zoh: 441000 calls (0 endings)
#      0.347us avg | 0.153s total | 1.53% of budget
# resample cyclelist: 441000 calls (0 endings)
#                     0.255us avg | 0.113s total | 1.13% of budget
# resample_const cyclelist: 441000 calls (0 endings)
#                           0.211us avg | 0.093s total | 0.93% of budget
# zoh cyclelist: 441000 calls (0 endings)
#                0.229us avg | 0.101s total | 1.01% of budget
# ZohWavetable: 441000 calls (0 endings)
#               0.091us avg | 0.040s total | 0.40% of budget

# It is faster than osc.
np.mean(np.abs(list((osc(440) + -zoh(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE))[:1.0])))
np.mean(np.abs(list((osc(440) + -ZohWavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE))[:1.0])))
# The fact that it apparently has less error than zoh is concerning, but probably indicates a bug in zoh.

# Now let's bring back interpolation.
class Wavetable(Stream):
    def __init__(self, list, rate, index=0):
        self.list = list
        self.rate = rate
        self.index = index % len(list)
    
    def __call__(self):
        index = int(self.index)
        frac = self.index - index
        start = self.list[index]
        end = self.list[(index + 1) % len(self.list)]
        interp = start + (end - start) * frac
        return (interp, Wavetable(self.list, self.rate, self.index + self.rate))

np.mean(np.abs(list((osc(440) + -Wavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE))[:1.0])))
# Again, curiously less error than resample. Should really check that for correctness...

profile.reset()
_ = list((profile("osc", osc(440)) +
          profile("raw_osc", osc(440)) +
          profile("resample", resample(cycle(to_stream(sine_table)), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const", resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh", zoh(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("resample cyclelist", resample(CycleListStream(sine_table), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const cyclelist", resample_const(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh cyclelist", zoh(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("ZohWavetable", ZohWavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("Wavetable", Wavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE)))[:10.0])
profile.dump()
# Yes, this is still faster than raw_osc.
# For fairness:
class Osc(Stream):
    def __init__(self, freq, phase=0):
        self.freq = freq
        self.phase = phase
    
    def __call__(self):
        return (math.sin(self.phase), Osc(self.freq, self.phase + 2*math.pi*self.freq/SAMPLE_RATE))

profile.reset()
_ = list((profile("osc", osc(440)) +
          profile("raw_osc", osc(440)) +
          profile("resample", resample(cycle(to_stream(sine_table)), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const", resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh", zoh(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("resample cyclelist", resample(CycleListStream(sine_table), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const cyclelist", resample_const(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh cyclelist", zoh(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("ZohWavetable", ZohWavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("Wavetable", Wavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("Osc", Osc(440)))[:10.0])
profile.dump()

np.mean(np.abs(list((osc(440) + -Osc(440))[:1.0])))

# Real-time budget: 22.676us per sample
# osc: 441000 calls (0 endings)
#      0.138us avg | 0.061s total | 0.61% of budget
# raw_osc: 441000 calls (0 endings)
#          0.136us avg | 0.060s total | 0.60% of budget
# resample: 441000 calls (0 endings)
#           0.424us avg | 0.187s total | 1.87% of budget
# resample_const: 441000 calls (0 endings)
#                 0.336us avg | 0.148s total | 1.48% of budget
# zoh: 441000 calls (0 endings)
#      0.353us avg | 0.155s total | 1.55% of budget
# resample cyclelist: 441000 calls (0 endings)
#                     0.300us avg | 0.132s total | 1.32% of budget
# resample_const cyclelist: 441000 calls (0 endings)
#                           0.223us avg | 0.098s total | 0.98% of budget
# zoh cyclelist: 441000 calls (0 endings)
#                0.205us avg | 0.090s total | 0.90% of budget
# ZohWavetable: 441000 calls (0 endings)
#               0.096us avg | 0.042s total | 0.42% of budget
# Wavetable: 441000 calls (0 endings)
#            0.096us avg | 0.043s total | 0.43% of budget
# Osc: 441000 calls (0 endings)
#      0.085us avg | 0.037s total | 0.37% of budget

# Well.
# I guess that clears one thing up.
# It's not that Wavetable is faster. It's that the function-streams are slower.
# One more experiment. (Is "raw-er" a word?)
def rawer_osc(freq, phase=0):
    def closure():
        return (math.sin(phase), rawer_osc(freq, phase + 2*math.pi*freq/SAMPLE_RATE))
    return closure

profile.reset()
_ = list((profile("osc", osc(440)) +
          profile("raw_osc", osc(440)) +
          profile("resample", resample(cycle(to_stream(sine_table)), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const", resample_const(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh", zoh(cycle(to_stream(sine_table)), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("resample cyclelist", resample(CycleListStream(sine_table), const(440 * len(sine_table) / SAMPLE_RATE))) +
          profile("resample_const cyclelist", resample_const(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("zoh cyclelist", zoh(CycleListStream(sine_table), 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("ZohWavetable", ZohWavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("Wavetable", Wavetable(sine_table, 440 * len(sine_table) / SAMPLE_RATE)) +
          profile("Osc", Osc(440)) +
          profile("rawer_osc", rawer_osc(440)))[:10.0])
profile.dump()


# Real-time budget: 22.676us per sample
# osc: 441000 calls (0 endings)
#      0.146us avg | 0.064s total | 0.64% of budget
# raw_osc: 441000 calls (0 endings)
#          0.128us avg | 0.057s total | 0.57% of budget
# resample: 441000 calls (0 endings)
#           0.467us avg | 0.206s total | 2.06% of budget
# resample_const: 441000 calls (0 endings)
#                 0.466us avg | 0.206s total | 2.06% of budget
# zoh: 441000 calls (0 endings)
#      0.390us avg | 0.172s total | 1.72% of budget
# resample cyclelist: 441000 calls (0 endings)
#                     0.304us avg | 0.134s total | 1.34% of budget
# resample_const cyclelist: 441000 calls (0 endings)
#                           0.236us avg | 0.104s total | 1.04% of budget
# zoh cyclelist: 441000 calls (0 endings)
#                0.230us avg | 0.101s total | 1.01% of budget
# ZohWavetable: 441000 calls (0 endings)
#               0.096us avg | 0.042s total | 0.42% of budget
# Wavetable: 441000 calls (0 endings)
#            0.101us avg | 0.045s total | 0.45% of budget
# Osc: 441000 calls (0 endings)
#      0.091us avg | 0.040s total | 0.40% of budget
# rawer_osc: 441000 calls (0 endings)
#            0.081us avg | 0.036s total | 0.36% of budget

# I see.
# It's not even that function-streams are slower.
# It's that @raw_stream makes them slow - to the tune of 0.21% of the budget.
# Hm.

# 3/6/2021

from core import *
from audio import *
volume(0.015)
play(sqr(440))
play()

import graph
import numpy as np
graph.plot(sqr(440)[:0.05])
graph.plot(np.log10(np.abs(np.fft.rfft(list(sqr(440)[:1.0])))))

s = np.zeros(SAMPLE_RATE)
for k in range(1, int(SAMPLE_RATE/2/440) + 1, 2):
# for k in range(1, 12, 2):
    print(440*k)
    s += 4/np.pi*np.sin(2*np.pi*440*k/SAMPLE_RATE*np.arange(len(s)))/k
graph.plot(np.log10(np.abs(np.fft.rfft(s))))

graph.plot(sqr(440)[:0.01])
graph.plot(s[:int(SAMPLE_RATE*0.01)])

play(sqr(440)[:1.0])
play(to_stream(s))

def clean_sqr(freq):
    s = np.zeros(math.ceil(SAMPLE_RATE / freq))
    rate = len(s) / (SAMPLE_RATE / freq)
    for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2):
        # print(freq*k, freq/rate*k)
        s += 4/np.pi*np.sin(2*np.pi*freq/rate*k/SAMPLE_RATE*np.arange(len(s)))/k
    # graph.plot(s)
    return Wavetable(s.tolist(), rate)

play()
play(clean_sqr(440))
graph.plot(clean_sqr(440)[:0.01])

graph.plot(np.log10(np.abs(np.fft.rfft(s))))
graph.plot(np.log10(np.abs(np.fft.rfft(list(sqr(440)[:1.0])))))
graph.plot(np.log10(np.abs(np.fft.rfft(s[:int(SAMPLE_RATE*1.0)]))))
graph.plot(np.log10(np.abs(np.fft.rfft(list(clean_sqr(440)[:1.0])))))

def clean_sqr2(freq, resolution=None):
    if resolution is None:
        resolution = int(SAMPLE_RATE / freq)
    s = np.zeros(resolution)
    rate = resolution / (SAMPLE_RATE / freq)
    for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2):
        s += 4/np.pi*np.sin(2*np.pi*freq/rate*k/SAMPLE_RATE*np.arange(resolution))/k
    return Wavetable(s.tolist(), rate)

np.mean(np.abs(list((to_stream(s) + -sqr(440))[:1.0])))
np.mean(np.abs(list((to_stream(s) + -clean_sqr(440))[:1.0])))
np.mean(np.abs(list((to_stream(s) + -clean_sqr2(440))[:1.0])))

import matplotlib.pyplot as plt
resolutions = 2**np.arange(1, 20)
errors = [np.mean(np.abs(list((to_stream(s) + -clean_sqr2(440, resolution))[:1.0])))
          for resolution in resolutions]
plt.plot(resolutions, np.log10(errors))
plt.show()

# Curious; this does not match my observations from osc_by_table yesterday.
def osc_by_table(freq, resolution=1024):
    sine_table = np.sin(np.linspace(0, 2*np.pi, resolution, endpoint=False))
    base_freq = SAMPLE_RATE / resolution
    return resample(cycle(to_stream(sine_table)), const(freq / base_freq))

resolutions = 2**np.arange(1, 10)
errors = [np.mean(np.abs(list((osc(440) + -osc_by_table(440, resolution))[:1.0])))
          for resolution in resolutions]
plt.plot(resolutions, np.log10(errors))
plt.show()

def osc_by_table(freq, resolution=1024):
    sine_table = np.sin(np.linspace(0, 2*np.pi, resolution, endpoint=False))
    base_freq = SAMPLE_RATE / resolution
    return Wavetable(sine_table.tolist(), freq / base_freq)

# Ah, but now it does (using Wavetable rather than resample), and the errors are lower to boot.
# This further hints at a bug in resample.

play()
play(sqr(1000))
play(clean_sqr2(1000, 32))
play(clean_sqr2(1000, 64))
play(clean_sqr2(1000, 1024))

def perfect_sqr(freq, dur):
    dur = convert_time(dur)
    s = np.zeros(dur)
    for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2):
        s += 4/np.pi*np.sin(2*np.pi*freq*k/SAMPLE_RATE*np.arange(dur))/k
    return to_stream(s)

np.mean(np.abs(list((perfect_sqr(440, SAMPLE_RATE) + -sqr(440))[:1.0])))
np.mean(np.abs(list((perfect_sqr(440, SAMPLE_RATE) + -clean_sqr(440))[:1.0])))

graph.plot(sqr(1000)[:0.01])
graph.plot(perfect_sqr(1000, 0.01))

np.mean(np.abs(list((perfect_sqr(1000, SAMPLE_RATE) + -sqr(1000))[:1.0])))
np.mean(np.abs(list((perfect_sqr(1000, SAMPLE_RATE) + -clean_sqr(1000))[:1.0])))
np.mean(np.abs(list((perfect_sqr(1000, SAMPLE_RATE) + -clean_sqr2(1000, 256))[:1.0])))

play(sqr(1000))
play(clean_sqr(1000))
play(clean_sqr2(1000, 1024))
play()

from prof import profile
profile.reset()
_ = list((profile("0", sqr(1000)) + profile("1", clean_sqr(1000)) + profile("2", clean_sqr2(1000, 1024)))[:1.0])
profile.dump()

# Now let's take the start-up cost into account.
profile.reset()
_ = list((profile("0", lambda: sqr(1000)()) + profile("1", lambda: clean_sqr(1000)()) + profile("2", lambda: clean_sqr2(1000, 1024)()) + profile("3", lambda: clean_sqr2(1000, 16384)()))[:1.0])
profile.dump()

# Looks like the Wavetable version is still a good bet.
# For completeness:
def cleanest_sqr(freq):
    return sum(osc(freq*k)/k for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)) * 4/math.pi

np.mean(np.abs(list((perfect_sqr(1000, SAMPLE_RATE) + -cleanest_sqr(1000))[:1.0])))

class Sqr(Stream):
    def __init__(self, freq, phase=0):
        self.freq = freq
        self.phase = phase
    
    def __call__(self):
        return (4/math.pi*sum(math.sin(self.phase*k)/k for k in range(1, int(SAMPLE_RATE/2/self.freq) + 1, 2)), Sqr(self.freq, self.phase + 2*math.pi*self.freq/SAMPLE_RATE))

class Additive(Stream):
    def __init__(self, parts, phase=0):
        self.parts = parts
        self.phase = phase
    
    def __call__(self):
        return (sum(math.sin(self.phase*freq)*amplitude for amplitude, freq in self.parts), Additive(self.parts, self.phase + 2*math.pi/SAMPLE_RATE))

def add_sqr(freq):
    return Additive([(4/math.pi/k, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)])

def additive(parts, phase=0):
    def closure():
        return (sum(math.sin(phase*freq)*amplitude for amplitude, freq in parts), additive(parts, phase + 2*math.pi/SAMPLE_RATE))
    return closure

def add_sqr2(freq):
    return additive([(4/math.pi/k, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)])

@raw_stream
def additive2(parts, phase=0):
    return lambda: (sum(math.sin(phase*freq)*amplitude for amplitude, freq in parts), additive(parts, phase + 2*math.pi/SAMPLE_RATE))

def add_sqr3(freq):
    return additive2([(4/math.pi/k, freq*k) for k in range(1, int(SAMPLE_RATE/2/freq) + 1, 2)])

np.mean(np.abs(list((perfect_sqr(1000, SAMPLE_RATE) + -Stream(add_sqr2(1000)))[:1.0])))

graph.plot(add_sqr(440)[:1.0])

profile.reset()
_ = list((profile("0", lambda: sqr(1000)()) +
          profile("1", lambda: clean_sqr(1000)()) +
          profile("2", lambda: clean_sqr2(1000, 1024)()) +
          profile("3", lambda: clean_sqr2(1000, 16384)()) +
          profile("4", lambda: cleanest_sqr(1000)()) +
          profile("5", lambda: Sqr(1000)()) +
          profile("6", lambda: add_sqr(1000)()) +
          profile("7", lambda: add_sqr2(1000)()) +
          profile("8", lambda: add_sqr3(1000)()) +
          profile("osc", lambda: osc(1000)()))[:5.0])
profile.dump()

play(sqr(440))
play(Sqr(440))
play(add_sqr3(440))
play()

# Wavetable provides a nice tradeoff between error and time (and it's a straight upgrade to sqr()).
# But additive() provides unbeatable error and seemingly decent performance.

# 3/12/2021

import inspect
import collections

def test_decorator(f):
    print(inspect.getsource(f))

@test_decorator
def foo():
    return "bar"

from core import *
# Convert any iterator into a stream
# Note that this is NOT replayable: next(it) changes the state of the iterator.
# For replayability (but not divergence), combine with memoize().
@raw_stream
def iter_stream(it):
    if not isinstance(it, collections.abc.Iterator):
        it = iter(it)
    # alt definition: silence.map(lambda _: next(it))
    def closure():
        return (next(it), closure)
    return closure

def gen_stream(f):
    return lambda *args, **kwargs: iter_stream(f(*args, **kwargs))

def memo_gen_stream(f):
    return lambda *args, **kwargs: memoize(iter_stream(f(*args, **kwargs)))

def _osc(freq):
    phase = 0
    while True:
        yield math.sin(phase)
        phase += 2*math.pi*freq/SAMPLE_RATE

gosc = gen_stream(_osc)
mosc = memo_gen_stream(_osc)

from prof import profile
profile.reset()
_ = list((profile('a', osc(440)) + profile('b', gosc(440)) + profile('c', mosc(440)))[:200.0])
profile.dump()

# Surprisingly close. .34, .44, .40 percent respectively.
# Unclear how mosc would beat gosc, though...
# Anyway, this looks kind of decent until replayability matters.
# You can even use this to iterate over another stream... at the cost of replayability.

import ast
import astor

def make_cfg(fn):
    id = -1
    def make_name(id):
        return ast.Name(id=f'_{hash(fn):x}_{id:x}', ctx=ast.Load())

    # TODO: Only transform a branch or loop if it has a yield somewhere in its subtree.
    def build_cfg(statements, successor=None):
        # print('build_cfg', statements, successor)
        nonlocal id
        id += 1
        cfg = {'id': id, 'name': make_name(id), 'children': []}
        stmts = []
        for i, statement in enumerate(statements):
            # print(astor.dump_tree(statement))
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Yield):
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('yield'), statement.value.value, make_name(id+1)], ctx=ast.Load())))
                # Break off into next CFG.
                cfg['statements'] = stmts
                cfg['children'] = [build_cfg(statements[i+1:], successor)]
                return cfg
            elif isinstance(statement, ast.Return):
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('return'), statement.value], ctx=ast.Load())))
                cfg['statements'] = stmts
                return cfg
            elif isinstance(statement, ast.If):
                rest_cfg = build_cfg(statements[i+1:], successor)
                successor = make_name(rest_cfg['id'])
                then_cfg = build_cfg(statement.body, successor)
                else_cfg = build_cfg(statement.orelse, successor)
                stmts.append(ast.If(test=statement.test,
                                    body=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), make_name(then_cfg['id'])], ctx=ast.Load()))],
                                    orelse=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), make_name(else_cfg['id'])], ctx=ast.Load()))]))
                cfg['statements'] = stmts
                cfg['children'] = [then_cfg, else_cfg, rest_cfg]
                return cfg
            elif isinstance(statement, ast.While):
                # TODO: Handle break, continue.
                cond_cfg = build_cfg([], None)
                rest_cfg = build_cfg(statements[i+1:], successor)
                then_successor = make_name(cond_cfg['id'])
                else_successor = make_name(rest_cfg['id'])
                then_cfg = build_cfg(statement.body, then_successor)
                else_cfg = build_cfg(statement.orelse, else_successor)
                cond_cfg['statements'].append(ast.If(test=statement.test,
                                                     body=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), make_name(then_cfg['id'])], ctx=ast.Load()))],
                                                     orelse=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), make_name(else_cfg['id'])], ctx=ast.Load()))]))
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('bounce'), then_successor], ctx=ast.Load())))
                cfg['statements'] = stmts
                cfg['children'] = [cond_cfg, then_cfg, else_cfg, rest_cfg]
                return cfg
            elif isinstance(statement, ast.For):
                # TODO
                pass
            else:
                stmts.append(statement)
        if successor:
            stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('bounce'), successor], ctx=ast.Load())))
        cfg['statements'] = stmts
        return cfg
    return build_cfg(fn.body)

def print_cfg(cfg):
    print("CFG:", cfg['id'])
    for statement in cfg['statements']:
        print('    ' + astor.dump_tree(statement))
    for child in cfg['children']:
        print_cfg(child)

def finish_conversion(cfg):
    defs = []
    def dfs(cfg):
        args = ast.arguments(args=[], kwonlyargs=[], kw_defaults=[], defaults=[])
        defs.append(ast.FunctionDef(name=cfg['name'].id, args=args,
                                    body=cfg['statements'], decorator_list=[]))
        for child in cfg['children']:
            dfs(child)
    dfs(cfg)
    m = ast.Module(defs)
    ast.fix_missing_locations(m)
    return m

def test_decorator(f):
    tree = ast.parse(inspect.getsource(f))
    fn = tree.body[0]
    # print(astor.dump_tree(fn))
    # for statement in fn.body:
    #     if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Yield):
    #         print("Yield:", astor.dump_tree(statement.value.value))
    #     else:
    #         print(astor.dump_tree(statement))
    cfg = make_cfg(fn)
    print_cfg(cfg)

def generator_to_stream(f):
    tree = ast.parse(inspect.getsource(f))
    fn = tree.body[0]
    cfg = make_cfg(fn)
    converted = finish_conversion(cfg)
    for defn in converted.body:
        print(astor.dump_tree(defn))
    global c
    exec(compile(converted, f.__code__.co_filename, 'exec'), globals())
    return globals()[cfg['name'].id]

# @test_decorator
@generator_to_stream
def foo():
    yield 1
    if True:
        yield 2
        print("yay")
    else:
        print("nay")
    print("next up")
    i = 0
    while i < 3:
        print(i)
        yield i
        i += 1 
    return 3

# To be continued... passing locals (including arguments), supporting for, continue, break...
