import math

SAMPLE_RATE = 44100

def osc(freqs):
    phase = 0
    for freq in freqs:
        yield math.sin(phase)
        phase += 2*math.pi*freq/SAMPLE_RATE

def env(attack, sustain, decay):
    for i in range(attack):
        yield i/attack
    for i in range(sustain):
        yield 1
    for i in range(decay):
        yield 1-i/decay


def interesting():
    if random.random() > 0.5:
        yield 0
        while True:
            yield random.random()
    else:
        yield 0
        while True:
            yield -random.random()