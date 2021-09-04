"""Integration with Rivalium (https://rivalium.com/).

Example usage:
>>> from aleatora import *
>>> from aleatora.thirdparty import rivalium
>>> play(rivalium.recv("4hb496kn6yh"))
>>> upload_stream, public_url, admin_url = rivalium.send(rand * 2 - 1)
>>> play(upload_stream)
"""
import json
import tempfile
import random
import urllib.request

import numpy as np
import pyogg

from ..streams import SAMPLE_RATE, stream

def opus_to_array(opus_file, resample=True):
    data = np.ctypeslib.as_array(opus_file.buffer, (opus_file.buffer_length // 2,)) / np.iinfo(np.int16).max
    if resample and opus_file.frequency != SAMPLE_RATE:
        new_length = int(SAMPLE_RATE / opus_file.frequency * len(data))
        x = np.arange(len(data)) / opus_file.frequency
        new_x = np.arange(new_length) / SAMPLE_RATE
        data = np.interp(new_x, x, data)
    return data

def decodeOggOpus(blob):
    # HACK: pyogg does not supported decoding Ogg Opus data from memory, so we write to a temporary file.
    # (The underlying library, libopusfile, actually does via `op_open_memory`, so perhaps a PR is in order?)
    with tempfile.NamedTemporaryFile(mode='wb') as tmp:
        tmp.write(blob)
        tmp.flush()
        # TODO: Does pyogg skip the "pre-skip" samples?
        opus_file = pyogg.OpusFile(tmp.name)
    return stream(opus_to_array(opus_file).tolist())

def fetch(url):
    with urllib.request.urlopen(url) as req:
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
def recv_urls(stream_id):
    "Returns stream of Rivalium segment URLs; random with short sequential runs."
    while True:
        chain_steps = random.randrange(1, 6)
        url = f"https://play.rivalium.com/api/{stream_id}/?start=random"
        for _ in range(chain_steps):
            with urllib.request.urlopen(url) as req:
                segments = json.loads(req.read())
            limit = random.randrange(1, len(segments))
            for segment in segments[:limit]:
                id = segment['segmentID']
                url = segment['segmentURL']
                yield url
            url = f"https://play.rivalium.com/api/{stream_id}/{id}"

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
    return urls.map(fetch).map(decodeOggOpus).join()

def send(stream, admin_url=None):
    "Returns stream with side-effect of sending audio to Rivalium stream."
    raise NotImplementedError
    # return (effectful_stream, public_url, admin_url)

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
