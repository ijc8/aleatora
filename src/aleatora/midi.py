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

from .streams import const, events_in_time, frame, m2f, osc, ramp, repeat, SAMPLE_RATE, stream

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

@stream
def load(filename, include_meta=False):
    simultaneous = []
    delta = 0
    for message in mido.MidiFile(filename):
        delta += message.time * SAMPLE_RATE
        if int(delta) > 0:
            yield tuple(simultaneous)
            delta -= 1
            yield from const(())[:int(delta)]
            delta -= int(delta)
            simultaneous = []
        if not message.is_meta or include_meta:
            simultaneous.append(message)

def save(stream, filename, rate=None, bpm=120):
    if rate is None:
        rate = SAMPLE_RATE
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    t = 0
    for messages in stream:
        for message in messages:
            if not isinstance(message, mido.Message):
                message = mido.Message(message.type, note=int(message.note), velocity=int(message.velocity or 0))
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
def make_poly(monophonic_instrument, persist_internal=False):
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
    def polyphonic_instrument(stream, **kwargs):
        substreams = {}
        voices = []
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
                        voices.append(iter(monophonic_instrument(substream, **kwargs)))
                elif event.type == 'note_off':
                    if event.note in substreams:
                        if persist_internal:
                            substreams[event.note].events = (event,)
                        else:
                            substreams[event.note].last_event = event
                            del substreams[event.note]

            for i in range(len(voices) - 1, -1, -1):
                try:
                    sample = next(voices[i])
                    acc += sample
                except StopIteration:
                    del voices[i]
            yield acc
        while voices:
            acc = 0
            for i in range(len(voices) - 1, -1, -1):
                try:
                    sample = next(voices[i])
                    acc += sample
                except StopIteration:
                    del voices[i]
            yield acc
    return polyphonic_instrument

# Handy decorator version
def poly(monophonic_instrument=None, persist_internal=False):
    if monophonic_instrument is None:
        return lambda mi: make_poly(mi, persist_internal)
    return make_poly(monophonic_instrument, persist_internal)

poly_instrument = poly(mono_instrument)

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


def sampler(mapping, fade=0.01):
    "Instrument that maps MIDI pitches to streams. Resamples to account for octave jumps."
    def get_sample(pitch, velocity):
        gain = velocity / 127
        if pitch in mapping:
            return mapping[pitch] * gain
        # No such pitch in the mapping; see if there's one in the same pitch class (offset by octaves).
        for m, s in mapping.items():
            if (pitch - m) % 12 == 0:
                return s.resample(2**((pitch - m)/12)) * gain

    @poly
    @stream
    def instrument(stream):
        it = iter([])
        for events in stream:
            if events:
                if events[-1].type == 'note_on':
                    it = iter(get_sample(events[-1].note, events[-1].velocity) * ramp(0, 1, fade, True))
                elif events[-1].type == 'note_off':
                    yield from ramp(1, 0, fade) * it
                    return
            try:
                yield next(it)
            except StopIteration:
                return
        yield from it
    return instrument


@stream
def soundfont(event_stream, preset=0, chunk_size=1024, path="/usr/share/sounds/sf2/default-GM.sf2"):
    try:
        import fluidsynth
    except ImportError as exc:
        raise ImportError(f"Missing optional dependency '{exc.name}'. Install via `python -m pip install {exc.name}`.")

    # NOTE: Currently, this sets up the synth when the stream starts.
    # This might(?) be slow, especially for short cycled streams, but it guarantees fresh synth state upon replay.
    # (If you don't want a fresh synth state, cycle `event_stream` rather than this stream.)
    fs = fluidsynth.Synth()
    sfid = fs.sfload(path)
    fs.program_select(0, sfid, 0, preset)

    for chunk in event_stream.chunk(chunk_size):
        for events in chunk:
            for event in events:
                channel = getattr(event, "channel", 0)
                if event.type == 'note_on':
                    fs.noteon(channel, int(event.note), event.velocity)
                elif event.type == 'note_off':
                    fs.noteoff(channel, int(event.note))
                elif event.type == 'control_change':
                    fs.cc(channel, event.control, event.value)
                elif event.type == 'program_change':
                    fs.program_change(channel, event.program)
        yield from map(frame, fs.get_samples(chunk_size).reshape((-1, 2)) / (2**15-1))

    fs.delete()
