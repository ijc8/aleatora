import mido
from core import *


# Example usage:
# print(mido.get_input_names())  # List available MIDI inputs.
# p = mido.open_input(mido.get_input_names()[1])
# play(poly(mono_instrument, event_stream(p)))

@raw_stream
def event_stream(port):
    return lambda: (port.poll(), event_stream(port))


# Instruments take a stream of mido-style messages
# (objects with `type`, `note`, `velocity` - or None, indicating no message)
# and produce a stream of samples.
# Instruments may persist (continue streaming even when they are only producing silence) or not.
# Persisting is useful for playing an instrument for a live or indeterminate source,
# while not persisting is useful for sequencing, or building up instruments
# (as in converting a monophonic instrument to polyphonic).


# Simple sine instrument. Acknowledges velocity, retriggers.
@raw_stream
def mono_instrument(stream, freq=0, phase=0, amp=0, velocity=0, persist=True):
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
        return (next_amp * math.sin(next_phase), mono_instrument(next_stream, next_freq, next_phase, next_amp, next_velocity, persist))
    return closure


# Helper for poly().
# Provides a 'substream' of messages for a single voice in a polyphonic instrument.
def _make_event_substream():
    substream = lambda: (substream.message, substream)
    substream.message = None
    return substream

# Convert a monophonic instrument into a polyphonic instrument.
# Assumes the monophonic instrument takes a boolean argument called `persist`.
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
                    substream = _make_event_substream()
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