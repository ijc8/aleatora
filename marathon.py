from core import *
from audio import *

def two_point_recurrence(y, c, d, g, h):
    def f(t):
        value = y[t % len(y)]
        y[t % len(y)] = c*y[(t-g) % len(y)] + d*y[(t-h) % len(y)]
        return value
    return count().map(f)

randbits = NamedStream("randbits", lambda: (random.getrandbits(1), randbits))

def pluck(f, s=1):
    # TODO: better tuning. all-pass filter, or resample, or something.
    p = int(SAMPLE_RATE / f)
    # We memoize because two_point_recurrence mutates its input.
    return memoize(two_point_recurrence(list((randbits*2 + -1)[:p]), 1-1/(2*s), 1/(2*s), p, p+1))

play(cycle((pluck(440) + pluck(660) + pluck(880))[:0.5]))
play()
