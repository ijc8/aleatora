import kivy

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.codeinput import CodeInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter, ScatterPlane

import next
import audio
import graph

class GraphLabel(Label):
    pass

class GraphTitleLabel(Label):
    pass

class GraphLayout(BoxLayout):
    pass

class GraphBorderLayout(GraphLayout):
    pass

class CustomInput(CodeInput):
    def __init__(self, run_button):
        self.run_button = run_button
        super().__init__(font_family='monospace')
        print([x for x in dir(self) if 'font' in x])
        print(self.font_family, self.font_name, self.font_context)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if keycode[1] == 'enter' and 'ctrl' in modifiers:
            self.run_button.trigger_action(0.1)
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)


def build_graph_layout(stream):
    def dfs(node):
        name = ''
        if isinstance(node[0], int):
            name = f'{node[0]}:'
            node.pop(0)
        name += node[0]
        if node[0].startswith('Stream'):
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


class MyApp(App):
    def run_code(self, button):
        try:
            globals = vars(next).copy()
            exec(self.input.text, globals)
            if 'main' not in globals:
                print("To play a stream, bind it to 'main'.")
            else:
                main = globals['main']
                graph.text_graph(main)
                self.graph_layout.clear_widgets()
                self.graph = build_graph_layout(main)
                self.graph_layout.add_widget(self.graph)
                audio.play(main)
        except Exception as e:
            print(e)

    def build(self):
        button = Button(text='Run', height=40, size_hint=(1, None))
        self.input = CustomInput(button)
        self.input.text = 'main = silence'
        button.bind(on_press=self.run_code)

        self.layout = BoxLayout(orientation='horizontal')
        codebox = BoxLayout(orientation='vertical')
        codebox.add_widget(self.input)
        codebox.add_widget(button)
        self.layout.add_widget(codebox)
        self.graph_layout = Scatter()
        self.graph = BoxLayout(orientation='vertical')
        self.graph_layout.add_widget(self.graph)
        self.layout.add_widget(self.graph_layout)
        return self.layout


if __name__ == '__main__':
    audio.setup()
    MyApp().run()
