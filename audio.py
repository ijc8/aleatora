import core

import sounddevice as sd
import numpy as np

import atexit
import time
import traceback


# Non-interactive version; blocking, cleans up and returns when the composition is finished.
def run(composition, blocksize=0):
    samples = iter(composition)

    def callback(outdata, frames, time, status):
        for i, sample in zip(range(frames), samples):
            outdata[i] = sample
        if i < frames - 1:
            raise sd.CallbackStop

    with sd.OutputStream(channels=1, callback=callback, blocksize=blocksize) as stream:
        core.SAMPLE_RATE = stream.samplerate
        try:
            while stream.active:
                sd.sleep(100)
        except KeyboardInterrupt:
            print("Finishing early due to user interrupt.")


# Interactive version: setup(), volume(), play(), addplay(). Non-blocking, works with the REPL.

# Internals:

_channels = 0
_stream = None
_samples = None
# Might make this public after moving on from `from audio import *`.
_volume = 1.0

def _cleanup():
    global _stream
    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None

# Public:

def volume(vol=None):
    global _volume
    if vol is not None:
        _volume = vol
    return _volume


# List devices with sd.query_devices().

def setup(device=None, channels=1, input=False):
    global _channels, _stream, _samples
    if _stream:
        _cleanup()

    if device is not None:
        sd.default.device = device
    if input:
        _stream = sd.Stream(channels=channels, callback=play_record_callback)
    else:
        _stream = sd.OutputStream(channels=channels, callback=play_callback)
    core.SAMPLE_RATE = _stream.samplerate
    _stream.start()
    _channels = channels

def play_callback(outdata, frames, time, status):
    global _samples
    if _samples is None or _samples.returned:
        outdata[:frames] = 0
        return
    try:
        i = -1
        # NOTE: This assumes _input_sample gets bound BEFORE we pull the next sample from _samples.
        # TODO: Make sure it actually works like that!
        for i, sample in zip(range(frames), _samples):
            outdata[i] = sample
        outdata *= _volume
        if _samples.returned:
            outdata[i+1:frames] = 0
            # Note: we avoid stopping the PortAudio stream,
            # because making a new stream later will break connections in Jack.
    except Exception as e:
        _samples.returned = e
        traceback.print_exc()

_input_sample = 0
input_stream = core.Stream(lambda: (_input_sample, input_stream))

def play_record_callback(indata, outdata, frames, time, status):
    global _samples, _input_sample
    if _samples is None or _samples.returned:
        outdata[:frames] = 0
        return
    try:
        i = -1
        indata = indata[:frames, 0].tolist()
        # NOTE: This assumes _input_sample gets bound BEFORE we pull the next sample from _samples.
        # TODO: Make sure it actually works like that!
        for i, _input_sample, sample in zip(range(frames), indata, _samples):
            outdata[i] = sample
        outdata *= _volume
        if _samples.returned:
            outdata[i+1:frames] = 0
            # Note: we avoid stopping the PortAudio stream,
            # because making a new stream later will break connections in Jack.
    except Exception as e:
        _samples.returned = e
        traceback.print_exc()


# play() -> stops playing
# play(a) -> plays the stream a, which may have one or more channels
# play(a, b) -> plays the mono streams a, b together in stereo


def play(*streams):
    global _samples
    if not streams:
        stream = core.empty
        channels = _channels
    elif len(streams) == 1:
        # Peek ahead to determine the number of channels automatically.
        sample, stream = core.peek(streams[0])
        channels = getattr(sample, '__len__', lambda: 1)()
    else:
        # Passed multiple tracks; zip them together as channels.
        stream = core.ZipStream(streams)
        channels = len(streams)

    if not _stream:
        setup(channels=channels)
    elif _channels < channels:
        setup(device=_stream.device, channels=channels, input=isinstance(_stream, sd.InputStream))
    _samples = iter(stream)


# Add another layer to playback without resetting the position of existing layers.
def addplay(layer):
    play(_samples.rest + layer)