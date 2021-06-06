"""Support for event streams, messages, instruments, MIDI devices, and MIDI files.

This module includes functions for working with MIDI devices and files,
but it also describes a basic interface for _events_ and _instruments_
which is useful even if you don't care about MIDI itself.

A event consists of some data; for example, a typical MIDI message like `Message(type='note_on', note=60, velocity=100)`.
The important thing is that events do not include timing information. Instead, the timing is inherent in the event stream.
Event streams consist of tuples of events. The timestamp of an event is given by its position in the stream.
At any point in the stream, multiple events may occur simultaneously (tuple of length > 1), or no events may occur (empty tuple).

Because event streams yield tuples, they may be composed in parallel by addition:
`event_stream_a + event_stream_b` creates a combined event stream with all the events from both.

An _instrument_ is any function that takes an event stream and returns a sample stream.

Example usage:
play(midi.poly_instrument(midi.input_stream()))
"""
import mido

from .core import *

get_input_names = mido.get_input_names

# This is used interchangably with mido.Message, which (true to MIDI) doesn't allow float vlaues.
# (Would use a namedtuple, but they lacks `defaults` in the version of PyPy I'm using.)
class Message:
    def __init__(self, type, note, velocity=None):
        self.type = type
        self.note = note
        self.velocity = velocity
    
    def __repr__(self):
        return f"Message({self.type}, {self.note}, {self.velocity})"

@stream
def input_stream(port=None):
    if port is None:
        port = get_input_names()[-1]
    if isinstance(port, str):
        port = mido.open_input(port)
    return repeat(lambda: tuple(port.iter_pending()))

# TODO: test this
def file_stream(filename, include_meta=False):
    def collect_messages():
        simultaneous = []
        timestamp = 0
        for message in mido.MidiFile(filename):
            delta = message.time/SAMPLE_RATE
            if delta == 0:
                if not message.is_meta or include_meta:
                    simultaneous.append(message)
            else:
                timestamp += delta
                yield const(())[:int(timestamp)]
                timestamp -= int(timestamp)
                if not message.is_meta or include_meta:
                    yield cons(tuple(simultaneous), empty)
                simultaneous = []
    return iter_to_stream(collect_messages()).join()

# TODO: test this
def render(stream, filename, rate=None, bpm=120):
    if rate is None:
        rate = SAMPLE_RATE
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    t = 0
    for messages in stream:
        for message in messages:
            message.time = int(t)
            t -= int(t)
            track.append(message)
        t += 1/rate * (bpm / 60) * mid.ticks_per_beat
    mid.save(filename)

# Instruments take a stream of tuples of MIDI-style messages
# (objects with `type`, `note`, `velocity`) and produce a stream of samples.
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
        events, next_stream = result
        if not events:
            next_freq = freq
            next_velocity = velocity
        elif events[-1].type == 'note_on':
            next_freq = m2f(events[-1].note)
            next_velocity = events[-1].velocity
        elif events[-1].type == 'note_off':
            next_freq = freq
            next_velocity = 0
        target_amp = next_velocity / 127
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
        substream = lambda: (substream.events, substream)
        substream.events = ()
        return substream

    @raw_stream(register=False)
    def polyphonic_instrument(stream, substreams={}, voices=[], persist=True):
        def closure():
            result = stream()
            if isinstance(result, Return):
                return result
            events, next_stream = result
            next_substreams = substreams
            next_voices = []
            acc = 0
            # Clear old messages:
            for substream in substreams.values():
                substream.events = ()
            for event in events:
                if event.type == 'note_on':
                    if event.note in substreams:
                        # Retrigger existing voice
                        substreams[event.note].events = (event,)
                    else:
                        # New voice
                        if next_substreams is substreams:
                            next_substreams = substreams.copy()
                        substream = make_event_substream()
                        substream.events = (event,)
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
                        substreams[event.note].events = (event,)
                        if not persist_internal:
                            if next_substreams is substreams:
                                next_substreams = substreams.copy()
                            del next_substreams[event.note]

            if not persist and not next_voices:
                return Return()

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
        events.append((int(time), Message(type='note_on', note=pitch)))
        time += duration * 60 / bpm * SAMPLE_RATE
        events.append((int(time) - 1, Message(type='note_off')))
    return events_in_time(events)