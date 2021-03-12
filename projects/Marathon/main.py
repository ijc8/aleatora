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

freqs = [215, 430*2/3, 430*2/3*5/4, 430]


octave = [-12, 0, 2, 4, 7, 9, 12]

def notes():
    note = random.choice(octave) + 60
    return (mido.Message(type='note_on', note=note), const(None)[:0.3] >> cons(mido.Message(type='note_off', note=note), notes))

from rhythm import *
# hhc = to_stream(wav.load_mono('samples/hhc.wav'))
# play(cycle(freeze(beat('xxx.xx.x.xx.', hhc, rpm=30))), cycle(freeze(beat('xxx.xx.x.xx..', hhc, rpm=30*12/13))))

# play(cycle(beat('xxx.xx.x.xx.', pluck(m2f(36), s=0.6), rpm=30)) + cycle(beat('xxx.xx.x.xx..', pluck(m2f(72), s=0.9), rpm=30*12/13)))
# play(cycle(freeze(beat('xxx.xx.x.xx.', pluck(m2f(36), s=0.6), rpm=30))) + cycle(freeze(beat('xxx.xx.x.xx..', pluck(m2f(72), s=0.9), rpm=30*12/13))))
# play()

x = 72
oh_yeah = cycle(beat('xxx.xx.x.xx.', w(lambda: pluck(m2f(36), s=0.6)), rpm=30)) + cycle(beat('xxx.xx.x.xx..', w(lambda: pluck(m2f(x), s=0.9)), rpm=30*12/13))

_ = lazy_concat(cycle(to_stream([72, 70, 69, 67])).map(
    lambda x: beat('xxx.xx.x.xx.'*12, w(lambda: pluck(m2f(36), s=0.6)), rpm=2) + beat('xxx.xx.x.xx..'*11 + '.', w(lambda: pluck(m2f(x), s=0.9)), rpm=2)))

# a = cycle(freeze(lazy_concat(to_stream([72, 70, 69, 67]).map(
#     lambda x: beat('xxx.xx.x.xx.'*12, w(lambda: pluck(m2f(36), s=0.55)), rpm=2) + beat('xxx.xx.x.xx..'*11 + '.', w(lambda: pluck(m2f(x), s=0.9)), rpm=2)))))
# b = filters.bpf(a, const(1000) + osc(3) * 800, 2)
# b = filters.bpf(a, const(1000) + osc(10) * 200, 10)

a = cycle(frozen('a2', lazy_concat(to_stream([72, 70, 69, 67]).map(
    lambda x: beat('xxx.xx.x.xx.'*12, w(lambda: pluck(m2f(36), s=0.55)), rpm=2.5) + beat('xxx.xx.x.xx..'*11 + '.', w(lambda: pluck(m2f(x), s=0.9)), rpm=2.5)))))
import filters
b = filters.bpf(a, const(1000) + osc(10) * 200, 5)

from speech import *

def repeat(stream, n):
    return ConcatStream([stream] * n)

def stutter(stream, size, repeats):
    return bind(repeat(stream[:size], repeats), lambda rest: stutter(rest, size, repeats) if rest else empty)


c = frozen('marathon', speech("Marathon!"))
d = frozen('victory', speech("Victory!"))
s2 = frozen('messenger', speech("Messenger"))
s3 = frozen('name', speech("Pheidippides"))
s4 = frozen('text', speech("gotta go gotta run gotta make it in time"))
e = stutter(c, 0.1, 18)
f = stutter(d, 0.05, 3)
p2 = stutter(resample(cycle(s2), const(0.5)), 0.15, 2)
p3 = stutter(resample(cycle(d), const(1.2)), 0.075, 3)
p4 = resample(cycle(s4), const(1.2))

bass = aa_tri(m2f(36)) # aa_saw(m2f(36))/8