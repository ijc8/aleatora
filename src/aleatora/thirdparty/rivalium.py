"""Integration with Rivalium (https://rivalium.com/).

Example usage:
>>> from aleatora import *
>>> from aleatora.thirdparty import rivalium
>>> play(rivalium.recv("4hb496kn6yh"))
>>> upload_stream, public_url, admin_url = rivalium.send(rand * 2 - 1)
>>> play(upload_stream)
"""
from datetime import datetime, timezone
import json
import random
import queue
import re
import threading
import urllib.request

import numpy as np
try:
    import ffmpeg
except ImportError:
    print(f"Missing optional depenendency 'ffmpeg-python'. Install via `python -m pip install ffmpeg-python`.")

from .. import net
from ..streams import convert_time, FunctionStream, SAMPLE_RATE, stream


# Ogg Opus helper functions

def encode(samples, bitrate):
    return (ffmpeg
        .input('pipe:', format='f32le', acodec='pcm_f32le', ac=1, ar=SAMPLE_RATE)
        .output('pipe:', format='opus', audio_bitrate=bitrate)
        .run(input=memoryview(samples.astype(np.float32)).cast('B'), quiet=True)
    )[0]

def decode(blob):
    return np.frombuffer((ffmpeg
        .input('pipe:', format='ogg', acodec='opus')
        .output('pipe:', format='f32le', acodec='pcm_f32le', ar=SAMPLE_RATE)
        .run(input=blob, capture_stdout=True)
    )[0], np.float32)


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
    - play.rivalium.com/stream/<stream ID>
    - play.rivalium.com/group/<group ID>
    - <stream ID>
    Returns the type of ID (stream or group) and the extracted ID.
    """
    stream_url_match = re.match("(?:https?://)?(?:rvm.sh/0|play.rivalium.com/(?:api|stream)/)([A-Za-z0-9_-]+)", descriptor)
    if stream_url_match:
        return ("stream", stream_url_match.groups()[0])
    group_url_match = re.match("(?:https?://)?(?:rvm.sh/2|play.rivalium.com/group/)([A-Za-z0-9_-]+)", descriptor)
    if group_url_match:
        return ("group", group_url_match.groups()[0])
    if re.match("[A-Za-z0-9_-]+", descriptor):
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
    return recv_urls(descriptor).map(fetch).map(decode)

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

def send(stream, admin_url=None, segment_duration=1.0, bitrate=12000):
    "Returns a stream with side-effect of sending audio to a Rivalium stream."
    if admin_url is None:
        data = json.loads(fetch("https://play.rivalium.com/api/stream", method="POST"))
        admin_url = data["admin"]
        public_url = data["public"]
    else:
        public_url = json.loads(fetch(admin_url))["public"]

    block = np.empty(convert_time(segment_duration), dtype=np.float32)

    @FunctionStream
    def upload_stream():
        it = iter(stream)
        i = len(block) - 1
        q = queue.Queue()
        running = True
        def loop():
            while running:
                admin_url, block = q.get()
                upload_segment(admin_url, encode(block, bitrate))
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        while i == len(block) - 1:
            i = -1
            for i, sample in zip(range(len(block)), it):
                yield sample
                block[i] = sample
            q.put((admin_url, block[:i+1].copy()))
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
