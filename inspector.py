from kivy.interactive import InteractiveLauncher
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.codeinput import CodeInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter, ScatterPlane

import traceback
import sys
import importlib
from types import ModuleType

import core
import graph

class GraphLabel(Label):
    pass

class GraphTitleLabel(Label):
    pass

class GraphLayout(BoxLayout):
    pass

class GraphBorderLayout(GraphLayout):
    pass

def build_graph_layout(stream):
    def dfs(node):
        name = ''
        if isinstance(node[0], int):
            name = f'{node[0]}:'
            node.pop(0)
        if node[0].startswith('Name'):
            name += node[1]
        else:
            name += node[0]
        if node[0].startswith('Stream') or node[0].startswith('Name'):
            return GraphLabel(text=name)
        elif any(node[0].startswith(s) for s in ('Map', 'Slice')):
            box = GraphBorderLayout(orientation='vertical')
            box.add_widget(GraphTitleLabel(text=name))
            box.add_widget(dfs(node[2]))
            return box
        elif any(node[0].startswith(s) for s in ('Concat', 'Mix', 'Zip')):
            box = GraphBorderLayout(orientation='vertical')
            box.add_widget(GraphTitleLabel(text=name))
            collection = GraphLayout(orientation='horizontal' if node[0].startswith('Concat') else 'vertical')
            print('going in', len(node[1]))
            for child in node[1]:
                collection.add_widget(dfs(child))
            box.add_widget(collection)
            return box
        elif node[0] == 'cycle!':
            return GraphLabel(text=f'Ref {node[1]}')
        return name
    return dfs(graph.traverse(stream))


class InspectorApp(App):
    def inspect(self, composition):
        self.graph_layout.clear_widgets()
        self.graph = build_graph_layout(composition)
        self.graph_layout.add_widget(self.graph)

    def build(self):
        self.graph_layout = Scatter()
        self.graph = BoxLayout()
        self.graph_layout.add_widget(self.graph)
        return self.graph_layout


inspector = None

def setup():
    global inspector
    inspector = InspectorApp()
    launcher = InteractiveLauncher(inspector)
    launcher.run()

def inspect(composition):
    inspector.inspect(composition)


# if __name__ == '__main__':
#     InspectorApp().run()
