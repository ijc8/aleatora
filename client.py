import asyncio
import websockets
import json

from core import *
from audio import *


# import my_cool_stuff
# register(my_cool_stuff)

# envelope = load("cool-envelope")
# foo = ...
# bar = ...
# composition = foo * envelope + bar ...


tune_a = osc(440)
tune_b = osc(660)

def get_streams():
    return {name: value for name, value in globals().items() if isinstance(value, Stream)}

async def hello(websocket, path):
    while True:
        # Send list of streams.
        streams = get_streams()
        await websocket.send(json.dumps(list(streams.keys())))
        while True:
            name = await websocket.recv()
            # Hack
            if name == 'refresh':
                break
            print(f"Play {name}")
            play(streams[name])
        print('Refresh')

start_server = websockets.serve(hello, "localhost", 8765)
# await start_server

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
