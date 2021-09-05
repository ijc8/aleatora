# Emulation of James Andy Moorer's THX Deep Note.
# Port of Ge Wang's ChucK version (https://github.com/ccrma/chuck/blob/main/examples/deep/thx.ck).
import random

from aleatora import *

WAVER = 12.5
SWEEP = 6.0
HOLD = 5.5
DECAY = 6.0

targets = [37.5 * x for x, n in [(1, 3), (2, 3), (4, 4), (80, 4), (16, 3), (24, 4), (32, 4), (40, 2), (48, 3)] for _ in range(n)]

@stream
def freq_contour(target):
    initial_freq = random.uniform(160, 360)
    waver_rate = random.uniform(0.1, 1)
    for progress in ramp(0, 1, WAVER):
        freq = initial_freq * (1 + (1.25 - progress) * 0.5 * math.sin(progress * WAVER * waver_rate))
        yield freq
    yield from ramp(freq, target, SWEEP, hold=True)[:SWEEP + HOLD + DECAY]

def make_voice(target):
    env = ramp(0, 1, WAVER)**3 >> const(1)[:SWEEP + HOLD] >> ramp(1, 0, DECAY)
    return pan(saw(freq_contour(target)) * env, random.random())

deep_note = sum(make_voice(target) for target in targets) / len(targets)
wav.save(deep_note, "deep_note.wav")
