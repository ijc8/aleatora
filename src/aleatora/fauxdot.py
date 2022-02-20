import collections
import heapq
from typing import TYPE_CHECKING

from .streams import const, empty, fit, just, SAMPLE_RATE, silence, stream, Stream
from . import midi
from . import wav

importError = None

try:
    from FoxDotPatterns import (
        GeneratorPattern, P, Pattern, PEuclid, PGroup, PGroupPrime, PGroupPlus, PGroupOr, PRand,
        ParsePlayString, Root, Scale, get_freq_and_midi, Samples, nil
    )

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
except ImportError as exc:
    # Defer import error to time of usage.
    importError = ImportError(f"Missing optional dependency '{exc.name}'. Install via `python -m pip install {exc.name}`.")
    if TYPE_CHECKING:
        raise importError
    else:
        class Fake:
            def __call__(*args):
                raise importError
            def __getitem__(*args):
                raise importError
            def __getattribute__(self, name):
                if name == 'default':
                    return Fake()
                raise importError
        Root = Scale = P = PRand = PEuclid = Fake()


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
                # Everything in here needs to happen simultaneously; yield a list of layers (and timing info).
                yield ([_event_stream(pattern_to_stream(layer), const(dur), const(sus), const(delay), const(amp), const(bpm), const(sample)) for layer in degree.data], dur, bpm)
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

def beat(pattern, dur=0.5, sus=None, delay=0, amp=1, bpm=120, sample=0):
    if importError:
        raise ImportError
    if sus is None:
        sus = dur
    return events_to_samples(event_stream(pattern, dur, sus, delay, amp, bpm, sample))

# TODO: can root, scale, oct be patterns?
# Used for regular instruments (everything except play(), e.g. pluck()).
@stream
def events_to_messages(event_stream, root=Root.default, scale=Scale.default, oct=5):
    # Maintain a priority queue of upcoming events to yield.
    # We use this to support cases where `sus` is greater than `dur`
    # (where one note's note_off will come after a subsequent note's note_on).
    queue = []
    t = 0
    i = 0

    def enqueue_event(event, t):
        nonlocal i
        # Each event contains either a single degree or a list of simultaneous substreams.
        if isinstance(event[0], list):
            # Group: layers should occur simultaneously
            layers, dur, bpm = event
            for layer in layers:
                st = t
                for event in layer:
                    st += enqueue_event(event, st)
        else:
            degree, dur, sus, delay, amp, bpm, _ = event
            _, pitch = get_freq_and_midi(degree, oct, root, scale)
            if delay != 0:
                delay *= 60/bpm
            sus *= 60/bpm
            noteon = midi.Message(type='note_on', note=pitch, velocity=int(amp*127))
            noteoff = midi.Message(type='note_off', note=pitch)
            heapq.heappush(queue, (t, i, noteon))
            heapq.heappush(queue, (t + sus, i + 1, noteoff))
            i += 2
        return dur * 60/bpm

    for event in event_stream:
        dur = enqueue_event(event, t)
        end = t + dur
        while queue and queue[0][0] < end:
            time, _, event = heapq.heappop(queue)
            yield from const(())[:time - t]
            events = (event,)
            while queue and queue[0][0] <= time:
                events += (heapq.heappop(queue)[2],)
            yield events
            t = time + 1/SAMPLE_RATE
        yield from const(())[:end - t]
        t = end
    # Flush any remaining `note_off`s.
    while queue:
        time, _, event = heapq.heappop(queue)
        yield from const(())[:time - t]
        events = (event,)
        while queue and queue[0][0] <= time:
            events += (heapq.heappop(queue)[2],)
        yield events
        t = time + 1/SAMPLE_RATE


# Return an event stream suitable for passing into an instrument.
def tune(degree, dur=1, sus=None, delay=0, amp=1, bpm=120, root=Root.default, scale=Scale.default, oct=5):
    if importError:
        raise importError
    return events_to_messages(event_stream(degree, dur=dur, sus=sus, delay=delay, amp=amp, bpm=bpm), root=root, scale=scale, oct=oct)


# other things for maybe eventual support: https://foxdot.org/docs/player-effects/
# most of these should probably translate to stream functions applied to instrumental voices
