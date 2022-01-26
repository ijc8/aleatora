from aleatora import *

## Basics
play(silence)

play(osc(440))
play(osc(440)[:1.0])
play(osc(440)/2)

play(osc(440)[:1.0] >> osc(660)[:1.0])
play((osc(440) + osc(660))/2)

play((osc(440)[:1.0] >> osc(660)[:1.0]).cycle())

play(rand)

##
play(osc(glide(Stream.cycle([200, 300, 400]), 1.0, 0.2))/10)

env = adsr(0.8, 0.3, 1.5, 0.5, 0.5)
woo = osc(osc(8 * env) * 100 * env + 440) * env
woo = freeze(woo)
play(woo/10)

##
shaker = fit(rand * adsr(0.05, 0.05, 0.2, 0.2, 0.01), 60 / (120 * 2)).cycle()
play(shaker/10)

phrase1 = [(60, 1/16), (0, 2/16), (60, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (59, 1/16), (0, 1/16)]

phrase2 = [(60, 1/16), (0, 2/16), (60, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (0, 2/16), (58, 1/16), (0, 2/16), (57, 1/16), (0, 1/16),
           (58, 1/16), (57, 1/16), (55, 1/16), (53, 1/16), (55, 1/16), (58, 1/16), (0, 2/16)]

riff = basic_sequencer(stream(phrase1 + phrase2), bpm=120).freeze().cycle()
play(riff/10)

play((shaker + riff)/20)

##
volume(0.1)
play(osc(440))

play(osc(440).resample(1))
play(osc(440).resample(0.5))
play(osc(440).resample(1.5))

play(osc(440).resample(osc(1)/2 + 1))

play(riff.resample(osc(1)/4 + 0.5))
play(riff.resample(osc(1)/2 + 1))
play(riff.resample(osc(1)/2 + 2))
play(riff.resample(resample(rand, const(0.001)) + 1))
play()


##
from phase import piano_phase
play(piano_phase)
