from core import *
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

def sqr_inst(pitch, duration):
    return sqr(m2f(pitch)) * basic_envelope(60.0 / bpm * duration * 4)

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
env = adsr(0.8, 0.3, 1.5, 0.5, 0.5)
salt = fm_osc(fm_osc(8 * env) * 100 * env + 440) * env
play(salt)
play(silence)
play(osc(440))
# play(basic_sequencer(cycle(list_to_stream([(60, 1/4), (67, 1/8), (69, 1/8)])), bpm=120))
play(basic_sequencer(alberti(C('D6', oct=3)), bpm=60) / 30)
play(basic_sequencer(cycle(list_to_stream([(60, 0.25), (60, 0.25), (0, 0.25), (58, 0.25)])), bpm=300)/40)
phrase1 = [(60, 1/16), (0, 2/16), (60, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (59, 1/16), (0, 1/16)]
phrase2 = [(60, 1/16), (0, 2/16), (60, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (57, 1/16), (55, 1/16), (53, 1/16), (55, 1/16), (58, 1/16), (0, 2/16)]
play(basic_sequencer(cycle(list_to_stream(phrase1 + phrase2)), bpm=120)/40)
# save(basic_sequencer(alberti(C('C', oct=3)), bpm=240)[:10.0], 'alberti.wav')

def pulse(freq, duty):
    return count().map(lambda t: int((t * freq/SAMPLE_RATE % 1) < duty) * 2 - 1)

@stream("fm_osc")
def fm_osc(freq_stream, phase=0):
    def closure():
        result = freq_stream()
        if isinstance(result, Return):
            return result
        freq, next_stream = result
        return (math.sin(phase), fm_osc(next_stream, phase + 2*math.pi*freq/SAMPLE_RATE))
    return closure

# foldr, not foldl.
@stream("fold")
def fold(stream, f, acc):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return acc
        x, next_stream = result
        return f(x, fold(next_stream, f, acc))
    return closure

# scanl, not scanr
@stream("scan")
def scan(stream, f, acc):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return acc
        x, next_stream = result
        next_acc = f(x, acc)
        return (acc, scan(next_stream, f, next_acc))
    return closure

list(scan(count(), lambda x, y: x+y, 0)[:5])

# TODO: evaluate performance compared to custom definition above.
# def fm_osc(freq_stream):
#     return scan(freq_stream, lambda x, y: x+y, 0).map(lambda phase: math.sin(2*math.pi*phase/SAMPLE_RATE))

play(fm_osc(osc(200) * 100 + 440))
play(osc(440))

def pulse(freq, duty):
    return count().map(lambda t: int((t * freq/SAMPLE_RATE % 1) < duty) * 2 - 1)

def fm_pulse(freq_stream, duty):
    return scan(freq_stream, lambda x, y: x+y, 0).map(lambda phase: int(((phase/SAMPLE_RATE) % 1) < duty) * 2 - 1)

def tri(freq):
    return count().map(lambda t: abs((t * freq/SAMPLE_RATE % 1) - 0.5) * 4 - 1)

play(tri(440) / 10)
play(sqr(440) / 10)

play(silence)
play(pulse(440, 0.25) / 10)
play(fm_pulse(tri(0.1) * 100 + 300, 0.25) / 30)

import random
rand = Stream(lambda: (random.random(), rand))
play(cycle(rand / 20 * adsr(0.05, 0.05, 0.2, 0.2, 0.01)))

shaker = cycle(fit(rand / 20 * adsr(0.05, 0.05, 0.2, 0.2, 0.01), 60 / (120 * 2)))
riff = basic_sequencer(cycle(list_to_stream(phrase1 + phrase2)), bpm=120)
play(shaker + riff)
play(shaker)
play(riff)
import bass
# Oof. Even this trivial convolve is behaving poorly, which suggests that filters may be problematic...
play(bass.convolve(shaker, np.array([1])))
# Maybe for now I should try to avoid getting too much into fancy DSP and stick with the tape stuff.

# TODO: this, but without resetting the playhead every time.
total = silence
def play_layer(s):
    global total
    total += s
    play(total)

play_layer(shaker)
play_layer(riff)
play(silence)

# Stream-controlled resampler. Think varispeed.
@stream("resample")
def resample(stream, advance_stream, pos=0, sample=None, next_sample=0):
    def closure():
        nonlocal stream, pos, sample, next_sample
        result = advance_stream()
        if isinstance(result, Return):
            return result
        advance, next_advance_stream = result
        pos += advance
        while pos >= 0:
            result = stream()
            if isinstance(result, Return):
                return result
            sample = next_sample
            next_sample, stream = result
            pos -= 1
        interpolated = (next_sample - sample) * (pos + 1) + sample
        return (interpolated, resample(stream, next_advance_stream, pos, sample, next_sample))
    return closure

def freeze(stream):
    print('Rendering...')
    t = time.time()
    r = list_to_stream(list(stream))
    print('Done in', time.time() - t)
    return r

play(osc(440))
play(silence)
# save(resample(riff, osc(1)/2 + 1)[:10.0], 'riff.wav')
# f = freeze(resample(riff, osc(1)/2 + 1)[:10.0])
# play(f)
play(resample(riff, osc(1) + 2))
play(resample(riff, repeat(1.2) + tri(5)))
play(resample(osc(440), repeat(1)))
# play(resample(riff, osc(1)/2 + 1))
# play(resample(rand, osc(1)/2 + 1))
