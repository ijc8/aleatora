import threading
import socket
import queue

from .streams import stream

# A blocking stream is one which always yields a meaningful sample,
# but may block for a while getting it: for example, a network stream.
# A nonblocking stream, instead of blocking until it can yield the sample,
# immediately yields a value indicating "not ready yet" (such as None).

# Blocking streams are contagious in the sense that (nonblocking + blocking) is blocking,
# blocking[:end] is blocking, and (nonblocking >> blocking) is partly blocking.

# We can convert any (IO-bound) blocking stream into a nonblocking stream
# by running it in another thread.
# We can convert a nonblocking stream into a blocking one via Stream.filter().

@stream
def unblock(stream, filler=None, hold=False):
    """Convert a blocking stream into a non-blocking stream by running thunks in a separate thread.
    
    This creates one thread per thunk, and it does not start computing a thunk until the next value is requested.
    It should not be used on nonblocking streams, as the overhead will slow them down.
    While the next value is being computed, this will yield filler values in the meantime.
    These can either be a specific value (None by default), or the last computed value if hold is True.
    """
    it = iter(stream)
    value = None
    done = object()
    def wrapper():
        nonlocal value
        try:
            value = next(it)
        except StopIteration:
            value = done

    while True:
        thread = threading.Thread(target=wrapper)
        thread.start()
        while thread.is_alive():
            yield filler
        if value is done:
            return
        yield value
        if hold:
            filler = value

@stream
def enqueue(blocking_stream, filler=None, size=1024):
    """Convert a blocking stream into a non-blocking stream by running it ahead in another thread.

    This creates a single thread at the start of iteration and starts computing immediately.
    Unlike `unblock()`, the blocking stream will run past the non-blocking stream, queueing up to `size` elements ahead.
    Yields `filler` if there are no elements ready in the queue.
    """
    q = queue.Queue(size)
    def loop():
        for item in blocking_stream:
            q.put(item)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    while t.is_alive():
        try:
            yield q.get_nowait()
        except queue.Empty:
            yield filler

@stream
def latest(stream, filler=None):
    """Convert a blocking stream into a non-blocking stream by running it ahead in another thread.
    
    Unlike `enqueue()`, the blocking stream runs as fast as possible (no blocking on the main thread).
    The non-blocking stream always yields the most recent value received from the blocking stream,
    which means that any values received between pulls on the non-blocking stream are lost.
    This behavior is useful for e.g. UDP (and more specifically OSC) streams used for control,
    where only the most recent data is relevant.
    """
    value = filler
    def loop():
        nonlocal value
        for item in stream:
            value = item

    thread = threading.Thread(target=loop)
    thread.start()
    while thread.is_alive():
        yield value

# This acts as a TCP client
# TODO: Test with netcat
@stream
def byte_stream(address, port, chunk_size=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((address, port))
    while True:
        data = s.recv(chunk_size)
        if not data:
            return
        yield data

# This acts as a UDP server
# Yields a stream of (datagram bytes, address of sender)
@stream
def packet_stream(address, port, max_packet_size=65536):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((address, port))
    while True:
        yield s.recvfrom(max_packet_size)


import oscpy
import oscpy.parser
from collections import namedtuple

OSCMessage = namedtuple('OSCMessage', ('address', 'tags', 'args', 'index'))

@stream
def osc_stream(address='0.0.0.0', port=8000):
    for packet, _ in packet_stream(address, port, 65536):
        for message in oscpy.parser.read_packet(packet):
            yield OSCMessage(*message)

# TODO: Try writing the other versions with generators, compare performance again.
# Notes from experimentation (back in Aleatora Classic):
# @raw_stream
# def blocking_count(count=0):
#     def closure():
#         time.sleep(1)
#         return (count, blocking_count(count + 1))
#     return closure

# # Approach 1: Run each frame in its own thread.
# @raw_stream
# def unblock_stream1(blocking_stream, filler=None):
#     ret = None
#     def wrapper():
#         nonlocal ret
#         ret = blocking_stream()
#     t = threading.Thread(target=wrapper)
#     def closure():
#         nonlocal t
#         if t.is_alive():
#             return (filler, closure)
#         if isinstance(ret, Return):
#             return ret
#         value, next_stream = ret
#         return (value, unblock_stream1(next_stream, filler))
#     # NOTE: We wait until the first sample is requested to start the thread.
#     def init():
#         t.start()
#         return closure()
#     return init

# # Informal performance measure:
# #   unblock_stream(blocking_count()).zip(count()).filter(lambda p: p[0] == 3)()[0][1]
# # returns 10248400, meaning unblock stream ran about 10M times in 4 seconds.

# # Approach 2: Run the other stream in the same thread.
# # This version allows the blocking stream to run ahead.
# # Specifying maxlen bounds how far it can run ahead; maxlen=0
# # creates an unbounded queue, but this is dangerous for infinite streams,
# # as the thread running blocking_stream will just keep going.
# import queue

# def unblock_stream2(blocking_stream, filler=None, maxlen=1024):
#     q = queue.Queue(maxlen)
#     it = iter(blocking_stream)
#     def wrapper():
#         for item in it:
#             q.put(item)
#     t = threading.Thread(target=wrapper)
#     t.start()
#     def closure():
#         try:
#             return (q.get_nowait(), closure)
#         except queue.Empty:
#             if t.is_alive():
#                 return (filler, closure)
#             return it.returned
#     closure = Stream(closure)
#     return closure

# # Informal performance measure: 6121484

# # This version waits to start the next thunk until the previous value has been received.
# def unblock_stream3(blocking_stream, filler=None):
#     event = threading.Event()
#     value = None
#     ready = False
#     it = iter(blocking_stream)
#     def wrapper():
#         nonlocal value, ready
#         for value in it:
#             ready = True
#             event.wait()
#             event.clear()
#     t = threading.Thread(target=wrapper)
#     def closure():
#         if not t.is_alive():
#             return it.returned
#         if ready:
#             out = value
#             event.set()
#             return (out, closure)
#         return (filler, closure)
#     closure = Stream(closure)
#     def init():
#         t.start()
#         return closure()
#     return Stream(init)

# # Informal performance measure: 5910909
# # Surprising; the version that creates a new thread for each thunk appears to be the winner.
# # Maybe not that surprising; in this example, only four thunks (of the blocking stream) get called.

# # Let's try them with a function that's not actually blocking.
# # unblock_stream(count()).filter(lambda x: x == 1e6)()[0]
# # In this case, the only function that doesn't take forever is #2.

# @raw_stream
# def hold_value(stream, filler=None, init=None):
#     "Replace filler values with the last non-filler value."
#     def closure():
#         result = stream()
#         if isinstance(result, Return):
#             return result
#         value, next_stream = result
#         if value is filler:
#             return (init, hold_value(next_stream, filler, init))
#         return (value, hold_value(next_stream, filler, value))
#     return closure


# def block_stream(stream, filler=None):
#     "Convert a nonblocking stream to a blocking stream."
#     return stream.filter(lambda x: x is not filler)

# # Example: random integers from random.org.

# import time
# import urllib.request
# RANDOM_URL = "https://www.random.org/integers/?num=1&min={0}&max={1}&col=1&base=10&format=plain&rnd=new"

# @raw_stream
# def random_org_stream(min=1, max=100):
#     def closure():
#         time.sleep(1)
#         url = RANDOM_URL.format(min, max)
#         value = int(urllib.request.urlopen(url).read().strip())
#         return (value, random_org_stream(1, 100))
#     return closure
