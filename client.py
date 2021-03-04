import asyncio
import math
import websockets
import json
import types
import cloudpickle as pickle
import os
import queue

from core import *
import audio
from speech import *
from midi import *


# Based on https://stackoverflow.com/questions/3906232/python-get-the-print-output-in-an-exec-statement
import sys
from io import StringIO
import contextlib
import traceback

@contextlib.contextmanager
def stdIO():
    old = sys.stdin, sys.stdout, sys.stderr
    sys.stdin = StringIO()
    sys.stdout = StringIO()
    sys.stderr = sys.stdout
    yield sys.stdout
    sys.stdin, sys.stdout, sys.stderr = old

# Example with changing envelope live:
# test = osc(660)[:1.0] * Stream(lambda: my_cool_envelope())
# more = cycle(Stream(lambda: test()))
# Can now edit and save envelope and hear changes immediately in loop.

# import my_cool_stuff
# register(my_cool_stuff)

# envelope = load("cool-envelope")
# foo = ...
# bar = ...
# composition = foo * envelope + bar ...

# class Envelope(Stream):
#     def __init__(self, points, time=0, prev_time=None, prev_value=None, next_time=0, next_value=None):
#         self.points = points
#         self.time = time
#         self.prev_time = prev_time
#         self.prev_value = prev_value
#         self.next_time = next_time
#         self.next_value = next_value
    
#     def __call__(self):
#         points = self.points
#         time = self.time
#         prev_time = self.prev_time
#         prev_value = self.prev_value
#         next_time = self.next_time
#         next_value = self.next_value
#         time += 1
#         while time >= next_time:
#             if not points:
#                 return Return()
#             prev_time, prev_value = next_time, next_value
#             (next_time, next_value), *points = points
#             next_time = convert_time(next_time)
#         interpolated = (next_value - prev_value) * (time - prev_time)/(next_time-prev_time) + prev_value
#         return (interpolated, Envelope(stream, time, prev_time, prev_value, next_time, next_value))

# or just...
class Envelope(Stream):
    def __init__(self, points):
        self.points = points
    
    def __call__(self):
        return interp(self.points)()
    
    def __str__(self):
        return "Envelope(...)"
    
    def inspect(self):
        return {
            "name": "envelope",
            "parameters": {"points": self.points}
        }

# Somewhere between basic_sequencer and the MIDI instruments.
def better_sequencer(notes, bpm=120):
    print('Notes:', notes)
    arrangement = []
    for (start, length, pitch) in notes:
        start *= 60 / bpm
        length *= 60 / bpm
        stream = osc(m2f(pitch)) * basic_envelope(length)
        arrangement.append((start, None, stream))
    print('Arranged:', arrangement)
    return arrange(arrangement)

class Sequence(Stream):
    def __init__(self, notes):
        print('SNotes:', notes)
        self.notes = notes
    
    def __call__(self):
        return better_sequencer(self.notes)()
    
    def __str__(self):
        return "Sequence(...)"
    
    def inspect(self):
        return {
            "name": "sequence",
            "parameters": {"notes": self.notes}
        }


# Map resources to their names.
# This way, we can save back to the correct location, even if the user renamed the resource.
resource_map = {}

def make_envelope(points):
    return Envelope([(p['x'], p['y']) for p in points])

def make_sequence(notes):
    return Sequence([(n['t'], n['g'], n['n']) for n in notes])

type_map = {'envelope': make_envelope, 'sequence': make_sequence, 'speech': speech}


def load(resource_name):
    with open(f'resources/{resource_name}.pkl', 'rb') as f:
        resource = pickle.load(f)
        resource_map[resource] = resource_name
        return resource

def save(resource, resource_name):
    if not os.path.isdir('resources'):
        os.mkdir('resources')
    with open(f'resources/{resource_name}.pkl', 'wb') as f:
        pickle.dump(resource, f)

tune_a = osc(440)
tune_b = osc(660)[:1.0] >> osc(880)[:1.0]
my_cool_envelope = load("my_cool_envelope")
import wav
my_cool_sound = to_stream(wav.load_mono('samples/a.wav'))

my_cool_seq = load("my_cool_seq")
my_cool_speech = load("my_cool_speech")

class MyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, types.FunctionType):
            return '<function>'
        return o.__dict__

# to_bytes = lambda x: x.to_bytes(math.ceil(math.log2(x+1)/8), 'big')
# encode = lambda s: base64.b16encode(to_bytes(s)).decode('utf8')
encode = lambda s: hex(s)[2:]

def serialize(resource):
    seen = set()
    def dfs(resource):
        if resource in seen:
            return {'name': '@' + encode(id(resource))}
        seen.add(resource)
        if isinstance(resource, Stream):
            stream = resource
            info = stream.inspect()
            info['type'] = 'stream'
            info['id'] = encode(id(stream))
            info['parameters'] = {n: dfs(p) if isinstance(p, Stream) else p for n, p in info['parameters'].items()}
            if 'children' in info:
                info['children']['streams'] = list(map(dfs, info['children']['streams']))
            if 'implementation' in info:
                info['implementation'] = dfs(info['implementation'])
            return info
        elif isinstance(resource, Instrument):
            return {'type': 'instrument', 'name': resource.name}
        elif isinstance(resource, types.FunctionType):
            # May be a quick wrapper lambda, or generally an 'un-Streamified' stream function.
            # Since we got here from seeing it embedded in a stream, we'll go ahead and assume it's also a stream.
            return {'type': 'stream', 'name': 'raw function'}
        else:
            # Probably an error, if this is embedded where a stream is expected...
            return {'type': 'unknown', 'name': f'mystery object: {type(resource)}'}
        
    return dfs(resource)

def get_resources():
    # Collect the resources within each module.
    modules_seen = set()
    variables_seen = set()
    resources = {}
    queue = [('__main__', sys.modules['__main__'])]
    while queue:
        name, module = queue.pop()
        if name in core.stream_registry:
            for var_name, value in core.stream_registry[name].items():
                if value.__module__ not in resources:
                    resources[value.__module__] = {}
                resources[value.__module__][var_name] = "TODO fn"
        for var_name, value in module.__dict__.items():
            if isinstance(value, Stream):
                if value.__module__ not in resources:
                    resources[value.__module__] = {}
                resources[value.__module__][var_name] = "TODO stream"  # serialize(stream)
            elif isinstance(value, Instrument):
                if value.__module__ not in resources:
                    resources[value.__module__] = {}
                resources[value.__module__][var_name] = "TODO instrument"
            # Note that we check if this is a module, not isinstance: this excludes CompiledLibs.
            # (Calling __dict__ on the portaudio FFI yields "ffi.error: symbol 'PaMacCore_GetChannelName' not found")
            elif type(value) is types.ModuleType and value not in modules_seen:
                modules_seen.add(value)
                queue.append((var_name, value))
    return resources


def get_resources_old():
    return {name: value for name, value in globals().items() if isinstance(value, Stream) or isinstance(value, Instrument)}

# https://stackoverflow.com/questions/33000200/asyncio-wait-for-event-from-other-thread
class EventThreadSafe(asyncio.Event):
    def set(self):
        self._loop.call_soon_threadsafe(super().set)

def play(stream=None):
    if stream:
        manager.play(None, stream)
    else:
        manager.stop(None)

class StreamManager:
    def __init__(self, finish_callback):
        self.finish_callback = finish_callback
        # Map of stream name -> (stream, paused position)
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
                    history = self.streams[name][2]
                    history_index = self.streams[name][3]
                    history[history_index] = next_stream
                    self.streams[name][3] = (history_index + 1) % self.history_length
                    acc += value
            except Exception as e:
                traceback.print_exc()
                self.finish_callback(name, e)
                self.streams[name][1] = self.streams[name][0]
        self.playing_streams = next_playing_streams
        return (acc, self)
    
    def play(self, name, stream):
        # TODO: rename stream -> resource
        if isinstance(stream, Stream):
            stream = stream
        elif isinstance(stream, Instrument):
            p = mido.open_input(mido.get_input_names()[1])
            stream = stream(event_stream(p))
        else:
            raise ValueError(f"Expected Stream or Instrument, got {type(stream)}.")
        if name in self.streams and self.streams[name][0] is stream:
            self.to_change.put((name, self.streams[name][1]))
        else:
            assert(stream is not None)
            self.streams[name] = [stream, stream, [stream] * self.history_length, 0]
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
        self.play(name, instrument(event_stream(p)[:5.0].map(callback)) >> finish)
        # Note that we could make an /audio-level/ recording instead by memoizing
        # Instead of actually using memoize(), would use callback() to append to an internal list_of_samples.
        # Create a ListStream afterwards.
    
    def stop(self, name):
        if name in self.streams:
            self.streams[name][1] = self.streams[name][0]
            self.to_change.put((name, None))
    
    def rewind(self, name):
        if name in self.playing_streams:
            self.to_change.put((name, self.streams[name][2][(self.streams[name][3] + 1) % self.history_length]))
        elif name in self.streams:
            self.streams[name][1] = self.streams[name][2][(self.streams[name][3] + 1) % self.history_length]




async def serve(websocket, path):
    finished_event = EventThreadSafe()
    finished = []
    def finish_callback(name, result):
        finished.append(name)
        finished_event.set()

    global manager
    manager = StreamManager(finish_callback)
    audio.play(manager)

    async def wait_for_finish():
        while True:
            await finished_event.wait()
            finished_event.clear()
            while finished:
                await websocket.send(json.dumps({"type": "finish", "name": finished.pop()}))

    asyncio.ensure_future(wait_for_finish())

    while True:
        # Send list of streams.
        # TODO: only refresh if streams changed
        resources = get_resources_old()
        dump = {"type": "resources", "resources_old": {name: serialize(resource) for name, resource in resources.items()}, "resources": get_resources()}
        blob = json.dumps(dump, cls=MyEncoder)
        await websocket.send(blob)
        while True:
            data = json.loads(await websocket.recv())
            print(data)
            cmd = data['cmd']
            if cmd == 'refresh':
                break
            elif cmd == 'play': 
                name = data['name']
                playing_stream = name
                manager.play(name, resources[name])
            elif cmd == 'pause':
                manager.pause(data['name'])
            elif cmd == 'record':
                name = data['name']
                manager.record(name, resources[name])
            elif cmd == 'stop':
                manager.stop(data['name'])
            elif cmd == 'rewind':
                manager.rewind(data['name'])
            elif cmd == 'save':
                resource = type_map[data['type']](data['payload'])
                resource_name = resource_map.get(resources.get(data['name'], None), data['name'])
                globals()[data['name']] = resource
                save(resource, resource_name)
                break
            elif cmd == 'exec':
                with stdIO() as s:
                    try:
                        code = compile(data['code'], '<assistant>', 'single')
                        exec(code, globals=globals())
                    except:
                        traceback.print_exc()
                print("result:", s.getvalue())
                await websocket.send(json.dumps({"type": "output", "output": s.getvalue()}))
                break
            elif cmd == 'volume':
                audio.volume(data['volume'])
        print('Refresh')

start_server = websockets.serve(serve, "localhost", 8765)
# await start_server

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
