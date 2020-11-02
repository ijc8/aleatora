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

def fm_pulse(freq, duty):
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



# Amazing:
# play(resample(basic_sequencer(arp(C('C7', oct=5, inv=1)), bpm=350), osc(0.1)/2 + 1))

# Hm.
# I guess 'mixing' two event streams should work like merging two sorted lists.
# That is, the resulting event stream should still be in chronological order.



# play(resample(cycle(m), osc(5)/10 + 2))
# play(basic_sequencer(arp(c), bpm=10))
# play(basic_sequencer(arp(c), bpm=20))
# play(basic_sequencer(arp(c), bpm=20) + basic_sequencer(arp(c), bpm=30))
# play(resample(basic_sequencer(arp(C('C7', oct=5, inv=1)), bpm=10), osc(0.1)/10 + 1)/2)

# addplay(resample(basic_sequencer(arp(C('C7', oct=5, inv=1)), bpm=350), osc(0.1)/2 + 1)/2)

# 10/29
shaker = cycle(fit(rand * adsr(0.05, 0.05, 0.2, 0.2, 0.01), 60 / (120 * 2)))
play(shaker)

phrase1 = [(60, 1/16), (0, 2/16), (60, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (59, 1/16), (0, 1/16)]

phrase2 = [(60, 1/16), (0, 2/16), (60, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (57, 1/16), (55, 1/16), (53, 1/16), (55, 1/16), (58, 1/16), (0, 2/16)]

riff = basic_sequencer(cycle(list_to_stream(phrase1 + phrase2)), bpm=120)
play(riff)

riff = cycle(freeze(basic_sequencer(list_to_stream(phrase1 + phrase2), bpm=120)))
# riff = freeze(basic_sequencer(list_to_stream(phrase1 + phrase2), bpm=120))
# Frozen streams should implement __len__.
play(riff)

import filters
play(filters.bpf(riff, 650 * osc(0.25) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(1) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(2) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(4) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(8) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(16) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(128) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(512) + 700, 0.7))
play(filters.bpf(riff, 650 * osc(2048) + 700, 0.7))

play(filters.bpf(shaker + riff, 650 * osc(0.25) + 700, 2))
play(filters.bpf(shaker + riff, 650 * osc(1) + 700, 2))
play(filters.bpf(shaker + riff, 650 * osc(2) + 700, 2))
play(filters.bpf(shaker + riff, 650 * osc(4) + 700, 2))
play(filters.bpf(shaker + riff, 650 * osc(8) + 700, 2))  # <-- !
play(filters.bpf(shaker + riff, 650 * osc(16) + 700, 2))

play(filters.bpf((shaker + riff)[:8.0], 650 * osc(8) + 700, 1.7))
save(filters.bpf((shaker + riff)[:8.0], 650 * osc(8) + 700, 1.7)/10, 'funky.wav', verbose=True)

play(osc(440)[:1.0])
save(osc(440)[:1.0], 'test.wav')


from core import *
from audio import *
from chord import *

play(basic_sequencer(list_to_stream([(60, 0.25)])))

print(C('C'))

def transpose(pc, interval):
    index = PITCH_CLASSES.index(PITCH_CLASS_ALIASES.get(pc, pc))
    index = (index + interval) % len(PITCH_CLASSES)
    return PITCH_CLASSES[index]

def relative_minor(pc):
    return transpose(pc, 9).lower()

notes = []
chord = 'C'
for i in range(12):
    for root in (chord, relative_minor(chord)):
        for oct in (3, 4, 5, 6):
            notes += C(root, oct=oct).notes
    chord = transpose(chord, 5)

arps = freeze(basic_sequencer((list_to_stream(notes)).map(lambda p: (p, 1/16)), bpm=120))

bass = basic_sequencer(list_to_stream([(36, 10)]))
noise = rand * (count()[:10.0]/441000 >> const(1))
play(cycle(arps)/2 + bass/2)


from core import *
from prof import profile

profile.dump()
profile.reset()

_ = list(profile("osc", osc(440))[:5.0])

_ = list(profile("mix", profile("osc 1", osc(440)) + profile("osc 2", osc(660)))[:5.0])

_ = list(profile("mix", profile("osc 1", osc(440)) + profile("osc 2", osc(660)) + profile("osc 3", osc(880)))[:5.0])

_ = list(profile("mix", profile("osc 1", osc(440)) + profile("osc 2", osc(660)) + profile("osc 3", osc(880)) + profile("osc 4", osc(1100)))[:5.0])

_ = list(profile("mix", osc(440) + osc(660) + osc(880) + osc(1100))[:5.0])

_ = list(profile("zero", silence)[:10.0])

# Notes:
# - Things take up more time/budget when played live.
#   (Doesn't look like it matters if sounddevice is merely playing silence, though.)
# - One osc takes about 4% of budget.
#   This suggests a max of 25 simultaneous oscillators for real-time playback.
#   (Less than that in reality due to overhead of combining operations)
# - ProfileStream itself has high overhead, which makes it harder to estimate container performance.
#   For example, mix with four oscillators appears to take 50% of budget (including children)
#   when the osc's are wrapped with ProfileStream, but it only takes 15% of the budget with unwrapped osc's.
#   This suggests each ProfileStream consumes (50-15)/4 = about 9% of the budget!
# - Also, this implies mix has surprisingly little cost... or that the timing operations are slow.
# - Bizarrely, silence has a practically identical profiling result to osc.
#   This suggests either the stream call overhead or the timing operations far outweigh the actual computation.

# Remove the proc timer and now this looks *way* faster. Phew.
# Previously saw > 4% for osc, now seeing < 1%.
# Seeing more meaningful difference between osc and silence. (~1% vs. ~.65%)
# mix w and w/o child container is closer now: 17% w/, 10.45% w/o.
# Suggests overhead of (17-10.45)/4 = 1.6375% for each ProfileStream.

# Got overhead down to 1.3125% with small optimizations.

# Got down to 0.7275% by avoiding lookups in ProfileStream.
# 0.645% by sticking self.entry in a local.
# Considering silence itself only takes around 0.55% of the budget, I don't think I'll get the overhead much lower than that.

# Refactored: profile changed from function to class.
# Moved ProfileStream.{data, reset, dump} to profile.

# (Unsurprisingly, looks like performance numbers are much worse in CPython.)

from core import *
from audio import *
import wav
import random

def branch(choices, default=empty):
    # choices is list [(weight, stream)]
    def closure():
        x = random.random()
        acc = 0
        for weight, stream in choices:
            acc += weight
            if acc >= x:
                return stream()
        return default()
    return closure

def flip(a, b):
    return branch([(0.5, a), (0.5, b)])

start = list_to_stream(wav.load_mono("/home/ian/code/aleatora/samples/start.wav"))
a = list_to_stream(wav.load_mono("/home/ian/code/aleatora/samples/a.wav"))
b = list_to_stream(wav.load_mono("/home/ian/code/aleatora/samples/b.wav"))
c = list_to_stream(wav.load_mono("/home/ian/code/aleatora/samples/c.wav"))
d = list_to_stream(wav.load_mono("/home/ian/code/aleatora/samples/d.wav"))

graph = start >> flip(
    a >> flip(b >> (lambda: graph()), lambda: graph()),
    c >> flip(d >> (lambda: graph()), lambda: graph())
)


play()
play((graph + graph + graph) / 2)
play(graph, resample(graph, const(0.95)))
addplay(graph)

def pan(stream, pos):
    return stream.map(lambda x: (x * (1 - pos), x * pos))

# This would be more convenient, but unfortunately numpy is incredibly slow
# (at least compared to PyPy's built-in operations) when used for many tiny computations.
# Therefore, I think the right solution will be a kind of specialized ZipStream that overrides the math operators.
# (StereoStream? MultiStream?)
def nppan(stream, pos):
    return stream.map(lambda x: np.array([x * (1 - pos), x * pos]))

def modpan(stream, pos_stream):
    return ZipStream((stream, pos_stream)).map(lambda p: (p[0] * (1 - p[1]), p[0] * p[1]))

play(modpan(graph, (osc(0.1) + 1)/2))


tree = start >> flip(
    a >> flip(b, empty),
    c >> flip(d, empty)
)

graph = tree >> (lambda: ((graph + graph)/2)())
wav.save(graph[:20.0], "graph.wav", verbose=True)

def stereo_add(self, other):
    if isinstance(other, Stream):
        # assumes self and other return tuples representing multiple channels.
        return ZipStream((self, other)).map(lambda p: (p[0][0] + p[1][0], p[0][1] + p[1][1]))
    else:
        return self.map(lambda p: (p[0] + other, p[1] + other))

play()
# play(stereo_add(pan(osc(440)/2, 0.2), pan(osc(660)/2, 1.0)))

# hm. can we get a clever way to cast a Stream to a StereoStream?
# otherwise, we're paying overhead simply for the syntactic sugar of __add__.
class StereoStream(Stream):
    def __init__(self, stream):
        self.stream = stream

    def __call__(self):
        result = self.stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        return (value, MapStream(next_stream, self.fn))

    __add__ = stereo_add

# aha! I think the right approach is NOT to make a new kind of stream, but to make a new kind of tuple.
# then the existing operators will continue to work.

play()
play(graph)

# First attempt. Initial panning: 0.5; children panning: random.
def layer(pos):
    return pan(tree, pos) >> (lambda: stereo_add(layer(pos), layer(random.random()))())

def normalize(stream):
    # Requires evaluating the whole stream to determine the max volume.
    print('Rendering...')
    t = time.time()
    l = np.array(list(stream))
    print('Done in', time.time() - t)
    peak = np.max(np.abs(l))
    return list_to_stream(l / peak)

play(layer(0.5))
wav.save(normalize(layer(0.5)[:45.0]), "layers2.wav", verbose=True)

profile.dump()
profile.reset()

# Bizarre. graph appears extremely light (.47%), but graph + graph takes 52.71%!
_ = list(profile("graph", graph + graph)[:10.0])
_ = list(profile("pan", pan(silence, 0.5))[:10.0])
_ = list(profile("pansum", ZipStream((pan(silence, 0.5), pan(silence, 0.5))).map(lambda p: (p[0][0] + p[1][0], p[0][1] + p[1][1])))[:10.0])
_ = list(profile("pansum2", ZipStream((nppan(silence, 0.5), nppan(silence, 0.5))).map(lambda p: (p[0][0] + p[1][0], p[0][1] + p[1][1])))[:10.0])
_ = list(profile("pansum3", nppan(silence, 0.5) + nppan(silence, 0.5))[:10.0])

# Similarly: a is cheap, b is cheap, osc(X) + osc(Y) is cheap, and yet a + b is incredibly expensive??
_ = list(profile("a", a)[:10.0])
_ = list(profile("b", b)[:10.0])
_ = list(profile("sum", a + b)[:10.0])
_ = list(profile("sum2", osc(440) + osc(660))[:10.0])

# Figured it out. They were yielding length-1 numpy arrays because I used wav.load instead of wav.load_mono.
# Worth noting that these are still yielding numpy numeric types (numpy.float64), which has seems like an issue for performance.