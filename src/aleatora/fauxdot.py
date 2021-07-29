import collections

from .streams import const, empty, fit, just, SAMPLE_RATE, silence, stream, Stream
from . import midi
from . import wav

try:
    from FoxDotPatterns import (
        GeneratorPattern, P, Pattern, PGroup, PGroupPrime, PGroupPlus, PGroupOr, PRand, ParsePlayString,
        Root, Scale, get_freq_and_midi, Samples, nil
    )
except ImportError as exc:
    raise ImportError(f"Missing optional dependency '{exc.name}'. Install via `python -m pip install {exc.name}`.")

nil.stream = empty

def buffer_read(buffer):
    buffer.stream = wav.load(buffer.fn)

def buffer_free(buffer):
    # Nothing to see here; buffer should get garbage-collected, and so should buffer.stream.
    pass

Samples.buffer_read = buffer_read
Samples.buffer_free = buffer_free

# Monkey-patch GeneratorPattern to avoid caching results (for nondeterministic replayability).
def GeneratorPattern_getitem(self, index=None, *args):
    """ Calls self.func(index) to get an item if index is not in
        self.history, otherwise returns self.history[index] """
    if index is None:
        index, self.index = self.index, self.index + 1
    return self.func(index)

GeneratorPattern.getitem = GeneratorPattern_getitem


def pattern_to_stream(patternish):
    # Convert a pattern-like object to a stream.
    if isinstance(patternish, Stream):
        return patternish
    elif isinstance(patternish, collections.abc.Iterable):
        return stream(Pattern(patternish))
    else:
        return just(patternish)

# TODO: Handle additional patternish parameters like `root`.
# (degree is included because it may contain PGroups that affect subdivision timing.)
def event_stream(degree, dur=1, sus=None, delay=0, amp=1, bpm=120, sample=0):
    if sus is None:
        sus = dur
    degree = pattern_to_stream(degree)
    dur = pattern_to_stream(dur).cycle()
    sus = pattern_to_stream(sus).cycle()
    delay = pattern_to_stream(delay).cycle()
    amp = pattern_to_stream(amp).cycle()
    bpm = pattern_to_stream(bpm).cycle()
    sample = pattern_to_stream(sample).cycle()
    @stream
    def _event_stream(degree_stream, dur_stream, sus_stream, delay_stream, amp_stream, bpm_stream, sample_stream):
        for (degree, dur, sus, delay, amp, bpm, sample) in zip(degree_stream, dur_stream, sus_stream, delay_stream, amp_stream, bpm_stream, sample_stream):
            # TODO: May need to deal with PGroupOr (which has a custom calculate_sample) here or punt.
            # TODO: Check how these are supposed to interact with sus and delay.
            # NOTE: We should not see nested Patterns here (just groups), because they should already be taken care of by pattern_to_stream.
            if isinstance(degree, PGroupOr):
                yield from _event_stream(pattern_to_stream(degree.data), const(dur), const(sus), const(delay), const(amp), const(bpm), pattern_to_stream(degree.meta[0]).cycle())
            elif isinstance(degree, PGroupPlus):
                # Spread over `sus`.
                yield from _event_stream(pattern_to_stream(degree.data), const(sus / len(degree)), const(sus), const(delay), const(amp), const(bpm), const(sample))
            elif isinstance(degree, PGroupPrime):
                # All of the other PGroupPrime subclasses spread over `dur`.
                yield from _event_stream(pattern_to_stream(degree.data), const(dur / len(degree)), const(sus), const(delay), const(amp), const(bpm), const(sample))
            elif isinstance(degree, PGroup):
                # Everything in here needs to happen simultaneously; yield a list of layers.
                yield [_event_stream(pattern_to_stream(layer), const(dur), const(sus), const(delay), const(amp), const(bpm), const(sample)) for layer in degree.data]
            else:
                yield (degree, dur, sus, delay, amp, bpm, sample)
    return _event_stream(degree, dur, sus, delay, amp, bpm, sample)

# Used for beat(), which is the analog of play().
# TODO: Just write a sampler instrument and use `events_to_messages`.
@stream
def events_to_samples(event_stream):
    for event in event_stream:
        if isinstance(event, list):
            # Group: layers should occur simultaneously
            yield from sum(events_to_samples(layer) for layer in event)
        else:
            # NOTE: Like play(), this ignores `sus`.
            degree, dur, sus, delay, amp, bpm, sample = event
            sample = Samples.getBufferFromSymbol(degree, sample).stream
            if amp != 1:
                sample *= amp
            # NOTE: `delay` does not throw off future timing.
            if delay != 0:
                delay *= 60/bpm
                sample = silence[:delay] >> sample
            dur *= 60/bpm
            yield from fit(sample, dur)

# TODO: Support sample, maybe support amplify.
def beat(pattern, dur=0.5, sus=None, delay=0, amp=1, bpm=120, sample=0):
    if sus is None:
        sus = dur
    return events_to_samples(event_stream(pattern, dur, sus, delay, amp, bpm, sample))

# TODO: can root, scale, oct be patterns?
# Used for regular instruments (everything except play(), e.g. pluck()).
@stream
def events_to_messages(event_stream, root=Root.default, scale=Scale.default, oct=5):
    for event in event_stream:
        # Each event is either a single event (tuple of details) or a list of layers (substreams of the same type).
        if isinstance(event, list):
            # Group: layers should occur simultaneously
            yield from sum((events_to_messages(layer, root, scale, oct) for layer in event), empty)
        else:
            degree, dur, sus, delay, amp, bpm, _ = event
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
def tune(degree, dur=1, sus=None, delay=0, amp=1, bpm=120, root=Root.default, scale=Scale.default, oct=5):
    return events_to_messages(event_stream(degree, dur=dur, sus=sus, delay=delay, amp=amp, bpm=bpm), root=root, scale=scale, oct=oct)


# other things for maybe eventual support: https://foxdot.org/docs/player-effects/
# most of these should probably translate to stream functions applied to instrumental voices
