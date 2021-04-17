from core import *


class Chord:
    def __init__(self, notes, name='unknown'):
        self.name = name
        self.notes = sorted(notes)


CHORD_ALIASES = {
    'maj': '',
    'min': 'm',
    'min7': 'm7',
    'M7': 'maj7',
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
    notes = notes[inv:] + tuple(pitch + 12 for pitch in notes[:inv])
    root_pitch = spn_to_pitch(root, oct)
    notes = [pitch + root_pitch for pitch in notes]
    return Chord(notes, name=canonical_name)


# Unlike the lower-level synthesis streams, these streams do not yield samples.
# Instead, they yield notes - tuples of (pitch, duration in beats).
def arp(chord, dur=1/8):
    return cycle(list_to_stream(chord.notes)).map(lambda p: (p, dur))


def alberti(chord, dur=1/8):
    sequence = []
    for lower in chord.notes[:-1]:
        sequence.append(lower)
        sequence.append(chord.notes[-1])
    return cycle(list_to_stream(sequence)).map(lambda p: (p, dur))