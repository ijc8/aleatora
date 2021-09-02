from . import streams

import numpy as np

import time
import wave


def load_array(filename, resample=False):
    with wave.open(filename, "rb") as w:
        width = w.getsampwidth()
        channels = w.getnchannels()
        sample_rate = w.getframerate()
        buffer = w.readframes(w.getnframes())
    if width == 2:
        data = np.frombuffer(buffer, dtype=np.int16).reshape(-1, channels).astype(np.float) / np.iinfo(np.int16).max
    elif width == 3:
        audio = np.frombuffer(buffer, dtype=np.uint8).reshape(-1, 3)
        converted = np.bitwise_or.reduce(audio << np.array([8, 16, 24]), dtype=np.int32, axis=1)
        data = converted.astype(np.float).reshape(-1, channels) / np.iinfo(np.int32).max
    elif width == 4:
        data = np.frombuffer(buffer, dtype=np.int32).astype(np.float).reshape(-1, channels) / np.iinfo(np.int32).max
    else:
        raise NotImplementedError(f"{width*8}-bit wave files not supported")
    if resample and streams.SAMPLE_RATE != w.getframerate():
        new_data = np.empty((int(streams.SAMPLE_RATE / sample_rate * len(data)), data.shape[1]))
        x = np.arange(len(data)) / sample_rate
        new_x = np.arange(len(new_data)) / streams.SAMPLE_RATE
        for i in range(data.shape[1]):
            new_data[:, i] = np.interp(new_x, x, data[:, i])
        data = new_data
    return data

def load(filename, resample=False, multichannel=False):
    data = load_array(filename, resample=resample)
    if multichannel:
        return streams.stream([streams.frame(x) for x in data.tolist()])
    return streams.stream(data.mean(axis=1).tolist())


def save(comp, filename, chunk_size=16384, verbose=False):
    w = wave.open(filename, "wb")
    sample, comp = streams.peek(comp)
    channels = getattr(sample, "__len__", lambda: 1)()
    chunk_size //= channels
    w.setnchannels(channels)
    w.setsampwidth(2)
    w.setframerate(streams.SAMPLE_RATE)
    chunk = np.empty((chunk_size, channels), dtype=np.float)
    siter = iter(comp)
    # Avoid holding onto memory if e.g. memoize() is involved:
    del comp
    i = chunk_size - 1
    if verbose:
        t = 0
        start_time = time.time()
    while i == chunk_size - 1:
        for i, sample in zip(range(chunk_size), siter):
            chunk[i] = sample
        w.writeframes((chunk[:i+1] * (2**15-1)).astype(np.int16))
        if verbose:
            t += (i + 1)
            print(f"{t} ({t/streams.SAMPLE_RATE}) - real time: {time.time() - start_time}")
    w.close()
