import asyncio
import collections
import json
import threading
import sys
import websockets

from .streams import stream

# import psutil
# @stream
# def resource_usage():
#     process = psutil.Process()
#     while True:
#         yield process.cpu_percent(), process.memory_info().rss/(1024**2)

Textbox = collections.namedtuple('Textbox', [])
Slider = collections.namedtuple('Slider', ['min', 'max'])

class Widgets:
    def __init__(self):
        self.updates = {}
        self.recv_streams = {}

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(websockets.serve(self.serve, "localhost", 8765))
        loop.run_forever()
        # asyncio.create_task(main())
        # asyncio.get_event_loop().run_forever()

    def play(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    async def send(self, websocket):
        while True:
            if self.updates:
                await websocket.send(json.dumps(self.updates))
                self.updates.clear()
            await asyncio.sleep(0.01)
    
    async def recv(self, websocket):
        while True:
            try:
                updates = json.loads(await websocket.recv())
            except websockets.exceptions.ConnectionClosedOK:
                return
            for key, value in updates:
                self.recv_streams[key].value = value

    async def serve(self, websocket, path):
        print("Websocket connection: start", file=sys.stderr)
        # await asyncio.gather(self.send(websocket), self.recv(websocket))
        # await websocket.recv()
        consumer_task = asyncio.create_task(self.recv(websocket))
        producer_task = asyncio.create_task(self.send(websocket))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        print("Websocket connection: stop", file=sys.stderr)

    @stream
    def log(self, stream, period=1, key=None, type=Textbox()):
        key = key or repr(stream)
        for i, x in enumerate(stream):
            if i % period == 0:
                self.updates[key] = x
            yield x
