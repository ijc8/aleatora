import collections

from .streams import const, empty, fit, just, SAMPLE_RATE, silence, stream
from . import midi
from . import wav

try:
    from FoxDotPatterns import (
        P, Pattern, PGroup, PGroupPrime, PGroupPlus, PGroupOr, PRand, ParsePlayString,
        Root, Scale, get_freq_and_midi, Samples, nil
    )
except ImportError as exc:
    raise ImportError(
        "Missing optional dependency 'FauxDotPatterns'.\n"
        "Install via `python -m pip install https://github.com/ijc8/FoxDotPatterns/archive/refs/heads/master.zip`."
    )

nil.stream = empty

def buffer_read(buffer):
    buffer.stream = wav.load(buffer.fn)

def buffer_free(buffer):
    # Nothing to see here; buffer should get garbage-collected, and so should buffer.stream.
    pass

Samples.buffer_read = buffer_read
Samples.buffer_free = buffer_free


def pattern_to_stream(pattern, cycle=True):
    if cycle:
        return stream(pattern).cycle()
    return stream(pattern)

def patternish_to_stream(patternish, cycle=True):
    # Convert a pattern-like object to a stream.
    if isinstance(patternish, collections.abc.Iterable):
        return pattern_to_stream(Pattern(patternish), cycle=cycle)
    elif cycle:
        return const(patternish)
    else:
        return just(patternish)

# There are other things that can be patternish, like `root` or `sample`, but this just deals timing.
# (degree is included because it may contain PGroups that affect subdivision timing.)
def event_stream(degree, dur=1, sus=None, delay=0, amp=1, bpm=120, cycle=True):
    if sus is None:
        sus = dur
    degree = patternish_to_stream(degree, cycle=cycle)
    dur = patternish_to_stream(dur)
    sus = patternish_to_stream(sus)
    delay = patternish_to_stream(delay)
    amp = patternish_to_stream(amp)
    bpm = patternish_to_stream(bpm)
    @stream
    def _event_stream(degree_stream, dur_stream, sus_stream, delay_stream, amp_stream, bpm_stream):
        for (degree, dur, sus, delay, amp, bpm) in zip(degree_stream, dur_stream, sus_stream, delay_stream, amp_stream, bpm_stream):
            # TODO: May need to deal with PGroupOr (which has a custom calculate_sample) here or punt.
            # TODO: Check how these are supposed to interact with sus and delay.
            # NOTE: We should not see nested patterns here, because these should already be taken care of by pattern_to_string.
            if isinstance(degree, PGroupOr):
                pass
            elif isinstance(degree, PGroupPlus):
                # Spread over `sus`.
                yield from _event_stream(patternish_to_stream(degree.data, cycle=False), const(sus / len(degree)), const(sus), const(delay), const(amp), const(bpm))
            elif isinstance(degree, PGroupPrime):
                # All of the other PGroupPrime subclasses spread over `dur`.
                yield from _event_stream(patternish_to_stream(degree.data, cycle=False), const(dur / len(degree)), const(sus), const(delay), const(amp), const(bpm))
            elif isinstance(degree, PGroup):
                # Everything in here needs to happen simultaneously.
                raise NotImplementedError
            else:
                yield (degree, dur, sus, delay, amp, bpm)
    return _event_stream(degree, dur, sus, delay, amp, bpm)

# Used for beat(), which is the analog of play().
@stream
def events_to_samples(event_stream):
    for event in event_stream:
        # NOTE: Like play(), this ignores `sus`.
        degree, dur, sus, delay, amp, bpm = event
        index = 0
        if isinstance(degree, PGroupOr):
            # Support basic sample-choosing syntax, as in |x2|.
            index = degree.meta[0]
            degree = degree[0]
        sample = Samples.getBufferFromSymbol(degree, index).stream
        if amp != 1:
            sample *= amp
        # NOTE: `delay` does not throw off future timing.
        if delay != 0:
            delay *= 60/bpm
            sample = silence[:delay] >> sample
        dur *= 60/bpm
        yield from fit(sample, dur)

# TODO: Support sample
# maybe support amplify?
def beat(pattern, dur=0.5, sus=None, delay=0, sample=0, amp=1, bpm=120):
    if isinstance(pattern, str):
        pattern = ParsePlayString(pattern)
    if sus is None:
        sus = dur
    return events_to_samples(event_stream(pattern, dur, sus, delay, amp, bpm))

# TODO: can root, scale, oct be patterns?
# Used for regular instruments (everything except play(), e.g. pluck()).
@stream
def events_to_messages(event_stream, root=Root.default, scale=Scale.default, oct=5):
    for event in event_stream:
        degree, dur, sus, delay, amp, bpm = event
        _, pitch = get_freq_and_midi(degree, oct, root, scale)
        if delay != 0:
            delay *= 60/bpm
        dur *= 60/bpm
        sus *= 60/bpm
        # TODO: For the moment, we're capping sus at dur - 1 (sample). (does FoxDot allow overlap between notes in a single layer?)
        sus = min(dur - 1/SAMPLE_RATE, sus)
        noteon = midi.Message(type='note_on', note=pitch, velocity=int(amp*127))
        noteoff = midi.Message(type='note_off', note=pitch)
        yield (noteon,)
        yield from const(())[:sus]
        yield (noteoff,)
        yield from const(())[:dur-sus-1/SAMPLE_RATE]

# Return an event stream suitable for passing into an instrument.
def tune(degree, dur=1, sus=None, delay=0, amp=1, bpm=120, root=Root.default, scale=Scale.default, oct=5, cycle=True):
    return events_to_messages(event_stream(degree, dur=dur, sus=sus, delay=delay, amp=amp, bpm=bpm, cycle=cycle), root=root, scale=scale, oct=oct)


# other things for maybe eventual support: https://foxdot.org/docs/player-effects/
# most of these should probably translate to stream functions applied to instrumental voices
