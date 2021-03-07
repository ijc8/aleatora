import asyncio
import math
import inspect
import json
import types
import os

import cloudpickle as pickle
import websockets

from core import *
import audio
from speech import *
from midi import *
from manager import *


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
        if id(resource) in seen:
            return {'name': '@' + encode(id(resource))}
        seen.add(id(resource))
        if isinstance(resource, Stream):
            stream = resource
            info = stream.inspect()
            info['type'] = 'stream'
            info['id'] = encode(id(stream))
            info['parameters'] = {n: dfs(p) if isinstance(p, Stream) else p for n, p in info['parameters'].items()}
            if 'children' in info:
                info['children']['streams'] = [dfs(child) for child in info['children']['streams']]
            if 'implementation' in info:
                info['implementation'] = dfs(info['implementation'])
            return info
        elif isinstance(resource, types.FunctionType):
            # May be a quick wrapper lambda, or generally an 'un-Streamified' stream function.
            # Since we got here from seeing it embedded in a stream, we'll go ahead and assume it's also a stream.
            return {'type': 'stream', 'name': 'raw function'}
        else:
            assert(False)
    if isinstance(resource, Stream):
        return dfs(resource)
    elif isinstance(resource, types.FunctionType):
        # Something registered; a stream-creating function (including instruments).
        # TODO: docstring, signature
        return {'type': 'function', 'name': resource.__qualname__, 'doc': resource.__doc__, 'signature': str(inspect.signature(resource)), **resource.metadata}
    else:
        assert(False)
        
    return dfs(resource)

def get_resources():
    # Collect the resources within each module.
    modules_seen = set()
    variables_seen = set()
    # NOTE: We traverse `core` first (so it gets to claim core streams like `silence`, despite other modules doing `from core import *`),
    # but we put `__main__` in `resources` first so that it gets listed first.
    resources = {'__main__': {}}
    queue = [('__main__', sys.modules['__main__']), ('core', sys.modules['core'])]
    while queue:
        module_name, module = queue.pop()
        if module_name in core.stream_registry:
            for var_name, value in core.stream_registry[module_name].items():
                if value.__module__ not in resources:
                    resources[value.__module__] = {}
                resources[value.__module__][var_name] = value
        for var_name, value in module.__dict__.items():
            if isinstance(value, Stream):
                if (var_name, value) not in variables_seen:
                    variables_seen.add((var_name, value))
                    if module_name not in resources:
                        resources[module_name] = {}
                    resources[module_name][var_name] = value
            # Note that we check if this is a module, not isinstance: this excludes CompiledLibs.
            # (Calling __dict__ on the portaudio FFI yields "ffi.error: symbol 'PaMacCore_GetChannelName' not found")
            elif type(value) is types.ModuleType and value not in modules_seen:
                modules_seen.add(value)
                queue.append((var_name, value))
    return resources

# https://stackoverflow.com/questions/33000200/asyncio-wait-for-event-from-other-thread
class EventThreadSafe(asyncio.Event):
    def set(self):
        self._loop.call_soon_threadsafe(super().set)

def play(stream=None):
    if stream:
        manager.play(None, stream)
    else:
        manager.stop(None)

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
        resources = get_resources()
        def get_resource(name):
            module, name = name.split(".", 1)
            return resources[module][name]

        serialized_resources = {module: {variable: serialize(value) for variable, value in module_contents.items()} for module, module_contents in resources.items()}
        dump = {"type": "resources", "resources": serialized_resources}
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
                manager.play(name, get_resource(name))
            elif cmd == 'pause':
                manager.pause(data['name'])
            elif cmd == 'record':
                name = data['name']
                manager.record(name, get_resource(name))
            elif cmd == 'stop':
                manager.stop(data['name'])
            elif cmd == 'rewind':
                manager.rewind(data['name'])
            elif cmd == 'save':
                resource = type_map[data['type']](data['payload'])
                resource_name = resource_map.get(get_resource(name), data['name'])
                globals()[data['name']] = resource
                save(resource, resource_name)
                break
            elif cmd == 'exec':
                with stdIO() as s:
                    try:
                        code = compile(data['code'], '<assistant>', data['mode'])
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
