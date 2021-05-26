import queue
import sys
import traceback
import types

import mido

from core import *
from midi import *


class StreamManager:
    def __init__(self, finish_callback):
        self.finish_callback = finish_callback
        # Map of stream name -> (stream, paused position, history, history index)
        self.streams = {}
        # Map of stream name -> stream
        self.playing_streams = {}
        # For thread-safety, we only mutate self.playing_streams in one thread.
        # Queue of (name, stream). `stream is None` indicates deletion.
        self.to_change = queue.Queue()
        self.history_length = SAMPLE_RATE * 1
    
    def __call__(self):
        # First, process any queued changes:
        while True:
            try:
                name, stream = self.to_change.get(block=False)
            except queue.Empty:
                break
            if stream:
                self.playing_streams[name] = stream
            elif name in self.playing_streams:
                del self.playing_streams[name]
        acc = 0
        # Not sure if it's better to put the next streams in a new dictionary, or re-use the old one.
        # (Re-use requires keeping track of which entries should be deleted, and doing that afterwards.)
        next_playing_streams = {}
        for name, stream in self.playing_streams.items():
            try:
                result = stream()
                if isinstance(result, Return):
                    self.finish_callback(name, result.value)
                    self.streams[name][1] = self.streams[name][0]
                else:
                    value, next_stream = result
                    next_playing_streams[name] = next_stream
                    # TODO: Devise a less memory-hungry approach here.
                    # A (replayable) stream contains a snapshot of the audio subgraph at that point in the stream,
                    # so saving each stream every sample is very expensive in memory usage.
                    # Instead, we should only save snapshots every N samples, or let the user save specific checkpoints.
                    # Until one of these alternatives is implemented, this feature is temporarily disabled.
                    # history = self.streams[name][2]
                    # history_index = self.streams[name][3]
                    # history[history_index] = next_stream
                    # self.streams[name][3] = (history_index + 1) % self.history_length
                    acc += value
            except Exception as e:
                traceback.print_exc()
                self.finish_callback(name, e)
                self.streams[name][1] = self.streams[name][0]
        self.playing_streams = next_playing_streams
        return (acc, self)
    
    def play(self, name, resource):
        if isinstance(resource, Stream):
            stream = resource
        elif isinstance(resource, types.FunctionType) and resource.metadata.get('instrument'):
            p = mido.open_input(mido.get_input_names()[1])
            stream = resource(input_stream(p))
        else:
            raise ValueError(f"Expected Stream or instrument, got {type(resource)}.")
        if name in self.streams and self.streams[name][0] is stream:
            self.to_change.put((name, self.streams[name][1]))
        else:
            assert(stream is not None)
            # See TODO above.
            # self.streams[name] = [stream, stream, [stream] * self.history_length, 0]
            self.streams[name] = [stream, stream]
            self.to_change.put((name, stream))
    
    def pause(self, name):
        if name not in self.playing_streams:
            print(f'Warning: {name} is not playing, desync with client.', file=sys.stderr)
            return
        self.streams[name][1] = self.playing_streams[name]
        self.to_change.put((name, None))
    
    def record(self, name, instrument):
        # This plays the instrument with live MIDI data, like play(),
        # but it also puts a layer in the middle that captures that MIDI data, for later playback.
        # Right now this creates a stream that plays back the MIDI data with the same instrument,
        # but this should create an object that is visible and editable (as a piano roll),
        # and replayable (using this or any other instrument).

        p = mido.open_input(mido.get_input_names()[1])
        self.list_of_events = []
        timer = 0
        def callback(event):
            nonlocal timer
            if event is not None:
                self.list_of_events.append((timer, event))
            timer += 1
            return event
        def finish():
            print(self.list_of_events)
            global recorded_stream
            recorded_stream = instrument(events_in_time(self.list_of_events))
            return (0, empty)
        # TODO: for now, this just records the next 5 seconds, but it should record until stopped.
        self.play(name, instrument(input_stream(p)[:5.0].map(callback)) >> finish)
        # Note that we could make an /audio-level/ recording instead by memoizing
        # Instead of actually using memoize(), would use callback() to append to an internal list_of_samples.
        # Create a ListStream afterwards.
    
    def stop(self, name):
        if name in self.streams:
            self.streams[name][1] = self.streams[name][0]
            self.to_change.put((name, None))
    
    def rewind(self, name):
        # See TODO above.
        # if name in self.playing_streams:
        #     self.to_change.put((name, self.streams[name][2][(self.streams[name][3] + 1) % self.history_length]))
        # elif name in self.streams:
        #     self.streams[name][1] = self.streams[name][2][(self.streams[name][3] + 1) % self.history_length]
        pass