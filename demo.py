from core import *
from audio import *

## Basics
play(silence)

play(osc(440))
play(osc(440)[:1.0])
play(osc(440)/2)

play(osc(440)[:1.0] >> osc(660)[:1.0])
play((osc(440) + osc(660))/2)

play(cycle(osc(440)[:1.0] >> osc(660)[:1.0]))

play(rand)

##
play(fm_osc(glide(cycle(list_to_stream([200, 300, 400])), 1.0, 0.2)))

env = adsr(0.8, 0.3, 1.5, 0.5, 0.5)
woo = fm_osc(fm_osc(8 * env) * 100 * env + 440) * env
play(woo)

##
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

play(shaker + riff)

##
play(osc(440))

play(resample(osc(440), repeat(1)))
play(resample(osc(440), repeat(0.5)))
play(resample(osc(440), repeat(1.5)))

play(resample(osc(440), osc(1)/2 + 1))

# save(resample(riff, osc(1)/2 + 1)[:10.0], 'riff.wav')
# f = freeze(resample(riff, osc(1)/2 + 1)[:10.0])
# play(f)
play(resample(riff, osc(1)/4 + 0.5))
play(resample(riff, osc(1)/2 + 1))
play(resample(riff, osc(1)/2 + 2))
play(resample(riff, resample(rand, repeat(0.001)) + 1))



##
from phase import piano_phase
play(piano_phase)