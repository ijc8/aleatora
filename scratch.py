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