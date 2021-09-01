"""Profile streams.

Example usage:

    >>> from aleatora import osc, profile
    >>> _ = list(profile('osc', osc(440)[:10.0]))
    >>> _ = list(profile('mix', (osc(440) + osc(660))[:10.0]))
    >>> profile.dump()
    Real-time budget: 22.676us per sample
    osc: 441001 calls (1 ending)
        0.098us avg | 0.043s total | 0.43% of budget
    mix: 441001 calls (1 ending)
        0.226us avg | 0.099s total | 0.99% of budget
    >>> profile.reset()
"""

import time

from . import streams


@streams.stream
def profile_stream(entry, stream):
    it = iter(stream)
    while True:
        entry[0] += 1
        try:
            start = time.perf_counter()
            value = next(it)
            entry[2] += time.perf_counter() - start
        except StopIteration as e:
            entry[2] += time.perf_counter() - start
            entry[1] += 1
            return e.value
        yield value


# This is what's exposed in the package.
class profile:
    # Set class docstring to module docstring.
    __doc__ = __doc__

    data = {}

    def __new__(cls, key, stream):
        if key not in profile.data:
            # List of [# of calls, # of endings, total time].
            # Using a list instead of a dict/namedtuple/etc. for performance.
            profile.data[key] = [0, 0, 0.0]
        return profile_stream(profile.data[key], stream)

    @staticmethod
    def reset():
        "Reset profiler."
        profile.data.clear()

    @staticmethod
    def dump():
        "Print out collected profiling data."
        print(f"Real-time budget: {1e6/streams.SAMPLE_RATE:.3f}us per sample")
        for key, (calls, ends, time) in profile.data.items():
            avg = time / calls
            print(f"{key}: {calls} calls ({ends} ending{'' if ends == 1 else 's'})")
            print(f"{' ' * len(key)}  {avg*1e6:.3f}us avg | {time:.3f}s total | {avg*streams.SAMPLE_RATE*100:.2f}% of budget")
