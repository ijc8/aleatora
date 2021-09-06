"""Integration with Rivalium (https://rivalium.com/).

Example usage:
>>> from aleatora import *
>>> from aleatora.thirdparty import rivalium
>>> play(rivalium.recv("4hb496kn6yh"))
>>> upload_stream, public_url, admin_url = rivalium.send(rand * 2 - 1)
>>> play(upload_stream)
"""
import array
from datetime import datetime, timezone
import io
import json
import tempfile
import random
import urllib.request

import numpy as np
import pyogg

from ..streams import convert_time, FunctionStream, SAMPLE_RATE, stream

def opus_to_array(opus_file, resample=True):
    data = np.ctypeslib.as_array(opus_file.buffer, (opus_file.buffer_length // 2,)) / np.iinfo(np.int16).max
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
        # TODO: Does pyogg skip the "pre-skip" samples?
        opus_file = pyogg.OpusFile(tmp.name)
    return stream(opus_to_array(opus_file).tolist())

def fetch(url, **kwargs):
    with urllib.request.urlopen(urllib.request.Request(url, **kwargs)) as req:
        return req.read()

# Notes:
#
# Expected: 1 sec + 80 ms segments
# Drop first 80ms
# Find indices of first & last zero-crossings: crop buffer to region between them
# For getting streams: Follow sortition redirect
# Playback mode as part of query. Query preserved in sortition redirect.
# Normal & live mode: request next segments from server
# Random: up to 10 files at a time from sludge.
#
# Randomly plays the first N segments returned from API.
#   Random number of iterations for request loop (e.g. 3-10):
#     Then, takes last-played segment and asks for the following segments.

@stream
def recv_urls(stream_id, max_run_length=30):
    "Returns endless stream of Rivalium segment URLs; random with sequential runs (up to `max_run_length` long)."
    while True:
        run_length = random.randrange(1, max_run_length + 1)
        url = f"https://play.rivalium.com/api/{stream_id}/?start=random"
        while run_length > 0:
            segments = json.loads(fetch(url))
            if not segments:
                # Reached the end of the stream, can't get to `run_length`.
                break
            for segment in segments[:run_length]:
                id = segment['segmentID']
                url = segment['segmentURL']
                yield url
            url = f"https://play.rivalium.com/api/{stream_id}/{id}"
            run_length -= len(segments)

def recv(stream_id):
    "Returns endless stream of samples from random Rivalium segments."
    # TODO: This should also works with groups (not just individual streams), and accomodate various formats for specifying the stream:
    #   - rvm.sh/{0,2}<id> (0 indicates stream URL, 1 indicates admin URL, 2 indicates group URL)
    #   - play.rivalium.com/api/<stream ID>
    #   - play.rivalium.com/api/<group ID>
    #   - <stream ID>
    # TODO: Eventually, this should take a `mode` kwarg to specify the playback mode (random, normal, live).
    # NOTE: This is blocking, so live playing will have underruns while segments are fetched and decoded.
    urls = recv_urls(stream_id)
    return urls.map(fetch).map(decode_ogg_opus).join()

def encode_ogg_opus(pcm_data):
    # Setup Opus encoder.
    encoder = pyogg.OpusBufferedEncoder()
    encoder.set_application("audio")
    # NOTE: Opus only supports sample rates of 8, 12, 16, 24, or 48 kHz.
    target_rate = 48000
    encoder.set_sampling_frequency(target_rate)
    if SAMPLE_RATE != target_rate:
        new_length = int(target_rate / SAMPLE_RATE * len(pcm_data))
        x = np.arange(len(pcm_data)) / SAMPLE_RATE
        new_x = np.arange(new_length) / target_rate
        pcm_data = np.interp(new_x, x, pcm_data).astype(np.int16)
    encoder.set_channels(1)
    encoder.set_frame_size(20) # milliseconds
    # Create in-memory file.
    f = io.BytesIO()
    # Encode segment.
    writer = pyogg.OggOpusWriter(f, encoder)
    writer.write(pcm_data)
    writer.close()
    return f.getbuffer()

def upload_segment(url, blob):
    boundary = b"---------------------------239558697137376533442076537635"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z").encode('utf8')
    body = b"""--%s\r
Content-Disposition: form-data; name="audio"; filename="%s.opus"\r
Content-Type: audio/ogg; codecs=opus\r
\r
%s\r
--%s--\r\n""" % (boundary, timestamp, blob, boundary)
    # TODO: Remove print.
    print(fetch(url, method="POST", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode('utf8')}"}))

def send(stream, admin_url=None, segment_duration=1.0):
    "Returns stream with side-effect of sending audio to Rivalium stream."
    if admin_url is None:
        data = json.loads(fetch("https://play.rivalium.com/api/stream", method="POST"))
        admin_url = data["admin"]
        public_url = data["public"]
    else:
        public_url = json.loads(fetch(admin_url))["public"]

    block = array.array("h", (0 for _ in range(convert_time(segment_duration))))

    @FunctionStream
    def upload_stream():
        it = iter(stream)
        i = len(block) - 1
        while i == len(block) - 1:
            i = -1
            for i, sample in zip(range(len(block)), it):
                yield sample
                block[i] = int(sample * (2**15 - 1))
            encoded = encode_ogg_opus(block[:i+1])
            upload_segment(admin_url, encoded)

    return (upload_stream, admin_url, public_url)

# TODO: Implement interface for managing Rivalium groups
# POST https://play.rivalium.com/group/create: -> returns group ID
# Currently:
#   PUT https://play.rivalium.com/group/<group ID>: body is "https://play.rivalium.com/api/<stream ID>?start=random" -> ID for removal
# In the future:
#   PUT https://play.rivalium.com/group/<group ID>: body is "https://play.rivalium.com/api/<stream ID>" -> ID for removal
# DELETE https://play.rivalium.com/group/<group ID>: body is ID for removal
# GET https://play.rivalium.com/group/<group ID>/?start=random

# In the future:
#   /length endpoint

class Group:
    def __init__(self, group_id=None):
        # self.remove_keys = {}
        raise NotImplementedError
    
    def add(self, stream_id):
        # self.remove_keys[stream_id] = remove_key
        raise NotImplementedError
    
    def remove(self, stream_id):
        # send_delete_request(..., self.remove_keys[stream_id])
        raise NotImplementedError
