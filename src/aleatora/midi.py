import mido
from .core import *

# TODO: Events as lists of messages.
# (This will address the issue of simultaneous events, or delta time = 0 in MIDI data.)

# Example usage:
# print(mido.get_input_names())  # List available MIDI inputs.
# p = mido.open_input(mido.get_input_names()[1])
# play(poly_instrument, event_stream(p))

get_input_names = mido.get_input_names

@stream
def input_stream(port=None):
    if port is None:
        port = get_input_names()[-1]
    if isinstance(port, str):
        port = mido.open_input(port)
    return repeat(port.poll)

# TODO: test this
def file_stream(filename, include_meta=False):
    def message_to_events(message):
        wait = const(None)[:int(message.time/SAMPLE_RATE)]
        if message.is_meta and not include_meta:
            return wait
        else:
            return wait >> cons(message, empty)
    return iter_to_stream(mido.MidiFile(filename)).map(message_to_events).join()

def render(stream, filename, rate=None, bpm=120):
    if rate is None:
        rate = SAMPLE_RATE
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    t = 0
    for message in stream:
        if message:
            ticks = int(t * (bpm / 60) * mid.ticks_per_beat)
            t -= ticks / mid.ticks_per_beat / (bpm / 60)
            message.time = ticks
            track.append(message)
        t += 1/rate
    mid.save(filename)

# Instruments take a stream of mido-style messages
# (objects with `type`, `note`, `velocity` - or None, indicating no message)
# and produce a stream of samples.
# Instruments may persist (continue streaming even when they are only producing silence) or not.
# Persisting is useful for playing an instrument for a live or indeterminate source,
# while not persisting is useful for sequencing, or building up instruments
# (as in converting a monophonic instrument to polyphonic).

# Simple sine instrument. Acknowledges velocity, retriggers.
@raw_stream(instrument=True)
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


# Convert a monophonic instrument into a polyphonic instrument.
# Assumes the monophonic instrument takes a boolean argument called `persist`.
def poly(monophonic_instrument, persist_internal=False):
    # Provides a 'substream' of messages for a single voice in a polyphonic instrument.
    def make_event_substream():
        substream = lambda: (substream.message, substream)
        substream.message = None
        return substream

    @raw_stream(register=False)
    def polyphonic_instrument(stream, substreams={}, voices=[], persist=True):
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
                        new_voice = monophonic_instrument(substream, persist=persist_internal)
                        # TODO: avoid duplication here?
                        result = new_voice()
                        if not isinstance(result, Return):
                            sample, new_voice = result
                            acc += sample
                            next_voices.append(new_voice)
                elif event.type == 'note_off':
                    if event.note in substreams:
                        substreams[event.note].message = event
                        if not persist_internal:
                            next_substreams = substreams.copy()
                            del next_substreams[event.note]

            if not persist and not next_voices:
                return Result()

            for voice in voices:
                result = voice()
                if not isinstance(result, Return):
                    sample, next_voice = result
                    acc += sample
                    next_voices.append(next_voice)
            return (acc, polyphonic_instrument(next_stream, next_substreams, next_voices, persist))
        return closure
    return polyphonic_instrument

@stream(instrument=True)
def poly_instrument(event_stream):
    return poly(mono_instrument)(event_stream)


# Takes [(pitch, duration)] and converts it to a Stream of Messages.
# TODO: support velocity?
# TODO: allow sequence to be a stream?
def seq_to_events(sequence, bpm=60):
    events = []
    time = 0
    for pitch, duration in sequence:
        events.append((int(time), mido.Message(type='note_on', note=pitch)))
        time += duration * 60 / bpm * SAMPLE_RATE
        events.append((int(time) - 1, mido.Message(type='note_off')))
    return events_in_time(events)