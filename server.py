import http.server
import socketserver
import wave
import io
import core
import math
import numpy as np
from phase import piano_phase

PORT = 8000
CHUNK_SIZE = 8192

def gen(freq):
    phase = 0
    while True:
        yield math.sin(phase)
        phase += 2*math.pi*freq/core.SAMPLE_RATE

def chunk_gen(gen):
    buf = np.empty(CHUNK_SIZE, dtype=np.int16)
    while True:
        buf[:] = 0
        for i, sample in zip(range(CHUNK_SIZE), gen):
            buf[i] = round(sample * (2**15-1))
        yield buf
        if i < CHUNK_SIZE - 1:
            break

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        if self.path == '/':
            content = b'<audio controls src="/audio.wav?foo=bar" preload="none">'
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path.startswith('/audio.wav'):
            self.send_response(200)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()

            f = io.BytesIO()
            w = wave.open(f, 'wb')
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(core.SAMPLE_RATE)
            # Hack to get wave data length set near max in header
            w.setnframes((0xffffffff - 36)//2)
            total = 0
            for data in chunk_gen(iter(piano_phase)):
                w.writeframesraw(data)
                chunk = f.getvalue()
                if not chunk:
                    continue
                tosend = b'%X\r\n%s\r\n' % (len(chunk), chunk)
                self.wfile.write(tosend)
                self.wfile.flush()
                total += len(tosend)
                print(total)
                f.truncate(0)
                f.seek(0)
            self.wfile.write('0\r\n\r\n')
        else:
            self.send_response(404)
            self.end_headers()

socketserver.ForkingTCPServer.allow_reuse_address = True
with socketserver.ForkingTCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()