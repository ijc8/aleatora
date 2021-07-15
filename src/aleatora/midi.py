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

from aleatora.streams.core import FunctionStream

from .streams import const, events_in_time, m2f, osc, repeat, SAMPLE_RATE, stream

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

def input_stream(port=None):
    if port is None:
        port = get_input_names()[-1]
    if isinstance(port, str):
        port = mido.open_input(port)
    return repeat(lambda: tuple(port.iter_pending()))

# TODO: test this
@stream
def file_stream(filename, include_meta=False):
    simultaneous = []
    timestamp = 0
    for message in mido.MidiFile(filename):
        delta = message.time/SAMPLE_RATE
        if delta == 0:
            if not message.is_meta or include_meta:
                simultaneous.append(message)
        else:
            timestamp += delta
            yield from const(())[:int(timestamp)]
            timestamp -= int(timestamp)
            if not message.is_meta or include_meta:
                yield tuple(simultaneous)
            simultaneous = []

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

# Simple mono instrument. Acknowledges velocity, retriggers.
@stream
def mono_instrument(stream, freq=0, amp=0, velocity=0, waveform=osc):
    freq_stream = repeat(lambda: freq)
    waveform_iter = iter(waveform(freq_stream))
    for events in stream:
        if not events:
            pass
        elif events[-1].type == 'note_on':
            freq = m2f(events[-1].note)
            velocity = events[-1].velocity
        elif events[-1].type == 'note_off':
            velocity = 0
        target_amp = velocity / 127
        if amp > target_amp:
            amp = max(target_amp, amp - 1e-4)
        else:
            amp = min(target_amp, amp + 1e-6 * velocity**2)
        yield amp * next(waveform_iter)
    while amp > 0:
        if amp > target_amp:
            amp = max(target_amp, amp - 1e-4)
        else:
            amp = min(target_amp, amp + 1e-6 * velocity**2)
        yield amp * next(waveform_iter)

# Convert a monophonic instrument into a polyphonic instrument.
def poly(monophonic_instrument, persist_internal=False):
    # Provides a 'substream' of messages for a single voice in a polyphonic instrument.
    def make_event_substream():
        @FunctionStream
        def substream():
            while substream.last_event is None:
                yield substream.events
            yield (substream.last_event,)
        substream.events = ()
        substream.last_event = None
        return substream

    @stream
    def polyphonic_instrument(stream, substreams={}, voices={}, **kwargs):
        for events in stream:
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
                        substream = make_event_substream()
                        substream.events = (event,)
                        substreams[event.note] = substream
                        voices[event.note] = iter(monophonic_instrument(substream, **kwargs))
                elif event.type == 'note_off':
                    if event.note in substreams:
                        if persist_internal:
                            substreams[event.note].events = (event,)
                        else:
                            substreams[event.note].last_event = event
                            del substreams[event.note]

            dead_list = []
            for note, voice in voices.items():
                try:
                    sample = next(voice)
                    acc += sample
                except StopIteration:
                    dead_list.append(note)
            for note in dead_list:
                del voices[note]
                if note in substreams:
                    del substreams[note]
            yield acc
    return polyphonic_instrument

def poly_instrument(event_stream, **kwargs):
    return poly(mono_instrument)(event_stream, **kwargs)


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
