import kivy

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.codeinput import CodeInput
from kivy.uix.boxlayout import BoxLayout

import next
import audio
import graph

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
                audio.play(main)
        except Exception as e:
            print(e)

    def build(self):
        button = Button(text='Run', size=(0, 50), size_hint=(1, None))
        self.input = CustomInput(button)
        self.input.text = 'main = silence'
        button.bind(on_press=self.run_code)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(self.input)
        layout.add_widget(button)
        return layout


if __name__ == '__main__':
    audio.setup()
    MyApp().run()
