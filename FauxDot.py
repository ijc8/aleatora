import collections

import core

from _FoxDot.Patterns import P, Pattern, PGroup, PGroupPrime, PGroupPlus, ParsePlayString
from _FoxDot.Buffers import Samples
from _FoxDot.Scale import get_freq_and_midi, Scale
from _FoxDot.Root import Root


def pattern_to_stream(pattern, cycle=True):
    # We use this instead of doing core.to_stream(pattern) (which would first convert the pattern to a list).
    # This is important for getting things like PRand to work right.
    if cycle:
        return core.mod(len(pattern)).map(lambda i: pattern.getitem(i))
    else:
        return core.count()[:len(pattern)].map(lambda i: pattern.getitem(i))

def patternish_to_stream(patternish, cycle=True):
    # Convert a pattern-like object to a stream.
    if isinstance(patternish, collections.abc.Iterable):
        return pattern_to_stream(Pattern(patternish), cycle=cycle)
    elif cycle:
        return core.const(patternish)
    else:
        return core.cons(patternish, empty)

# There are other things that can be patternish, like `root` or `sample`, but this just deals timing.
# (degree is included because it may contain PGroups that affect subdivision timing.)
def event_stream(degree, dur=1, sus=None, delay=0, amp=1, bpm=120):
    if sus is None:
        sus = dur
    degree = patternish_to_stream(degree)
    dur = patternish_to_stream(dur)
    sus = patternish_to_stream(sus)
    delay = patternish_to_stream(delay)
    amp = patternish_to_stream(amp)
    bpm = patternish_to_stream(bpm)
    @core.raw_stream
    def _event_stream(degree_stream, dur_stream, sus_stream, delay_stream, amp_stream, bpm_stream):
        def closure():
            result = degree_stream()
            if isinstance(result, core.Return):
                return result
            degree, next_degree_stream = result
            dur, next_dur_stream = dur_stream()
            sus, next_sus_stream = sus_stream()
            delay, next_delay_stream = delay_stream()
            amp, next_amp_stream = amp_stream()
            bpm, next_bpm_stream = bpm_stream()

            next_stream = _event_stream(next_degree_stream, next_dur_stream, next_sus_stream, next_delay_stream, next_amp_stream, next_bpm_stream)
            # TODO: May need to deal with PGroupOr (which has a custom calculate_sample) here or punt.
            # TODO: Check how these are supposed to interact with sus and delay.
            # NOTE: We should not see nested patterns here, because these should already be taken care of by pattern_to_string.
            if isinstance(degree, PGroupPlus):
                # Spread over `sus`.
                return (_event_stream(patternish_to_stream(degree.data, cycle=False), core.const(sus / len(degree)), core.const(sus), core.const(delay), core.const(amp), core.const(bpm)) >> next_stream)()
            elif isinstance(degree, PGroupPrime):
                # All of the other PGroupPrime subclasses spread over `dur`.
                return (_event_stream(patternish_to_stream(degree.data, cycle=False), core.const(dur / len(degree)), core.const(sus), core.const(delay), core.const(amp), core.const(bpm)) >> next_stream)()
            elif isinstance(degree, PGroup):
                # Everything in here needs to happen simultaneously.
                raise NotImplementedError
            return ((degree, dur, sus, delay, amp, bpm), next_stream)
        return closure
    return _event_stream(degree, dur, sus, delay, amp, bpm)

# Used for beat(), which is the analog of play().
def events_to_samples(event_stream):
    def process_event(event):
        # NOTE: Like play(), this ignores `sus`.
        degree, dur, sus, delay, amp, bpm = event
        sample = Samples.getBufferFromSymbol(degree).stream
        if amp != 1:
            sample *= amp
        # NOTE: `delay` does not throw off future timing.
        if delay != 0:
            delay *= 60/bpm
            sample = core.silence[:delay] >> sample
        dur *= 60/bpm
        return core.fit(sample, dur)
    return core.lazy_concat(event_stream.map(process_event))

# maybe support amplify?
def beat(pattern, dur=0.5, sus=None, delay=0, sample=0, amp=1, bpm=120):
    if isinstance(pattern, str):
        pattern = ParsePlayString(pattern)
    if sus is None:
        sus = dur
    return events_to_samples(event_stream(pattern, dur, sus, delay, amp, bpm))

# TODO: maybe settle on this or mido.Message? mido.Message unfortunately doesn't allow float values (true to MIDI).
# would use namedtuple but it lacks `defaults` in this version of pypy
class Message:
    def __init__(self, type, note, velocity=None):
        self.type = type
        self.note = note
        self.velocity = velocity
# BTW: may want to switch abstraction from one event per sample to a collection of events per sample
# so e.g. notes can start simultaneously
# TODO: can root, scale, oct be patterns?
# Used for regular instruments (everything except play(), e.g. pluck()).
def events_to_messages(event_stream, root=Root.default, scale=Scale.default, oct=5):
    def closure():
        event, next_event_stream = event_stream()
        degree, dur, sus, delay, amp, bpm = event
        _, pitch = get_freq_and_midi(degree, oct, root, scale)
        if delay != 0:
            delay *= 60/bpm
        dur *= 60/bpm
        sus *= 60/bpm
        # TODO: For the moment, we're capping sus at dur - 1 (sample). (does FoxDot allow overlap between notes in a single layer?)
        sus = min(dur - 1/core.SAMPLE_RATE, sus)
        noteon = Message(type='note_on', note=pitch, velocity=int(amp*127))
        noteoff = Message(type='note_off', note=pitch)
        recur = events_to_messages(next_event_stream, root=root, scale=scale, oct=oct)
        return (noteon, core.const(None)[:sus] >> core.cons(noteoff, core.const(None)[:dur-sus-1/core.SAMPLE_RATE] >> recur))
    return closure

# Return an event stream suitable for passing into an instrument.
def tune(degree, dur=1, sus=None, delay=0, amp=1, bpm=120, root=Root.default, scale=Scale.default, oct=5):
    return events_to_messages(event_stream(degree, dur=dur, sus=sus, delay=delay, amp=amp, bpm=bpm), root=root, scale=scale, oct=oct)


# other things for maybe eventual support: https://foxdot.org/docs/player-effects/
# most of these should probably translate to stream functions applied to instrumental voices
