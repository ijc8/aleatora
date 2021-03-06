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
    p = int(SAMPLE_RATE / f - 1/2)
    # We memoize because two_point_recurrence mutates its input.
    return memoize(two_point_recurrence(list((randbits*2 + -1)[:p]), 1-1/(2*s), 1/(2*s), p, p+1))

one = cycle((pluck(440) + pluck(660) + pluck(880))[:0.5])
two = cycle(pluck(220)[:0.75])
# ratatat, ratatat, ratatat, ratatat, ah... (one pitch per group)

def mono_guitar(stream, s=1, length=3.0, persist=False):
    assert(persist == False)
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if event and event.type == 'note_on':
            return (event.velocity / 127 * pluck(m2f(event.note), s=s)[:length])()
        return (0, mono_guitar(next_stream))
    return closure

# from midi import *
# p = mido.open_input(mido.get_input_names()[1])

@stream(instrument=True)
def guitar(event_stream):
    return poly(mono_guitar)(event_stream)
# play(poly(lambda *args, **kwargs: mono_guitar(*args, **kwargs, s=0.7))(event_stream(p)))
