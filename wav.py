import core
import wave
import numpy as np


def save(comp, filename, chunk_size=8192):
    w = wave.open(filename, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(core.SAMPLE_RATE)
    chunk = np.empty(chunk_size, dtype=np.float)
    siter = iter(comp)
    i = chunk_size - 1
    while i == chunk_size - 1:
        for i, sample in zip(range(chunk_size), siter):
            chunk[i] = sample
        w.writeframes((chunk[:i] * (2**15-1)).astype(np.int16))
    w.close()