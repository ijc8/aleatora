import pyaudio
import numpy as np
import time
import math

sample_rate = 44100

def s(seconds):
    return seconds * sample_rate

def trim(stream, index):
    def closure():
        if index == 0:
            return None
        result = stream()
        if result is None:
            return None
        value, next_stream = result
        return (value, trim(next_stream, index-1))
    return closure

# Simpler version for demonstration:
# def concat2(a, b):
#     def closure():
#         result = a()
#         if result is None:
#             return b()
#         value, next_a = result
#         return (value, concat(next_a, b))
#     return closure

def concat(*streams):
    def closure():
        if not streams:
            return None
        result = streams[0]()
        # Special case to avoid indirection when there's only one stream left.
        if len(streams) == 1:
            return result
        if result is None:
            return concat(*streams[1:])()
        value, next_stream = result
        return (value, concat(next_stream, *streams[1:]))
    return closure

def smap(stream, fn):
    def closure():
        result = stream()
        if result is None:
            return None
        value, next_stream = result
        return (fn(value), smap(next_stream, fn))
    return closure

def szip(*streams):
    def closure():
        results = [stream() for stream in streams]
        if None in results:
            return None
        values = [result[0] for result in results]
        next_streams = [result[1] for result in results]
        return (values, szip(*next_streams))
    return closure

def repeat(value):
    # Defining it this way avoids allocating additional closures.
    f = lambda: (value, f)
    return f

silence = repeat(0)

def count(start=0):
    return lambda: (start, count(start+1))

# Explicit definition:
# def osc(freq, phase=0):
#     def closure():
#         result = math.sin(phase)
#         next_phase = phase + 2*math.pi*freq/sample_rate
#         return (result, osc(freq, phase=next_phase))
#     return closure

# Shorter version in terms of smap and count:
def osc(freq):
    return smap(count(), lambda t: math.sin(2*math.pi*t*freq/sample_rate))

def callback(in_data, frame_count, time_info, status):
    global stream
    audio = np.zeros(frame_count, dtype=np.float32)
    flag = pyaudio.paContinue
    for i in range(frame_count):
        result = stream()
        if result is None:
            print("Finished playing.")
            flag = pyaudio.paComplete
            break
        value, stream = result
        audio[i] = value
    return (audio, flag)

composition = concat(trim(osc(440), s(1)),
                     trim(silence, s(0.5)),
                     trim(osc(660), s(1)))
stream = composition

def main():
    buffer_size = 1024
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    frames_per_buffer=buffer_size,
                    rate=sample_rate,
                    output=True,
                    stream_callback=callback)
    stream.start_stream()

    try:
        # Do whatever you want here.
        while stream.is_active():
            # print("Still going!")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Finishing early due to user interrupt.")

    stream.stop_stream()
    stream.close()
    p.terminate()


if __name__ == '__main__':
    main()