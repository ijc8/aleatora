import asyncio
import websockets
import json
import types
import pickle
import os

from core import *
from audio import *


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
my_cool_envelope = load("my_cool_envelope")

def custom_serialize(x):
    if x.__class__.__repr__ == types.FunctionType.__repr__:
        return '<function>'
    return x

def serialize(stream):
    info = stream.inspect()
    info['parameters'] = {n: p if isinstance(p, Stream) else custom_serialize(p) for n, p in info['parameters'].items()}
    if 'children' in info:
        info['children']['streams'] = list(map(serialize, info['children']['streams']))
    if 'implementation' in info:
        info['implementation'] = serialize(info['implementation'])
    return info

def get_streams():
    return {name: value for name, value in globals().items() if isinstance(value, Stream)}

async def serve(websocket, path):
    while True:
        # Send list of streams.
        streams = get_streams()
        blob = json.dumps({name: serialize(stream) for name, stream in streams.items()})
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
        print('Refresh')

start_server = websockets.serve(serve, "localhost", 8765)
# await start_server

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
