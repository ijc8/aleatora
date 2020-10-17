import core

import sounddevice as sd
import numpy as np

import atexit
import time
import traceback


# Non-interactive version; blocking, cleans up and returns when the composition is finished.
def run(composition):
    samples = iter(composition)

    def callback(outdata, frames, time, status):
        for i, sample in zip(range(frames), samples):
            outdata[i] = sample
        if i < frames - 1:
            print("Finished playing.")
            raise sd.CallbackStop

    with sd.OutputStream(channels=1, callback=callback) as stream:
        core.SAMPLE_RATE = stream.samplerate
        try:
            while True:
                sd.sleep(100)
        except KeyboardInterrupt:
            print("Finishing early due to user interrupt.")


# Interactive version: setup(), volume(), play(), addplay(). Non-blocking, works with the REPL.
def setup(device=None):
    if device is not None:
        sd.default.device = device
    play_callback.samples = iter(core.silence)
    stream = sd.OutputStream(channels=1, callback=play_callback)
    core.SAMPLE_RATE = stream.samplerate
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
        outdata *= play_callback.volume
        if i < frames - 1:
            print("Finished playing.")
            raise sd.CallbackStop
    except:
        traceback.print_exc()
        play_callback.samples = iter(core.silence)

play_callback.volume = 1.0

def volume(vol):
    play_callback.volume = vol

def play(composition):
    if not setup.done:
        setup()
    play_callback.samples = iter(composition >> core.silence)

# Add another layer to playback without resetting the position of existing layers.
def addplay(layer):
    play(play_callback.samples.rest + layer)