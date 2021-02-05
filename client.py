import asyncio
import websockets
import json
import types
import pickle
from pprint import pprint
import os

from core import *
from audio import *

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


# Map resources to their names.
# This way, we can save back to the correct location, even if the user renamed the resource.
resource_map = {}

def make_envelope(points):
    return Envelope([(p['x'], p['y']) for p in points])

type_map = {'envelope': make_envelope}


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
# my_cool_envelope = load("my_cool_envelope")
import wav
my_cool_sound = list_to_stream(wav.load_mono('samples/a.wav'))

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
            return {'name': '@' + encode(id(stream)), 'parameters': []}
        seen.add(stream)
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
    seen = set()
    root = {}
    queue = [('__main__', sys.modules['__main__'], None)]
    while queue:
        name, module, parent = queue.pop()
        # print(name, module)
        this = {} if parent else root
        for var_name, value in module.__dict__.items():
            # print(' ', name, type(value))
            if isinstance(value, Stream) and value not in seen:
                seen.add(value)
                this[var_name] = var_name  # serialize(stream)
            # Note that we check if this is a module, not isinstance: this excludes CompiledLibs.
            # (Calling __dict__ on the portaudio FFI yields "ffi.error: symbol 'PaMacCore_GetChannelName' not found")
            elif type(value) is types.ModuleType and value not in seen:
                seen.add(value)
                queue.append((var_name, value, this))
        if parent and this:
            parent[name] = this
    return root


def get_streams():
    return {name: value for name, value in globals().items() if isinstance(value, Stream)}

async def serve(websocket, path):
    while True:
        # Send list of streams.
        # TODO: only refresh if streams changed
        streams = get_streams()
        # pprint({name: serialize(stream) for name, stream in streams.items()})
        blob = json.dumps({"type": "streams", "streams": {name: serialize(stream) for name, stream in streams.items()}, "tree": get_stream_tree()})
        print(blob)
        await websocket.send(blob)
        while True:
            data = json.loads(await websocket.recv())
            cmd = data['cmd']
            if cmd == 'refresh':
                break
            elif cmd == 'play': 
                name = data['name']
                print(f"Play {name}")
                play(streams[name])
            elif cmd == 'save':
                print('save', data)
                resource = type_map[data['type']](data['payload'])
                resource_name = resource_map.get(streams.get(data['name'], None), data['name'])
                globals()[data['name']] = resource
                save(resource, resource_name)
            elif cmd == 'exec':
                print('code', data['code'])
                with stdIO() as s:
                    try:
                        code = compile(data['code'], '<assistant>', 'single')
                        exec(code, globals=globals())
                    except:
                        traceback.print_exc()
                print("result:", s.getvalue())
                await websocket.send(json.dumps({"type": "output", "output": s.getvalue()}))
                break
        print('Refresh')

start_server = websockets.serve(serve, "localhost", 8765)
# await start_server

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
