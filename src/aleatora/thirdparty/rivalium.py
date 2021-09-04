import json
import tempfile
import urllib.request

import numpy as np
import pyogg

from .. import streams

opus_file = pyogg.OpusFile("/home/ian/Downloads/00000026.ogx")

def opus_to_array(opus_file, resample=True):
    data = np.ctypeslib.as_array(opus_file.buffer, (opus_file.buffer_length // 2,)) / np.iinfo(np.int16).max
    if resample and opus_file.frequency != streams.SAMPLE_RATE:
        new_length = int(streams.SAMPLE_RATE / opus_file.frequency * len(data))
        x = np.arange(len(data)) / opus_file.frequency
        new_x = np.arange(new_length) / streams.SAMPLE_RATE
        data = np.interp(new_x, x, data)
    return data

# Issues:
# - Does PyOgg skip pre-skip?
# - Extra leading '0' in rvm.sh link? rvm.sh/04hb496kn6yh -> 4hb496kn6yh
# - Can't create an OpusFile from memory... have to save to temporary file.

# https://play.rivalium.com/api/4hb496kn6yh/00000026
# https://play.rivalium.com/audio/4hb496kn6yh/00000026.opus


from aleatora import *
import random

@stream
def recv_urls(stream_id):
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

# Random
def recv(stream_id):
    urls = recv_urls(stream_id)
    return urls.map(fetchOpus).join()

def recv(stream_url):
    # Be accomodating, accept various formats:
    # - rvm.sh/Xabcdef
    # - play.rivalium.com/{api,group}/abcdef
    # - abcdef
    ...

def recv_group(group_id):
    ...

def fetchOpus(url):
    with urllib.request.urlopen(url) as req:
        contents = req.read()
    with tempfile.NamedTemporaryFile(mode='wb') as tmp:
        tmp.write(contents)
        tmp.flush()
        opus_file = pyogg.OpusFile(tmp.name)
    return stream(opus_to_array(opus_file).tolist())

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
        ...
        self.remove_keys = {}
    
    def add(self, stream_id):
        ...
        self.remove_keys[stream_id] = remove_key
    
    def remove(self, stream_id):
        ...
        delete_request(..., self.remove_keys[stream_id])


sick_beat_A_with_effect, public_url, admin_url = send(sick_beat_A)
play(sick_beat_A_with_effect)
play()

calm_beat_B = ...
play(send(calm_beat_B, admin_url)[0])


def send(stream, admin_url): -> (stream, admin_url, public_url)


def add_stream_to_collection(collection, public_url):
    ...
    return id



# Expected: 1 sec + 80 ms segments
# Drop first 80ms
# Find indices of first & last zero-crossings: crop buffer to region between them
# For getting streams: Follow sortition redirect
# Playback mode as part of query. Query preserved in sortition redirect.
# Normal & live mode: request next segments from server
# Random: up to 10 files at a time from sludge.

# Randomly plays the first N segments returned from API.
#   Random number of iterations for request loop (e.g. 3-10):
#     Then, takes last-played segment and asks for the following segments.
