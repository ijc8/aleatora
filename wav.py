import core

import numpy as np

import time
import wave


def load(filename):
    with wave.open(filename, 'rb') as w:
        width = w.getsampwidth()
        channels = w.getnchannels()
        buffer = w.readframes(w.getnframes())
        if width == 2:
            return np.frombuffer(buffer, dtype=np.int16).reshape(-1, channels).astype(np.float) / np.iinfo(np.int16).max
        elif width == 3:
            audio = np.frombuffer(buffer, dtype=np.uint8).reshape(-1, 3)
            converted = np.bitwise_or.reduce(audio << np.array([8, 16, 24]), dtype=np.int32, axis=1)
            return converted.astype(np.float).reshape(-1, channels) / np.iinfo(np.int32).max
        elif width == 4:
            return np.frombuffer(buffer, dtype=np.int32).astype(np.float).reshape(-1, channels) / np.iinfo(np.int32).max
        else:
            raise NotImplementedError(f"{width*8}-bit wave files not supported")


def load_mono(filename):
    audio = load(filename)
    return audio.sum(axis=1) / audio.shape[1]


def save(comp, filename, chunk_size=16384, verbose=False):
    w = wave.open(filename, 'wb')
    sample, comp = core.peek(comp)
    channels = getattr(sample, '__len__', lambda: 1)()
    chunk_size //= channels
    w.setnchannels(channels)
    w.setsampwidth(2)
    w.setframerate(core.SAMPLE_RATE)
    chunk = np.empty((chunk_size, channels), dtype=np.float)
    siter = iter(comp)
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
            print(f'{t} ({t/core.SAMPLE_RATE}) - real time: {time.time() - start_time}')
    w.close()