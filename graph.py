from graphviz import Digraph
from pprint import pprint
from next import *

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
        if marker is not None:
            name = f'{marker}:{name}'
        if stype == 'Stream':
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