# from graphviz import Digraph
from pprint import pprint
from core import *
import matplotlib.pyplot as plt

def traverse(stream):
    seen = {}
    cycles = {}
    def dfs(stream):
        if stream in seen:
            result = ['cycle!']
            if stream not in cycles:
                cycles[stream] = []
            cycles[stream].append(result)
            return result
        seen[stream] = None
        count = len(seen)
        if isinstance(stream, ConcatStream):
            result = ['Concat', [dfs(s) for s in stream.streams]]
        elif isinstance(stream, MixStream):
            result = ['Mix', [dfs(s) for s in stream.streams]]
        elif isinstance(stream, MapStream):
            result = ['Map', stream.fn, dfs(stream.stream)]
        elif isinstance(stream, ZipStream):
            result = ['Zip', [dfs(s) for s in stream.streams]]
        elif isinstance(stream, SliceStream):
            result = ['Slice', slice(stream.start, stream.stop, stream.step), dfs(stream.stream)]
        elif isinstance(stream, NamedStream):
            result = ['Name', stream.name]
        else:
            result = ['Stream']
        result[0] += ' ' + str(count)
        seen[stream] = result
        return result
    tree = dfs(stream)
    next_name = 0
    for stream, occurences in cycles.items():
        if isinstance(seen[stream], int):
            name = seen[stream][0]
        else:
            name = next_name
            next_name += 1
            seen[stream].insert(0, name)
        for occurence in occurences:
            occurence.append(name)
    return tree


def text_graph(stream):
    lines = []
    markers = {}
    def dfs(node, row, col):
        nonlocal lines
        marker = None
        if row >= len(lines):
            lines += [''] * (row - len(lines) + 1)
        if col > len(lines[row]):
            lines[row] += ' ' * (col - len(lines[row]))
        if isinstance(node[0], int):
            marker = node[0]
            markers[marker] = node[1]
            node.pop(0)
        stype = node[0].split()[0]
        name = stype
        if stype == 'Name':
            name = node[1]
        if marker is not None:
            name = f'{marker}:{name}'
        if stype in ['Stream', 'Name']:
            lines[row] += name
            width, height = len(name), 1
        elif stype == 'Concat':
            width = len(name) + 2
            lines[row] += name + ' {'
            height = 1
            for child in node[1][:-1]:
                w, h = dfs(child, row, col + width)
                height = max(height, h)
                lines[row] += ' >> '
                width += w + 4
            w, h = dfs(node[1][-1], row, col + width)
            height = max(height, h)
            lines[row] += '}'
            width += w + 1
        elif stype in ('Mix', 'Zip'):
            init_width = len(name) + 2
            width = init_width
            lines[row] += name + ': '
            height = 0
            for child in node[1]:
                w, h = dfs(child, row + height, col + init_width)
                width = max(width, init_width + w)
                height += h
            height = max(height, 1)
        elif stype in ('Map', 'Slice'):
            lines[row] += name + ' ['
            width = len(name) + 2
            w, h = dfs(node[2], row, col + width)
            width += w + 1
            lines[row] += ']'
            height = h
        elif stype == 'cycle!':
            text = f'Ref:{node[1]}'
            lines[row] += text
            return (len(text), 1)
        return width, height
    dfs(traverse(stream), 0, 0)
    print('\n'.join(lines))
    return lines


def graph(stream):
    root = Digraph()  # (engine='fdp')
    markers = {}
    # root.attr(compound='true')
    dummies = 0
    def dfs(node, graph):
        nonlocal dummies
        if isinstance(node[0], int):
            markers[node[0]] = node[1]
            node.pop(0)
        name = node[0]
        if node[0].startswith('Stream'):
            graph.node(node[0], shape='record')
        elif any(node[0].startswith(s) for s in ('Map', 'Slice')):
            sub = Digraph(name=f"cluster {node[0]}")
            sub.attr(label=node[0])
            name = f'dummy {dummies}'
            dummies += 1
            sub.node(name, style='invis')
            sub.edge(name, dfs(node[2], sub), style='invis')
            graph.subgraph(sub)
        elif any(node[0].startswith(s) for s in ('Concat', 'Mix', 'Zip')):
            sub = Digraph(name=f"cluster {node[0]}")
            sub.attr(rankdir='LR' if node[0].startswith('Concat') else 'TB')
            sub.attr(label=node[0])
            name = f'dummy {dummies}'
            dummies += 1
            sub.node(name, style='invis')
            print('going in', len(node[1]))
            last = name
            for child in node[1]:
                cur = dfs(child, sub)
                if last:
                    sub.edge(last, cur, style='invis')
                last = cur
            graph.subgraph(sub)
        elif node[0] == 'cycle!':
            print('skipping cycle for now')
            name = str(id(node))
        return name
    dfs(traverse(stream), root)
    root.render(view=True)
    return root

import html

def to_html(obj, seen=frozenset()):
    if obj in seen:
        # TODO: point back to first occurence
        return "<p>cycle!</p>"
    seen = seen | {obj}
    if isinstance(obj, Stream):
        info = obj.inspect()
        params = ''.join(f"<li>{name} = {to_html(value, seen)}</li>" for name, value in info['parameters'].items())
        if params:
            params = f"<h2>Parameters:</h2><ul>{params}</ul>"
        children = ''
        if 'children' in info:
            direction = info['children']['direction']
            streams = info['children']['streams']
            separator = f"<span>{html.escape(info['children']['separator'])}</span>"
            children = f'<div class="{direction}">{separator.join(to_html(stream, seen) for stream in streams)}</div>'
        implementation = ''
        print(info)
        if 'implementation' in info:
            implementation = f'<p>Implementation <button onclick="expand(this, \'implementation\')">+</button></p><div class="implementation">{to_html(info["implementation"])}</div>'
        details = params + children + implementation
        name = info['name']
        if details:
            details = f'<div class="details">{details}</div>'
            name += ' <button onclick="expand(this, \'details\')">+</button>'
        return f'<div class="node"><h1>{name}</h1>{details}</div>'
    elif isinstance(obj, tuple):
        lst = ''.join(f"<li>{to_html(value, seen)}</li>" for value in obj)
        return f"<ul>{lst}</ul>"
    elif isinstance(obj, list):
        return "[list]"
    else:
        return html.escape(str(obj))

# Not really related to the above functions, but on the general theme of visualizing:
def plot(stream):
    plt.plot(list(stream))
    plt.show(block=False)

def plot_spectrum(stream):
    samples = list(stream)
    x = SAMPLE_RATE * np.arange(np.ceil((len(samples)+1)/2))/len(samples)
    print(len(samples), len(x), len(np.fft.fft(samples)), len(np.fft.rfft(samples)))
    plt.plot(x, np.abs(np.fft.rfft(samples)))
    plt.show(block=False)


# Experimental work on an inspector server.
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

PORT = 7004
HOST = '127.0.0.1'
SERVER_ADDRESS = '{host}:{port}'.format(host=HOST, port=PORT)
FULL_SERVER_ADDRESS = 'http://' + SERVER_ADDRESS

server_content = "Hello!"

class HTTPServerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""

        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(server_content.encode('utf8'))
        elif self.path == '/style.css':
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            with open('style.css', 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/assistant.js':
            self.send_response(200)
            self.send_header('Content-type', 'text/javascript')
            self.end_headers()
            with open('assistant.js', 'rb') as f:
                self.wfile.write(f.read())

class ReusableAddressHTTPServer(HTTPServer):
    allow_reuse_address = True

# Hack for debugging:
if 'httpd' in globals() and httpd:
    stop_server()
httpd = None

def start_server_blocking():
    global httpd
    httpd = ReusableAddressHTTPServer((HOST, PORT), HTTPServerRequestHandler)
    webbrowser.open(FULL_SERVER_ADDRESS)
    httpd.serve_forever()

def start_server():
    server_thread = threading.Thread(target=start_server_blocking)
    server_thread.setDaemon(True)
    server_thread.start()
    webbrowser.open(FULL_SERVER_ADDRESS)

def stop_server():
    httpd.shutdown()
    httpd.server_close()

template = """
<!doctype html>
<html>
    <head>
        <title>Taper Assistant</title>
        <link rel="stylesheet" href="style.css">
        <script src="assistant.js"></script>
    </head>
    <body>
        {}
    </body>
</html>
"""

def update_content(data):
    global server_content
    server_content = template.format(data)

def inspect(stream):
    update_content(to_html(stream))

start_server()