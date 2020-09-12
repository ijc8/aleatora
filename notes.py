import math

sample_rate = 44100

# Consider:
def osc(freq):
    phase = 0
    while True:
        yield math.sin(phase)
        phase += 2*math.pi*freq/sample_rate

# The problem with this is that there's no way to go back.
# The generator only advances.
# g = osc(440)
# next(g) => 0.0
# next(g) => 0.06264832417874368
# The old states are lost.
# This is problematic whenever a generator has moderately complex execution, or is nondeterministic.
# Wow. You can actually get inside the generator: g.gi_frame.f_locals
# Looks like the dict just gets updated between next() calls.
# General issue here: locals might be mutable
# So for this to work as expected, need to adopt a functional, immutable approach

# That said, hacking Python generators might be a worthwhile approach...
# The issue is that the generator object keeps its internal state.
# This is problematic for 'replaying' from an earlier point.
# The closure-based model (or equivalently a model that yields its updated local state, to be passed to the next call)
# automatically gives replay points everywhere.
# But a generator-hack model could provide replaying 'on demand' by copying the generator frame...

# It would be good to get a refresher on when I really want this replaying functionality.

# Hmm. Can't add a __slice__ method to the built-in generator type.
# Maybe it's time for a decorator? @stream
# Takes the generator and wraps it in a Stream that has __next__ and __slice__.

# One question remains before I go in on this generator-hack approach.
# What about final return values? What about split?
def test():
    yield 1
    yield 2
    yield 3
    return 4
# Ahahaha. StopIteration does this beautifully: it includes the return value as e.value. Great!
# Conveniently, this means the special case for end-of-stream is just a try-except.

# Here's Pipe's ">>":
def concat(a, b):
    yield from a
    yield from b

# Thanks to yield from, that also handles the return value propagation correctly, among other things.
# Now here's ">>=":
def bind(a, fn_b):
    v = yield from a
    yield from fn_b(v)

class Stream:
    def __init__(self, gen):
        self.gen = gen

    def __getitem__(self, index):
        if isinstance(index, int):
            f_locals = self.gen.gi_frame.f_locals.copy()
            for i in range(index):
                try:
                    value = next(self.gen)
                except StopIteration:
                    raise IndexError("stream index out of range")
            self.gen.gi_frame.f_locals.update(f_locals)
            return value
        if isinstance(index, slice):
            pass  # abandoned due to realizations below

def test2():
    x = 0
    yield x
    x += 1
    yield x

# Welp. Nevermind. The frame object (gen.gi_frame) can't actually be manipulated - not even f_locals.
# So much for that plan.

# Here's a reason to want 'random-access' replayability (i.e. something beyond generator factories):
import random
def example():
    yield -1
    if random.random < 0.5:
        print("A is happening!")
        while True:
            yield random.random()
    else:
        while True:
            yield -random.random()

# A continuation-based approach could allow you to cut off the beginning and still get consistent behavior on replays,
# because the decision was made 'in the past' - that is, earlier in the stream.
# This is impossible in a generator-based system because it can only replay from the 'start', which means remaking the decision.
# More generally, the generator-factory approach violates the notion that a stream should be one item... followed by another stream.
# This is because there is no way to make another factory for the rest of the stream.
# You could fake it by returning a modified factory that drops the first N elements, but this would remake all the earlier decisions,
# and re-perform all of the earlier side effects.

# You can't convert a generator to a stream in general, because of the issues described above.
# but you CAN easily convert a generator to a memoized stream (in which case iterations only execute once; replay is just from memory).
# This is totally fine if you don't need nondeterministic replay (as when the generator is deterministic and doesn't depend on other streams).
