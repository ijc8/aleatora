import next

import sounddevice as sd
import numpy as np

import atexit
import time
import traceback

# sd.default.device = 10

# Blocking version; cleans up and returns when the composition is finished.
def run(composition):
    samples = iter(composition)

    def callback(outdata, frames, time, status):
        for i, sample in zip(range(frames), samples):
            outdata[i] = sample
        if i < frames - 1:
            print("Finished playing.")
            raise sd.CallbackStop

    with sd.OutputStream(channels=1, callback=callback) as stream:
        next.SAMPLE_RATE = stream.samplerate
        try:
            while True:
                sd.sleep(100)
        except KeyboardInterrupt:
            print("Finishing early due to user interrupt.")

# # Non-blocking version: setup() and play() are a pair. Works with the REPL.
def setup():
    if setup.done:
        return
    play_callback.samples = iter(next.silence)
    stream = sd.OutputStream(channels=1, callback=play_callback)
    next.SAMPLE_RATE = stream.samplerate
    stream.start()
    setup.done = True

    # TODO: check if this is still necessary.
    def cleanup():
        stream.stop()
        stream.close()
    atexit.register(cleanup)

setup.done = False

def play_callback(outdata, frames, time, status):
    try:
        for i, sample in zip(range(frames), play_callback.samples):
            outdata[i] = sample
        if i < frames - 1:
            print("Finished playing.")
            raise sd.CallbackStop
    except:
        traceback.print_exc()
        play_callback.samples = iter(next.silence)

def play(composition):
    if not setup.done:
        setup()
    play_callback.samples = iter(composition >> next.silence)