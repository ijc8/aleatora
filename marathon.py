from core import *
from audio import *
from midi import *

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

# convenience function: lazify; ensure that a stream is recreated at play time.
# handy for livecoding (can affect a cycle by changing a variable/function live), and for streams that employ nondeterminism (like pluck with randbits) on creation.
def w(f):
    return Stream(lambda: f()())
x = 72
oh_yeah = cycle(beat('xxx.xx.x.xx.', w(lambda: pluck(m2f(36), s=0.6)), rpm=30)) + cycle(beat('xxx.xx.x.xx..', w(lambda: pluck(m2f(x), s=0.9)), rpm=30*12/13))

_ = lazy_concat(cycle(to_stream([72, 70, 69, 67])).map(
    lambda x: beat('xxx.xx.x.xx.'*12, w(lambda: pluck(m2f(36), s=0.6)), rpm=2) + beat('xxx.xx.x.xx..'*11 + '.', w(lambda: pluck(m2f(x), s=0.9)), rpm=2)))

a = cycle(freeze(lazy_concat(to_stream([72, 70, 69, 67]).map(
    lambda x: beat('xxx.xx.x.xx.'*12, w(lambda: pluck(m2f(36), s=0.55)), rpm=2) + beat('xxx.xx.x.xx..'*11 + '.', w(lambda: pluck(m2f(x), s=0.9)), rpm=2)))))
import filters
b = filters.bpf(a, const(1000) + osc(3) * 800, 2)
b = filters.bpf(a, const(1000) + osc(10) * 200, 10)

a = cycle(freeze(lazy_concat(to_stream([72, 70, 69, 67]).map(
    lambda x: beat('xxx.xx.x.xx.'*12, w(lambda: pluck(m2f(36), s=0.55)), rpm=2) + beat('xxx.xx.x.xx..'*11 + '.', w(lambda: pluck(m2f(x), s=0.9)), rpm=2)))))
import filters
b = filters.bpf(a, const(1000) + osc(10) * 200, 5)
from speech import *
c = speech("Marathon!")
d = speech("Victory!")
s2 = speech("Messenger")
s3 = speech("Pheidippides")
e = stutter(c, 0.1, 18)
f = stutter(d, 0.05, 3)
p2 = stutter(resample(cycle(s2), const(0.5)), 0.15, 2)
p3 = stutter(resample(cycle(d), const(1.2)), 0.075, 3)

bass = aa_tri(m2f(36)) # aa_saw(m2f(36))/8
# Note the distinction between stutter(cycle(list_stream)) and cycle(stutter(list_stream)).
play(b + p2 + p3 + stutter(cycle(c), 0.1, 18) + bass)
play()

# tomorrow, melody shorthands.
# F-E..., C..., Eb...

import cProfile as profile
profile.run('list(guitar(notes)[:10.0])', sort='cumtime')

from prof import profile
profile.reset()
_ = list(profile('0', guitar(notes))[:10.0])
profile.dump()

# Hmm. cProfile reported 15.067 seconds, but prof only 6.576.
# Are there really nearly 9 seconds overhead outside the stream itself?
# Not even counting playback?

play(guitar(notes))
play()

# Looking at profile...
# 14.454 total (for 10 seconds)
# This claims that an enormous amount of time (> 5 seconds) is spent just in Stream.__call__.
# which just has the one line `return self.fn()`.
# That much overhead?
# ncalls is 16085909/441000 = about 36.
# does that imply 36 streams are called upon per sample?
# that's crazy.

# Let's count.
# guitar is decorated with @stream. +1
# It returns poly, which returns a function decorated by @raw_stream. +1
# polyphonic_instrument calls the event_stream, which is a @raw_stream. +1
# polyphonic_instrument calls its voices. if these notes have length 3.0 and a new one starts every 0.3 seconds,
# this should saturate at all voices operating. so there should be 7 voices most of the time.
# each voice is a mono_guitar, which is not decorated, and mono_guitar pulls from undecorated substreams.
# however, once the note starts, mono_guitar is replaced with a pluck.
# pluck is also undecorated, but it returns memoize(two_point_recurrence)
# memoize is a raw_stream. +7
# two_point_recurrence is undecorated, but it returns count().map().
# count is a raw_stream. +7
# map returns a MapStream, which has its own separate __call__.

# by my count, there should be 17 calls to Stream.__call__... not 36.

# let's see.
# @raw_stream makes the function return a NamedStream.
# NamedStream does not replace Stream.__call__.
# @stream is trickier. it wraps the inner stream with namify().
# namify involves a wrapper(), which add its own layer of indirection,
# but it's also a @raw_stream, adding a Stream.__call__.
# NOTE: We could condense the wrapper and Stream layers of namify into one,
#       with a subclass that overrides Stream.__call__. (Like MapStream with an identity.)

# more clues; 7570881/441000 calls to the namify wrapper closure().
# that's 17 per sample! how could there be that many @streams involved??
# here's maybe the root of the mystery:
# 5146852/441001 for StreamIterator.__next__. that's 11.67 per sample.
# why so many? the list() on the outside can only be responsible for 1 per sample.

# let's see. 4701007/441001 for SliceStream.__call__. 10.66x
# there's the SliceStream on the outside, and one per pluck. that's 8.
# also, I forgot that the plucks are multiplied.
# that should add one, or in the unfortunate OOP case two, MapStreams per pluck.
# but that should not add to the Stream.__call__ count.

# why the extra StreamIterator.__next__?
# SliceStream uses iterators if there's a non-zero start or a non-1 step.
# wait, hold up. not true.
# it creates an iterator even if the step *is* 1, if there's a stop.
# TODO: Don't do that!
# so there should be one StreamIterator.__next__ per pluck.
# now we're up to 8, which is closer to the measured 11.67.
# zip() shouldn't take an extra value from the other iterators after an earlier one runs out...
# right?
# let's check.
# "The left-to-right evaluation order of the iterables is guaranteed" okay.
# I wonder if SliceStream should be taken apart into take, drop, and some kind of step.
# what is this step even going to be used for...?

# 1:1 calls to ConcatStream.__call__.
# I wonder why. Where is the concat in this construction?
# Ah, of course.
# This is not using event_stream; this is using notes().
# And notes() uses const, which is a raw_stream (+1),
# and it uses a SliceStream, and it uses a ConcatStream.
# Oh, dear. It uses cons, which would be perfectly acceptable
# if not for the awful fact
# that is is a @stream: so the whole rest of the stream gets wrapped.
# That means that after every note that plays,
# this accumulates an ADDITIONAL layer of indirection!
# So it gets slower and slower over time.
# Welp. I think this was the big mystery.

# Of course, cons should not keep this wrapper around.
# And the broader issue is this: is namify() misguided?
# Any stream could "bottom out" with a different stream;
# it is impossible to maintain identity without overhead, and,
# outside of profile() and StreamManager, it is undesirable.
# The trouble is, it would be nice to keep that inspection data around, at least until a real switch.
# Obviously, for cons, it is a bit silly: there's literally only one sample attributable to the cons.
# But what about others streams?
# For those that don't 'bottom-out' into something else, this adds only constant overhead.

# For cons, I suppose the solution is simple enough.
# Just use @raw_stream and remove the explicit wrapper.
# Then the return value will get wrapped in a NamedStream, but it won't cling to the stream forever.

# For others, maybe my old idea is a good one: don't namify.
# Just make a copy of the NamedStream (assuming the function creates a NamedStream) and change the attributes.

# Okay, enough talk, it's experiment time.

# Here's the first bit of output from the last run:
#          234938104 function calls (199378442 primitive calls) in 14.454 seconds

#    Ordered by: cumulative time

#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#         1    0.000    0.000   14.454   14.454 {built-in function exec}
#         1    0.029    0.029   14.454   14.454 <string>:1(<module>)
# 5146852/441001    1.268    0.000   14.424    0.000 core.py:33(__next__)
# 4701007/441001    2.882    0.000   14.296    0.000 core.py:356(__call__)
# 16085909/441000    5.069    0.000   13.780    0.000 core.py:148(__call__)
# 7570881/441000    0.290    0.000   13.668    0.000 core.py:96(closure)
#    441000    0.611    0.000   13.469    0.000 midi.py:64(closure)
# 7637988/3819006    0.405    0.000    8.919    0.000 core.py:294(__call__)
#   3814080    0.135    0.000    2.530    0.000 core.py:443(closure)
#   4700915    1.116    0.000    1.116    0.000 core.py:30(__iter__)
#  16081112    0.484    0.000    0.970    0.000 core.py:83(<lambda>)
# 440999/440966    0.036    0.000    0.842    0.000 core.py:221(__call__)
#   4701018    0.175    0.000    0.472    0.000 core.py:344(__init__)
#  16081112    0.250    0.000    0.359    0.000 core.py:396(__init__)

# Now I will make the proposed change to cons.
# And run again.

# Now we have:
#          185049925 function calls (163746245 primitive calls) in 13.468 seconds

#    Ordered by: cumulative time

#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#         1    0.000    0.000   13.468   13.468 {built-in function exec}
#         1    0.030    0.030   13.468   13.468 <string>:1(<module>)
# 5148364/441001    1.327    0.000   13.437    0.000 core.py:33(__next__)
# 4701763/441001    3.245    0.000   13.315    0.000 core.py:356(__call__)
# 8956784/441000    3.602    0.000   12.648    0.000 core.py:148(__call__)
#    441000    0.019    0.000   12.431    0.000 core.py:96(closure)
#    441000    0.596    0.000   12.211    0.000 midi.py:64(closure)
# 7639500/3819762    1.074    0.000   10.557    0.000 core.py:294(__call__)
#   3814080    0.143    0.000    2.864    0.000 core.py:443(closure)
#   4701671    1.111    0.000    1.111    0.000 core.py:30(__iter__)
# 440999/440966    0.032    0.000    0.820    0.000 core.py:221(__call__)
#   8951231    0.273    0.000    0.574    0.000 core.py:83(<lambda>)
#   4701774    0.188    0.000    0.504    0.000 core.py:344(__init__)

# Well, okay. That's 21% fewer function calls, but only 6.8% less time.

# Now let's try the change to SliceStream.
# For the moment, I'll keep everything the same, just avoid the iterator/for-loop shenanigans when step == 1.
# Okay. Let's go again.

# Remarkable.

#          161546500 function calls (144943607 primitive calls) in 7.879 seconds

#    Ordered by: cumulative time

#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#         1    0.000    0.000    7.879    7.879 {built-in function exec}
#         1    0.067    0.067    7.878    7.878 <string>:1(<module>)
# 446914/441001    0.019    0.000    7.811    0.000 core.py:33(__next__)
# 4701984/441001    0.192    0.000    7.792    0.000 core.py:356(__call__)
# 8957005/441000    3.814    0.000    7.724    0.000 core.py:148(__call__)
#    441000    0.222    0.000    7.488    0.000 core.py:96(closure)
#    441000    1.079    0.000    7.038    0.000 midi.py:64(closure)
# 7639942/3819983    0.330    0.000    5.208    0.000 core.py:294(__call__)
#   3814080    0.134    0.000    1.270    0.000 core.py:452(closure)
#   8951231    0.225    0.000    0.501    0.000 core.py:83(<lambda>)
#   4701995    0.143    0.000    0.437    0.000 core.py:344(__init__)
# 440999/440966    0.028    0.000    0.391    0.000 core.py:221(__call__)
#   3814080    0.181    0.000    0.349    0.000 <ipython-input-1-86e269f1322c>:6(f)
#   3814080    0.092    0.000    0.306    0.000 core.py:432(<lambda>)
#  14105985    0.198    0.000    0.294    0.000 core.py:528(convert_time)
#  36287429    0.258    0.000    0.259    0.000 {built-in function isinstance}
#   3814080    0.243    0.000    0.243    0.000 {method 'append' of 'list' objects}
#   8951231    0.147    0.000    0.209    0.000 core.py:405(__init__)
#  15697353    0.172    0.000    0.172    0.000 {built-in function len}
#   3814080    0.078    0.000    0.109    0.000 core.py:132(<lambda>)
#   8951231    0.062    0.000    0.062    0.000 core.py:145(__init__)
#   7640054    0.052    0.000    0.052    0.000 core.py:289(__init__)

# Another 12% reduction in function calls (31% from the original)
# Another 41% reduction in time (45% from the original)
# Awesome!

# Curiously, there are still a few __next__ calls beyond the number of samples.
# But nowhere near what it was before.
# Right now, about 20x Stream._call__ (down from 36x earlier).
# Still the largest single time sink (3.8s).
# After that, poly's closure(), which makes sense; it's fairly complicated.

# One further experiment: let's banish namify.
# Simply set stream = raw_stream.

# Hm, got a longer run. And Stream.__call__ barely went down!
# More mysteries await. At least there's no more time spent in namify's wrapper thing.

# Maybe the main argument for making Stream subclasses
# is that they allow you to avoid Stream.__call__.

# The unfortunate thing is that, if all the operators were just functions
# there would be no need for @raw_stream, because there'd be no need to promote
# streams to Streams.
# Basically, I want the operator overloading without the overhead of a wrapper class just to change type.

# In the meantime:
# I threw the old stuff out and improved SliceStream performance.
# Looking ahead, it's worth considering splitting up SliceStream to further improve performance.
# (take, drop, step...)
# The overhead of wrapping everything in Stream is unfortunate,
# but I don't see a good alternative given that we want operator overloading and methods.
# It'd be better if we could subclass function itself,
# and create streams as that subclass.
