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


import time


class ProfileStream(Stream):
    data = {}

    def __init__(self, key, stream):
        if key not in ProfileStream.data:
            ProfileStream.data[key] = {
                'calls': 0,
                'ends': 0,
                'wall': 0.0,
                'proc': 0.0,
            }
        self.key = key
        self.stream = stream

    def __call__(self):
        wall_start = time.perf_counter()
        proc_start = time.process_time()
        result = self.stream()
        wall_end = time.perf_counter()
        proc_end = time.process_time()

        entry = ProfileStream.data[self.key]
        entry['calls'] += 1
        entry['wall'] += wall_end - wall_start
        entry['proc'] += proc_end - proc_start

        if isinstance(result, Return):
            entry['ends'] += 1
            return result
        x, next_stream = result
        return (x, ProfileStream(self.key, next_stream))

    @staticmethod
    def reset():
        ProfileStream.data.clear()

    @staticmethod
    def dump():
        print(f"Real-time budget: {1e6/core.SAMPLE_RATE:.3f}us per sample")
        for key, entry in ProfileStream.data.items():
            wall_avg = entry['wall'] / entry['calls']
            proc_avg = entry['proc'] / entry['calls']
            print(f"{key}: {entry['calls']} CALLS ({entry['ends']} ENDINGS)")
            print(f"{' ' * len(key)}  PROC: {proc_avg*1e6:.3f}us avg | {entry['proc']:.3f}s total")
            print(f"{' ' * len(key)}  WALL: {wall_avg*1e6:.3f}us avg | {entry['wall']:.3f}s total | {wall_avg*core.SAMPLE_RATE*100:.2f}% of budget")


ProfileStream.reset()
ProfileStream.dump()

_ = list(ProfileStream("osc", osc(440))[:5.0])

_ = list(ProfileStream("mix", ProfileStream("osc 1", osc(440)) + ProfileStream("osc 2", osc(660)))[:5.0])

_ = list(ProfileStream("mix", ProfileStream("osc 1", osc(440)) + ProfileStream("osc 2", osc(660)) + ProfileStream("osc 3", osc(880)))[:5.0])

_ = list(ProfileStream("mix", ProfileStream("osc 1", osc(440)) + ProfileStream("osc 2", osc(660)) + ProfileStream("osc 3", osc(880)) + ProfileStream("osc 4", osc(1100)))[:5.0])

_ = list(ProfileStream("mix", osc(440) + osc(660) + osc(880) + osc(1100))[:5.0])

_ = list(ProfileStream("zero", silence)[:5.0])

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