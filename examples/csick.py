from aleatora import *

c = chord((60, 64, 67, 72))
m = freeze(basic_sequencer(c.arp()[:4], bpm=20)).cycle()

# (time, modulation frequency)
freq_points = [
    (0.0,  0.0),
    (15.0, 0.0),
    (20.0, 0.25),
    (25.0, 0.5),
    (30.0, 1.0),
    (35.0, 2.0),
    (40.0, 4.0),
    (45.0, 8.0),
    (50.0, 16.0),
    (55.0, 32.0),
    (56.0, 0.0),
    (60.0, 0.0)
]

# (time, modulation depth)
depth_points = [
    (0.0,  0.0),
    (15.0, 0.0),
    (20.0, 0.01),
    (25.0, 0.1),
    (30.0, 0.2),
    (35.0, 0.3),
    (40.0, 0.4),
    (45.0, 0.5),
    (50.0, 1.0),
    (55.0, 2.0),
    (56.0, 0.0),
    (60.0, 0.0)
]

mod_freq = freeze(interp(freq_points))
mod_depth = freeze(interp(depth_points))
low_rate = 1 + osc(mod_freq) * mod_depth
mid_rate = 2 + osc(mod_freq) * mod_depth
high_rate = 3 + osc(mod_freq) * mod_depth

low = m.resample(low_rate)
mid = silence[:5.0] >> (m.resample(mid_rate[5.0:]) * basic_envelope(58.0 - 5.0))
high = silence[:10.0] >> (m.resample(high_rate[10.0:]) * basic_envelope(56.0 - 10.0))

composition = (low + mid + high)/3
wav.save(composition, "csick.wav", verbose=True)
