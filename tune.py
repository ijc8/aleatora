from core import *
import math


class Chord:
    def __init__(self, notes, name='unknown'):
        self.name = name
        self.notes = sorted(notes)

CHORD_ALIASES = {
    'maj': '',
    'min': 'm',
    'min7': 'm7',
    'halfdim7': 'm7b5',
}

# TODO: support extensions and alterations
CHORD_TYPES = {
    '': (0, 4, 7),
    'm': (0, 3, 7),
    'dim': (0, 3, 6),
    '7': (0, 4, 7, 10),
    'maj7': (0, 4, 7, 11),
    'm7': (0, 3, 7, 10),
    'm7b5': (0, 3, 6, 10),
    'dim7': (0, 3, 6, 9),
    '6': (0, 4, 7, 9),
    'm6': (0, 3, 7, 9),
    'sus4': (0, 5, 7),
    'sus2': (0, 2, 7),
    'sus2/4': (0, 2, 5, 7),
}

PITCH_CLASS_ALIASES = {
    'Ab': 'G#',
    'Bb': 'A#',
    'Db': 'C#',
    'Eb': 'D#',
    'Gb': 'F#',
}

PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def spn_to_pitch(cls, oct):
    "Convert Scientific Pitch Notation (pitch class + octave) to a numeric (MIDI) pitch."
    cls = PITCH_CLASS_ALIASES.get(cls, cls)
    return PITCH_CLASSES.index(cls) + (oct + 1) * 12


# TODO: more voicing options?
def C(name, inv=0, oct=4):
    root = name[0]
    assert(root.lower() in 'abcdefg')
    ctype = name[1:]
    if ctype and ctype[0] in '#b':
        root += ctype[0]
        ctype = ctype[1:]
    if root.islower():
        root = root.upper()
        ctype = 'min' + ctype
    ctype = CHORD_ALIASES.get(ctype, ctype)
    notes = CHORD_TYPES.get(ctype)
    if notes is None:
        raise ValueError(f'Unrecognized chord type: "{ctype}"')
    canonical_name = root + ctype
    inv = inv % len(notes)
    notes = notes[inv:] + notes[:inv]
    root_pitch = spn_to_pitch(root, oct)
    notes = [pitch + root_pitch for pitch in notes]
    return Chord(notes, name=canonical_name)

def alberti(chord):
    sequence = []
    for lower in chord.notes[:-1]:
        sequence.append(lower)
        sequence.append(chord.notes[-1])
    return cycle(list_to_stream(sequence)).map(lambda p: (p, 1/8))


# TODO: overlapping concat
# TODO: replace list_to_stream with to_stream (maybe a different name)
# perhaps streams made from lists (+ arrays, tuples, strings...) should be a new class for inspection

# Three questions, looking ahead: timelines, tempo contexts, and inter-tape synchronization.
# One important point about the stream abstraction:
# It's easy to embed other abstractions inside of it, in their own little worlds
# This is not true of, for instance, the audio graph abstraction.
# Imagine trying to implement lazy streams in MSP.
# (Technically possible with the WebAudio API due to the buffer-level access provided by workers.)

# main = fm_osc(glide(cycle(list_to_stream([100, 200, 300])), 1.0, 0.2))
from audio import *
from wav import save
# play(osc(440))
# save(osc(440)[:10.0], 'osc.wav')
play(fm_osc(glide(cycle(list_to_stream([200, 300, 400])), 1.0, 0.2)))
# env = list_to_stream(list(adsr(0.8, 0.3, 1.5, 0.5, 0.5))[::-1])

play(silence)
play(osc(440))
# play(basic_sequencer(cycle(list_to_stream([(60, 1/4), (67, 1/8), (69, 1/8)])), bpm=120))
# save(basic_sequencer(alberti(C('C', oct=3)), bpm=240)[:10.0], 'alberti.wav')

def pulse(freq, duty):
    return count().map(lambda t: int((t * freq/SAMPLE_RATE % 1) < duty) * 2 - 1)

list(scan(count(), lambda x, y: x+y, 0)[:5])

# TODO: evaluate performance compared to custom definition above.
# def fm_osc(freq_stream):
#     return scan(freq_stream, lambda x, y: x+y, 0).map(lambda phase: math.sin(2*math.pi*phase/SAMPLE_RATE))

play(fm_osc(osc(200) * 100 + 440))
play(osc(440))

play(tri(440) / 10)
play(sqr(440) / 10)

play(silence)
play(pulse(440, 0.25) / 10)
play(fm_pulse(tri(0.1) * 100 + 300, 0.25) / 30)

play(cycle(rand / 20 * adsr(0.05, 0.05, 0.2, 0.2, 0.01)))

# Oof. Even this convolve([1], ...) is behaving poorly, which suggests that filters may be problematic...
# Maybe for now I should try to avoid getting too much into fancy DSP and stick with the tape stuff.

# TODO: this, but without resetting the playhead every time.
total = silence
def play_layer(s):
    global total
    total += s
    play(total)

# This version does the same thing without resetting
# the playhead position on what's already playing.
import audio
def addplay(layer):
    play(audio.play_callback.samples.rest + layer)

# play(resample(riff, osc(1)/2 + 1))
# play(resample(rand, osc(1)/2 + 1))
