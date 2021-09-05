import traceback

import sounddevice as sd

from .streams import audio, empty, frame, FunctionStream, Stream, peek


def get_playback_stream(streams):
    if len(streams) == 1:
        # Peek ahead to determine the number of channels automatically.
        sample, stream = peek(streams[0])
        channels = getattr(sample, "__len__", lambda: 1)()
    else:
        # Passed multiple tracks; zip them together as channels.
        stream = Stream.zip(*streams).map(frame)
        channels = len(streams)
    return stream, channels

# Non-interactive version; blocking, cleans up and returns when the composition is finished.
def run(*streams, blocksize=0):
    stream, channels = get_playback_stream(streams)
    samples = iter(stream)

    def callback(outdata, frames, time, status):
        i = -1
        for i, sample in zip(range(frames), samples):
            outdata[i] = sample
        if i < frames - 1:
            raise sd.CallbackStop

    with sd.OutputStream(channels=channels, callback=callback, blocksize=blocksize) as stream:
        audio.SAMPLE_RATE = stream.samplerate
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

# For convenience, expose this:
query_devices = sd.query_devices

def setup(device=None, channels=1, input=False, **kwargs):
    global _channels, _stream, _samples
    if _stream:
        _cleanup()

    if device is not None:
        sd.default.device = device
    if input:
        _stream = sd.Stream(channels=channels, callback=play_record_callback, **kwargs)
    else:
        _stream = sd.OutputStream(channels=channels, callback=play_callback, **kwargs)
    SAMPLE_RATE = _stream.samplerate
    _stream.start()
    _channels = channels

def play_callback(outdata, frames, time, status):
    global _samples
    if _samples is None:
        outdata[:frames] = 0
        return
    try:
        i = -1
        for i, sample in zip(range(frames), _samples):
            outdata[i] = sample
    except Exception as e:
        _samples = None
        traceback.print_exc()
    if i < frames - 1:
        # Note: we avoid stopping the PortAudio stream,
        # because making a new stream later will break connections in Jack.
        outdata[i+1:frames] = 0
        _samples = None
    outdata *= _volume

_input_sample = 0
@FunctionStream
def input_stream():
    while True:
        yield _input_sample

def play_record_callback(indata, outdata, frames, time, status):
    global _samples, _input_sample
    if _samples is None:
        outdata[:frames] = 0
        return
    try:
        i = -1
        indata = indata[:frames, 0].tolist()
        # NOTE: _input_sample gets bound BEFORE we pull the next sample from _samples.
        for i, _input_sample, sample in zip(range(frames), indata, _samples):
            outdata[i] = sample
    except Exception as e:
        _samples = None
        traceback.print_exc()
    if i < frames - 1:
        # Note: we avoid stopping the PortAudio stream,
        # because making a new stream later will break connections in Jack.
        outdata[i+1:frames] = 0
        _samples = None
    outdata *= _volume


# play() -> stops playing
# play(a) -> plays the stream a, which may have one or more channels
# play(a, b) -> plays the mono streams a, b together in stereo


def play(*streams, mix=False):
    global _samples

    if not streams:
        stream = empty
        channels = _channels
    else:
        stream, channels = get_playback_stream(streams)
    
    if mix and _samples is not None:
        # Add another layer to playback without resetting the position of existing layers.
        # NOTE: We add _samples _after_ the peek(), to avoid "generator already executing" errors due to the audio thread.
        channels = max(channels, _channels)
        stream += _samples

    if not _stream:
        setup(channels=channels)
    elif _channels < channels:
        setup(device=_stream.device, channels=channels, input=isinstance(_stream, sd.InputStream))
    _samples = iter(stream)
