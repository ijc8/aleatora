import asyncio
import math
import websockets
import json
import types
import cloudpickle as pickle
import os

from core import *
import audio
from speech import *

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

def convert(x):
    if x.__class__.__repr__ == types.FunctionType.__repr__:
        return '<function>'
    return x

# to_bytes = lambda x: x.to_bytes(math.ceil(math.log2(x+1)/8), 'big')
# encode = lambda s: base64.b16encode(to_bytes(s)).decode('utf8')
encode = lambda s: hex(s)[2:]

def serialize(stream):
    seen = set()
    def dfs(stream):
        if stream in seen:
            return {'name': '@' + encode(id(stream))}
        seen.add(stream)
        if not isinstance(stream, Stream):
            # Handle quick lambdas, etc.
            if isinstance(stream, types.FunctionType):
                return {'name': 'raw function'}
            else:
                return {'name': f'not a stream: {type(stream)}'}
        info = stream.inspect()
        info['id'] = encode(id(stream))
        info['parameters'] = {n: dfs(p) if isinstance(p, Stream) else convert(p) for n, p in info['parameters'].items()}
        if 'children' in info:
            info['children']['streams'] = list(map(dfs, info['children']['streams']))
        if 'implementation' in info:
            info['implementation'] = dfs(info['implementation'])
        return info
    return dfs(stream)

def get_stream_tree():
    # BFS with cycle detection
    modules_seen = set()
    variables_seen = set()
    root = {}
    queue = [('__main__', sys.modules['__main__'], None)]
    while queue:
        name, module, parent = queue.pop()
        this = {} if parent else root
        for var_name, value in module.__dict__.items():
            if isinstance(value, Stream) and (var_name, value) not in variables_seen:
                variables_seen.add((var_name, value))
                this[var_name] = var_name  # serialize(stream)
            # Note that we check if this is a module, not isinstance: this excludes CompiledLibs.
            # (Calling __dict__ on the portaudio FFI yields "ffi.error: symbol 'PaMacCore_GetChannelName' not found")
            elif type(value) is types.ModuleType and value not in modules_seen:
                modules_seen.add(value)
                queue.append((var_name, value, this))
        if parent and this:
            parent[name] = this
    return root


def get_streams():
    return {name: value for name, value in globals().items() if isinstance(value, Stream)}

# https://stackoverflow.com/questions/33000200/asyncio-wait-for-event-from-other-thread
class EventThreadSafe(asyncio.Event):
    def set(self):
        self._loop.call_soon_threadsafe(super().set)

class StreamManager:
    def __init__(self, finish_callback):
        self.finish_callback = finish_callback
        # Map of stream name -> (stream, paused position)
        self.streams = {}
        # Map of stream name -> stream
        self.playing_streams = {}
        self.history_length = SAMPLE_RATE * 1
    
    def __call__(self):
        acc = 0
        to_remove = set()
        for name, stream in self.playing_streams.items():
            try:
                result = stream()
                if isinstance(result, Return):
                    self.finish_callback(name, result.value)
                    to_remove.add(name)
                else:
                    value, next_stream = result
                    self.playing_streams[name] = next_stream
                    history = self.streams[name][2]
                    history_index = self.streams[name][3]
                    history[history_index] = next_stream
                    self.streams[name][3] = (history_index + 1) % self.history_length
                    acc += value
            except Exception as e:
                traceback.print_exc()
                self.finish_callback(name, e)
                to_remove.add(name)
        for name in to_remove:
            self.streams[name][1] = self.streams[name][0]
            del self.playing_streams[name]
        return (acc, self)
    
    def play(self, name, stream):
        if name in self.streams and self.streams[name][0] is stream:
            self.playing_streams[name] = self.streams[name][1]
        else:
            assert(stream is not None)
            self.streams[name] = [stream, stream, [stream] * self.history_length, 0]
            self.playing_streams[name] = stream
    
    def pause(self, name):
        if name not in self.playing_streams:
            print(f'Warning: {name} is not playing, desync with client.', file=sys.stderr)
            return
        self.streams[name][1] = self.playing_streams[name]
        del self.playing_streams[name]
    
    def stop(self, name):
        if name in self.streams:
            self.streams[name][1] = self.streams[name][0]
            if name in self.playing_streams:
                del self.playing_streams[name]
    
    def rewind(self, name):
        if name in self.playing_streams:
            self.playing_streams[name] = self.streams[name][2][(self.streams[name][3] + 1) % self.history_length]
        else:
            self.streams[name][1] = self.streams[name][2][(self.streams[name][3] + 1) % self.history_length]




async def serve(websocket, path):
    finished_event = EventThreadSafe()
    finished = []
    def finish_callback(name, result):
        finished.append(name)
        finished_event.set()

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
        streams = get_streams()
        dump = {"type": "streams", "streams": {name: serialize(stream) for name, stream in streams.items()}, "tree": get_stream_tree()}
        blob = json.dumps(dump)
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
                manager.play(name, streams[name])
            elif cmd == 'pause':
                manager.pause(data['name'])
            elif cmd == 'stop':
                manager.stop(data['name'])
            elif cmd == 'rewind':
                manager.rewind(data['name'])
            elif cmd == 'save':
                resource = type_map[data['type']](data['payload'])
                resource_name = resource_map.get(streams.get(data['name'], None), data['name'])
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
