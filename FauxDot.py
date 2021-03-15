import collections

import core

from _FoxDot.Patterns import P, Pattern, PGroup, PGroupPrime, PGroupPlus, ParsePlayString
from _FoxDot.Buffers import Samples


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

# @core.raw_stream
# def sampleplayer_stream(event_stream, time=0):
#     def closure():
#         (degree, dur, sus, delay, amp, bpm), next_event_stream = event_stream()
#         sample = Samples.getBufferFromSymbol(degree).stream
#         next_time = time + dur * 60/bpm
#         if amp != 1:
#             sample *= amp
#         return ((time, sample), sampleplayer_stream(next_event_stream, next_time))
#     return closure

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
    # TODO: map characters to samples via Samples.getBufferFromSymbol(char, index).stream
    # convert each pattern-able arg to a stream
    # pull from all of them to generate each event
    # then just concat. ez.
    return events_to_samples(event_stream(pattern, dur, sus, delay, amp, bpm))

    
# later, for instruments, handle `scale` and `root`.

# other things for maybe eventual support: https://foxdot.org/docs/player-effects/
# most of these should probably translate to stream functions applied to instrumental voices
