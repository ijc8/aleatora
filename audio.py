import pyaudio
import numpy as np
import core
import atexit
import time

def callback(in_data, frame_count, time_info, status):
    flag = pyaudio.paContinue
    for i, sample in zip(range(frame_count), callback.samples):
        callback.audio[i] = sample
    if i < frame_count - 1:
        print("Finished playing.")
        flag = pyaudio.paComplete
    return (callback.audio, flag)

# Blocking version; cleans up PyAudio and returns when the composition is finished.
def run(composition, buffer_size=1024):
    callback.samples = iter(composition)
    callback.audio = np.zeros(buffer_size, dtype=np.float32)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    frames_per_buffer=buffer_size,
                    rate=core.SAMPLE_RATE,
                    output=True,
                    stream_callback=callback)
    stream.start_stream()
    setup.done = True

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Finishing early due to user interrupt.")

    stream.stop_stream()
    stream.close()
    p.terminate()

# Non-blocking version: setup() and play() are a pair. Works with the REPL.
def setup(buffer_size=1024):
    if setup.done:
        return
    callback.samples = core.silence
    callback.audio = np.zeros(buffer_size, dtype=np.float32)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    frames_per_buffer=buffer_size,
                    rate=core.SAMPLE_RATE,
                    output=True,
                    stream_callback=callback)
    stream.start_stream()
    setup.done = True

    def cleanup():
        # Seems like pyaudio should already do this, via e.g. stream.__del__ and p.__del___...
        stream.stop_stream()
        stream.close()
        p.terminate()
    atexit.register(cleanup)

setup.done = False

def play(composition):
    callback.samples = iter(composition >> core.silence)