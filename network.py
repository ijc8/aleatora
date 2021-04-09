import threading
import queue

from core import *

# A blocking stream is one which always yields a meaningful sample,
# but may block for a while getting it. For example, a network stream.
# A nonblocking stream, instead of blocking until it can yield the sample,
# immediately yields a value indicating "not ready yet" (such as None).

# Blocking streams are contagious in the sense that (nonblocking + blocking) is blocking,
# blocking[:end] is blocking, and (nonblocking >> blocking) is partly blocking.

# We can convert any (IO-bound) blocking stream into a nonblocking stream
# by running it in another thread.
# We can convert a nonblocking stream into a blocking one via Stream.filter().

@raw_stream
def blocking_count(count=0):
    def closure():
        time.sleep(1)
        return (count, blocking_count(count + 1))
    return closure

# Approach 1: Run each frame in its own thread.
@raw_stream
def unblock_stream1(blocking_stream, filler=None):
    ret = None
    def wrapper():
        nonlocal ret
        ret = blocking_stream()
    t = threading.Thread(target=wrapper)
    def closure():
        nonlocal t
        if t.is_alive():
            return (filler, closure)
        if isinstance(ret, Return):
            return ret
        value, next_stream = ret
        return (value, unblock_stream(next_stream, filler))
    # NOTE: We wait until the first sample is requested to start the thread.
    def init():
        t.start()
        return closure()
    return init

# Informal performance measure:
#   unblock_stream(blocking_count()).zip(count()).filter(lambda p: p[0] == 3)()[0][1]
# returns 10248400, meaning unblock stream ran about 10M times in 4 seconds.

# Approach 2: Run the other stream in the same thread.
# This version allows the blocking stream to run ahead.
# Specifying maxlen bounds how far it can run ahead; maxlen=0
# creates an unbounded queue, but this is dangerous for infinite streams,
# as the thread running blocking_stream will just keep going.
def unblock_stream(blocking_stream, filler=None, maxlen=1024):
    q = queue.Queue(maxlen)
    it = iter(blocking_stream)
    def wrapper():
        for item in it:
            q.put(item)
    t = threading.Thread(target=wrapper)
    t.start()
    def closure():
        try:
            return (q.get_nowait(), closure)
        except queue.Empty:
            if t.is_alive():
                return (filler, closure)
            return it.returned
    closure = Stream(closure)
    return closure

# Informal performance measure: 6121484

# This version waits to start the next thunk until the previous value has been received.
def unblock_stream3(blocking_stream, filler=None):
    event = threading.Event()
    value = None
    ready = False
    it = iter(blocking_stream)
    def wrapper():
        nonlocal value, ready
        for value in it:
            ready = True
            event.wait()
            event.clear()
    t = threading.Thread(target=wrapper)
    def closure():
        if not t.is_alive():
            return it.returned
        if ready:
            out = value
            event.set()
            return (out, closure)
        return (filler, closure)
    closure = Stream(closure)
    def init():
        t.start()
        return closure()
    return Stream(init)

# Informal performance measure: 5910909
# Surprising; the version that creates a new thread for each thunk appears to be the winner.
# Maybe not that surprising; in this example, only four thunks (of the blocking stream) get called.

# Let's try them with a function that's not actually blocking.
# unblock_stream(count()).filter(lambda x: x == 1e6)()[0]
# In this case, the only function that doesn't take forever is #2.

@raw_stream
def hold_value(stream, filler=None, init=None):
    "Replace filler values with the last non-filler value."
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        value, next_stream = result
        if value is filler:
            return (init, hold_value(next_stream, filler, init))
        return (value, hold_value(next_stream, filler, value))
    return closure


def block_stream(stream, filler=None):
    "Convert a nonblocking stream to a blocking stream."
    return stream.filter(lambda x: x is not filler)


# Example: random integers from random.org.

import time
import urllib.request
RANDOM_URL = "https://www.random.org/integers/?num=1&min={0}&max={1}&col=1&base=10&format=plain&rnd=new"

@raw_stream
def random_org_stream(min=1, max=100):
    def closure():
        time.sleep(1)
        url = RANDOM_URL.format(min, max)
        value = int(urllib.request.urlopen(url).read().strip())
        return (value, random_org_stream(1, 100))
    return closure