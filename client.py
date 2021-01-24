import asyncio
import websockets
import json
import types
import pickle

from core import *
from audio import *


# import my_cool_stuff
# register(my_cool_stuff)

# envelope = load("cool-envelope")
# foo = ...
# bar = ...
# composition = foo * envelope + bar ...

def load(resource_name):
    with open(f'resources/{resource_name}.pkl', 'rb') as f:
        return pickle.load(f)

tune_a = osc(440)
tune_b = osc(660)[:1.0] >> osc(880)[:1.0]

def custom_repr(x):
    if x.__class__.__repr__ == types.FunctionType.__repr__:
        return '<function>'
    return repr(x)

def serialize(stream):
    info = stream.inspect()
    info['parameters'] = {n: p if isinstance(p, Stream) else custom_repr(p) for n, p in info['parameters'].items()}
    if 'children' in info:
        info['children']['streams'] = list(map(serialize, info['children']['streams']))
    if 'implementation' in info:
        info['implementation'] = serialize(info['implementation'])
    return info

def get_streams():
    return {name: value for name, value in globals().items() if isinstance(value, Stream)}

async def hello(websocket, path):
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
        print('Refresh')

start_server = websockets.serve(hello, "localhost", 8765)
# await start_server

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
