import core

import time

# TODO: rename this to 'profile.py' once this is an actual python package.
# (Right now 'profile' conflicts with the built-in module 'profile'.)

## Usage example:
#
# from core import *
# from prof import profile
# _ = list(profile(osc(440)[:10.0]))
# profile.dump()
# profile.reset()
# _ = list(profile((osc(440) + osc(660)[:10.0]))


class ProfileStream(core.Stream):
    def __init__(self, entry, stream):
        self.entry = entry
        self.stream = stream

    def __call__(self):
        entry = self.entry
        start = time.perf_counter()
        result = self.stream()
        entry[2] += time.perf_counter() - start
        entry[0] += 1

        if isinstance(result, core.Return):
            entry[1] += 1
            return result
        x, next_stream = result
        return (x, ProfileStream(entry, next_stream))


# This is barely a class, hence the lowercase.
class profile:
    data = {}

    def __new__(cls, key, stream):
        if key not in profile.data:
            # List of [# of calls, # of endings, total time].
            # Using a list instead of a dict/namedtuple/etc. for performance.
            profile.data[key] = [0, 0, 0.0]
        return ProfileStream(profile.data[key], stream)

    @staticmethod
    def reset():
        profile.data.clear()

    @staticmethod
    def dump():
        print(f"Real-time budget: {1e6/core.SAMPLE_RATE:.3f}us per sample")
        for key, (calls, ends, time) in profile.data.items():
            avg = time / calls
            print(f"{key}: {calls} calls ({ends} endings)")
            print(f"{' ' * len(key)}  {avg*1e6:.3f}us avg | {time:.3f}s total | {avg*core.SAMPLE_RATE*100:.2f}% of budget")