from next import *
import math

# TODO: define this in terms of a fold.
# TODO: expose the freq_stream for inspection.
#   This will probably require making this a class and rethinking how graph generation works.
@stream("fm_osc")
def fm_osc(freq_stream, phase=0):
    def closure():
        result = freq_stream()
        if isinstance(result, Return):
            return result
        freq, next_stream = result
        return (math.sin(phase), fm_osc(next_stream, phase + 2*math.pi*freq/SAMPLE_RATE))
    return closure

# main = fm_osc(count() / 480 % 800)

def glide(freq_stream, hold_time, transition_time, start_freq=0):
    def closure():
        result = freq_stream()
        if isinstance(result, Return):
            return result
        freq, next_stream = result
        tt = convert_time(transition_time)
        transition = (count()[:tt] / tt) * (freq - start_freq) + start_freq
        hold = repeat(freq)[:hold_time]
        return (transition >> hold >> glide(next_stream, hold_time, transition_time, start_freq=freq))()
    return closure


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

@stream("lazy_concat")
def lazy_concat(stream_of_streams):
    def closure():
        result = stream_of_streams()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (value >> lazy_concat(next_stream))()
    return closure

def basic_sequencer(note_stream, bpm=80):
    # Assumes quarters have the beat.
    return lazy_concat(note_stream.map(lambda n: sqr(m2f(n[0])) * basic_envelope(60.0 / bpm * n[1] * 4)))

def adsr(attack, decay, sustain_time, sustain_level, release):
    attack, decay, sustain_time, release = map(convert_time, (attack, decay, sustain_time, release))
    return list_to_stream(np.concatenate((np.linspace(0, 1, attack, endpoint=False),
                                          np.linspace(1, sustain_level, decay, endpoint=False),
                                          np.ones(sustain_time) * sustain_level,
                                          np.linspace(0, sustain_level, release, endpoint=False)[::-1])))


# This function produces a stream of exactly length, by trimming or padding as needed.
# Hypothetically, might also want a function that strictly pads (like str.ljust()).
# Could return another object with length metadata, or make this a method and override it for some kinds of streams.
def fit(stream, length):
    return (stream >> silence)[:length]

# TODO: overlapping concat
# TODO: replace list_to_stream with to_stream (maybe a different name)
# perhaps streams made from lists (+ arrays, tuples, strings...) should be a new class for inspection

# main = fm_osc(glide(cycle(list_to_stream([100, 200, 300])), 1.0, 0.2))
from audio import *
from wav import save
# play(osc(440))
# save(osc(440)[:10.0], 'osc.wav')
play(fm_osc(glide(cycle(list_to_stream([200, 300, 400])), 1.0, 0.2)))
env = adsr(0.2, 0.3, 0.5, 0.5, 0.5)
play(fm_osc(osc(100) * 440 * env + 440) * env)
# play(silence)
# play(basic_sequencer(cycle(list_to_stream([(60, 1/4), (67, 1/8), (69, 1/8)])), bpm=120))
# play(basic_sequencer(alberti(C('C', oct=3)), bpm=60))
# save(basic_sequencer(alberti(C('C', oct=3)), bpm=240)[:10.0], 'alberti.wav')

import random
rand = Stream(lambda: (random.random(), rand))
play(rand)