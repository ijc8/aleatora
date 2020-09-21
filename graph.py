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