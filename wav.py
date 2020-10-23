import core

import numpy as np

import time
import wave


def save(comp, filename, chunk_size=16384, verbose=False):
    w = wave.open(filename, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(core.SAMPLE_RATE)
    chunk = np.empty(chunk_size, dtype=np.float)
    siter = iter(comp)
    i = chunk_size - 1
    if verbose:
        t = 0
        start_time = time.time()
    while i == chunk_size - 1:
        for i, sample in zip(range(chunk_size), siter):
            chunk[i] = sample
        w.writeframes((chunk[:i] * (2**15-1)).astype(np.int16))
        if verbose:
            t += i
            print(f'{t} ({t/core.SAMPLE_RATE}) - real time: {time.time() - start_time}')
    w.close()