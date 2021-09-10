"""Integration with Rivalium (https://rivalium.com/).

Example usage:
>>> from aleatora import *
>>> from aleatora.thirdparty import rivalium
>>> play(rivalium.recv("4hb496kn6yh"))
>>> upload_stream, public_url, admin_url = rivalium.send(rand * 2 - 1)
>>> play(upload_stream)
"""
from datetime import datetime, timezone
import io
import json
import random
import queue
import re
import tempfile
import threading
import urllib.request

import numpy as np
import pyogg

from .. import net
from ..streams import convert_time, FunctionStream, SAMPLE_RATE, stream


# Ogg Opus helper functions

def opus_to_array(opus_file, resample=True):
    data = opus_file.as_array().reshape(-1) / np.iinfo(np.int16).max
    if resample and opus_file.frequency != SAMPLE_RATE:
        new_length = int(SAMPLE_RATE / opus_file.frequency * len(data))
        x = np.arange(len(data)) / opus_file.frequency
        new_x = np.arange(new_length) / SAMPLE_RATE
        data = np.interp(new_x, x, data)
    return data

def decode_ogg_opus(blob):
    # HACK: pyogg does not supported decoding Ogg Opus data from memory, so we write to a temporary file.
    # (The underlying library, libopusfile, actually does via `op_open_memory`, so perhaps a PR is in order?)
    with tempfile.NamedTemporaryFile(mode='wb') as tmp:
        tmp.write(blob)
        tmp.flush()
        # NOTE: Seems like pyogg skips the "pre-skip" samples.
        opus_file = pyogg.OpusFile(tmp.name)
    return opus_to_array(opus_file)

def encode_ogg_opus(samples, sample_rate):
    # Setup Opus encoder.
    encoder = pyogg.OpusBufferedEncoder()
    encoder.set_application("audio")
    # NOTE: Opus only supports sample rates of 8, 12, 16, 24, or 48 kHz.
    encoder.set_sampling_frequency(sample_rate)
    if SAMPLE_RATE != sample_rate:
        new_length = int(sample_rate / SAMPLE_RATE * len(samples))
        x = np.arange(len(samples)) / SAMPLE_RATE
        new_x = np.arange(new_length) / sample_rate
        samples = np.interp(new_x, x, samples)
    encoder.set_channels(1)
    encoder.set_frame_size(20) # milliseconds
    # Create in-memory file.
    f = io.BytesIO()
    # Encode segment.
    writer = pyogg.OggOpusWriter(f, encoder)
    samples *= 2**15 - 1
    samples = samples.astype(np.int16)
    writer.write(samples.data.cast("B"))
    writer.close()
    return f.getbuffer()


# Networking helpers functions

def fetch(url, **kwargs):
    with urllib.request.urlopen(urllib.request.Request(url, **kwargs)) as req:
        return req.read()

def upload_segment(url, blob):
    boundary = b"---------------------------239558697137376533442076537635"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z").encode('utf8')
    body = b"""--%s\r
Content-Disposition: form-data; name="audio"; filename="%s.opus"\r
Content-Type: audio/ogg; codecs=opus\r
\r
%s\r
--%s--\r\n""" % (boundary, timestamp, blob, boundary)
    fetch(url, method="POST", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode('utf8')}"})


# Rivalium functions

def extract_id(descriptor):
    """Parse a stream or group descriptor in a supported format:

    - rvm.sh/0<stream ID>
    - rvm.sh/2<group ID>
    - play.rivalium.com/api/<stream ID>
    - play.rivalium.com/group/<group ID>
    - <stream ID>
    Returns the type of ID (stream or group) and the extracted ID.
    """
    stream_url_match = re.match("(?:https?://)?(?:rvm.sh/0|play.rivalium.com/api/)(\w+)", descriptor)
    if stream_url_match:
        return ("stream", stream_url_match.groups()[0])
    group_url_match = re.match("(?:https?://)?(?:rvm.sh/2|play.rivalium.com/group/)(\w+)", descriptor)
    if group_url_match:
        return ("group", group_url_match.groups()[0])
    if re.match("\w+", descriptor):
        return ("stream", descriptor)
    raise ValueError("Expected valid stream/group URL or stream ID.")

@stream
def recv_urls(descriptor, max_run_length=30):
    "Returns endless stream of Rivalium segment URLs; random with sequential runs (up to `max_run_length` long)."
    type, id = extract_id(descriptor)
    prefix = type if type == "group" else "api"
    while True:
        run_length = random.randrange(1, max_run_length + 1)
        url = f"https://play.rivalium.com/{prefix}/{id}/?start=random"
        while run_length > 0:
            segments = json.loads(fetch(url))
            if not segments:
                # Reached the end of the stream, can't get to `run_length`.
                break
            for segment in segments[:run_length]:
                yield segment['segmentURL']
            url = f"https://play.rivalium.com/{prefix}/{id}/{segment['segmentID']}"
            run_length -= len(segments)

def recv_segments(descriptor):
    "Return stream of segments (as numpy arrays) from Rivalium stream or group (in random playback mode)."
    return recv_urls(descriptor).map(fetch).map(decode_ogg_opus)

def zero_crossing_crop(segment):
    "Crop segment to region between first and last zero-crossings, for click-free concatenation."
    zero_crossings = np.where(np.diff(np.sign(segment)))[0]
    start_index = zero_crossings[0] + 1  # Index after first zero-crossing
    end_index = zero_crossings[-1]  # Index before last zero-crossing
    return segment[start_index:end_index]

def recv(descriptor):
    "Returns endless stream of samples from Rivalium stream or group (in random playback mode)."
    # TODO: Eventually, this should take a `mode` kwarg to specify the playback mode (random, normal, live).
    cropped_segments = recv_segments(descriptor).map(zero_crossing_crop).map(np.ndarray.tolist)
    # Fetch and decode in another thread; queue up to 4 segments in advance.
    return net.enqueue(cropped_segments, filler=[0], size=4).join()

def send(stream, admin_url=None, segment_duration=1.0, sample_rate=12000):
    "Returns a stream with side-effect of sending audio to a Rivalium stream."
    if admin_url is None:
        data = json.loads(fetch("https://play.rivalium.com/api/stream", method="POST"))
        admin_url = data["admin"]
        public_url = data["public"]
    else:
        public_url = json.loads(fetch(admin_url))["public"]

    block = np.empty(convert_time(segment_duration), dtype=float)

    @FunctionStream
    def upload_stream():
        it = iter(stream)
        i = len(block) - 1
        q = queue.Queue()
        running = True
        def loop():
            while running:
                admin_url, block = q.get()
                upload_segment(admin_url, encode_ogg_opus(block, sample_rate))
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        while i == len(block) - 1:
            i = -1
            for i, sample in zip(range(len(block)), it):
                yield sample
                block[i] = sample
            q.put((admin_url, block[:i+1]))
        running = False

    return (upload_stream, public_url, admin_url)


class Group:
    """Class representing a Rivalium group.
    
    Example usage:
    >>> group = rivalium.Group()
    >>> group.add("4hb496kn6yh")
    >>> upload_stream, public_url, admin_url = rivalium.send(rand * 2 - 1)
    >>> group.add(public_url)
    >>> upload_stream[:10.0].run()
    >>> play(group.recv())
    >>> # time elapses...
    >>> group.remove(public_url)
    """
    def __init__(self, group_id=None):
        self.group_id = group_id or fetch("https://play.rivalium.com/group/create", method="POST").decode("utf8")
        self.remove_keys = {}
    
    def recv(self):
        return recv(f"rvm.sh/2{self.group_id}")
    
    def add(self, stream_descriptor):
        type, stream_id = extract_id(stream_descriptor)
        if type != "stream":
            raise ValueError("Expected stream, got group.")
        key = fetch(
            f"https://play.rivalium.com/group/{self.group_id}",
            data=f"https://play.rivalium.com/api/{stream_id}?start=random".encode("utf8"),
            method="PUT", headers={"Content-Type": "text/plain"}
        )
        self.remove_keys[stream_id] = key
    
    def remove(self, stream_descriptor):
        type, stream_id = extract_id(stream_descriptor)
        if type != "stream":
            raise ValueError("Expected stream, got group.")
        fetch(
            f"https://play.rivalium.com/group/{self.group_id}",
            data=self.remove_keys[stream_id],
            method="DELETE", headers={"Content-Type": "text/plain"}
        )
