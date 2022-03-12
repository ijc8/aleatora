import asyncio
import collections
import json
import threading
import sys
import websockets

from .streams import stream, Stream

Text = collections.namedtuple('Text', [])
Number = collections.namedtuple('Number', [])
History = collections.namedtuple('History', [])
Slider = collections.namedtuple('Slider', ['min', 'max'], defaults=(-1, 1))

Widget = collections.namedtuple('Widget', ['type', 'direction'])

class Widgets:
    def __init__(self):
        self.updates = {}
        self.widgets = {}
        self.sources = {}

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(websockets.serve(self.serve, "localhost", 8765))
        loop.run_forever()

    def play(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    async def send(self, websocket):
        widgets = {}
        while True:
            if self.widgets != widgets:
                widgets = self.widgets.copy()
                payload = {}
                for k, widget in widgets.items():
                    payload[k] = {
                        "type": type(widget.type).__name__,
                        "direction": widget.direction,
                        "args": widget.type._asdict(),
                    }
                await websocket.send(json.dumps({"type": "widgets", "payload": payload}))
            if self.updates:
                await websocket.send(json.dumps({"type": "updates", "payload": self.updates}))
                self.updates.clear()
            await asyncio.sleep(0.01)
    
    async def recv(self, websocket):
        while True:
            try:
                updates = json.loads(await websocket.recv())
            except (websockets.exceptions.ConnectionClosedOK, websockets.exceptions.ConnectionClosedError):
                return
            for key, value in updates.items():
                self.sources[key] = value

    async def serve(self, websocket, path):
        print("Websocket connection: start", file=sys.stderr)
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
    def log(self, stream, period=1, key=None, type=Slider()):
        key = key or repr(stream)
        self.widgets[key] = Widget(type, "sink")
        for i, x in enumerate(stream):
            if i % period == 0:
                self.updates[key] = x
            yield x
    
    @stream
    def get(self, key=None, type=None):
        type = type or Slider()
        key = key or repr(type) + " @ " + hex(id(type))
        self.widgets[key] = Widget(type, "source")
        # TODO: Avoid busy loop waiting for first change.
        # Instead, have sensible default values for inputs.
        while True:
            if key in self.sources:
                yield self.sources[key]
    
    def clear(self):
        self.updates = {}
        self.widgets = {}
        self.sources = {}

# Unpredictable deletion, at least in PyPy.
# class LogStreamIter:
#     def __init__(self, iter):
#         self.iter = iter

#     def __next__(self):
#         return next(self.iter)
    
#     def __iter__(self):
#         return self
    
#     def __del__(self):
#         print("Bye!")

# class LogStream(Stream):
#     def __init__(self, stream):
#         self.stream = stream

#     def __iter__(self):
#         return LogStreamIter(iter(self.stream))
