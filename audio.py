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

# Internals:

_setup = False
_channels = 0
_stream = None
_samples = None
# Might make this public after moving on from `from audio import *`.
_volume = 1.0

def _cleanup():
    if _stream:
        _stream.stop()
        _stream.close()

# Public:

def volume(vol=None):
    if vol is not None:
        _volume = vol
    return _volume

def setup(device=None, channels=1):
    global _setup, _channels, _stream, _samples
    if _setup:
        _cleanup()
        _setup = False

    if device is not None:
        sd.default.device = device
    _samples = iter(core.silence)
    _stream = sd.OutputStream(channels=channels, callback=play_callback)
    core.SAMPLE_RATE = _stream.samplerate
    _stream.start()
    _channels = channels
    _setup = True

    # TODO: check if this is still necessary.
    if not _setup:
        atexit.register(_cleanup)

def play_callback(outdata, frames, time, status):
    global _samples
    try:
        for i, sample in zip(range(frames), _samples):
            outdata[i] = sample
        outdata *= _volume
        if i < frames - 1:
            print("Finished playing.")
            raise sd.CallbackStop
    except:
        traceback.print_exc()
        _samples = iter(core.silence)


# play() -> plays silence
# play(a) -> plays the stream a, which may have one or more channels
# play(a, b) -> plays the mono streams a, b together in stereo


def play(*composition):
    global _samples
    if len(composition) > 1:
        # Passed multiple tracks; zip them together as channels.
        channels = len(composition)
        composition = core.ZipStream(composition)
    else:
        composition = composition[0] if composition else core.silence
        # Peek ahead to determine the number of channels automatically.
        sample, composition = core.peek(composition)
        channels = getattr(sample, '__len__', lambda: 1)()
    if not _setup or _channels != channels:
        setup(channels=channels)
    _samples = iter(composition >> core.silence)

# Add another layer to playback without resetting the position of existing layers.
def addplay(layer):
    play(_samples.rest + layer)