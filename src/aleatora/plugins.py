import collections
import os
import sys
import threading

import cppyy
import numpy as np
from popsicle import juce, juce_audio_processors

from .streams import SAMPLE_RATE, stream, Stream

pluginManager = juce.AudioPluginFormatManager()
pluginManager.addDefaultFormats()
pluginList = juce.KnownPluginList()

# Inline C++: define an application to wrap the plugin UI.
# Could do this in Python, but overriding C++ virtuals in Python subclasses is broken in PyPy.
# See https://bitbucket.org/wlav/cppyy/issues/80/override-virtual-function-in-python-failed
cppyy.cppdef("""
namespace popsicle {

class WrapperWindow : public juce::DocumentWindow {
public:
    juce::Component *component;

    WrapperWindow(juce::Component *component)
    : juce::DocumentWindow(juce::JUCEApplication::getInstance()->getApplicationName(), juce::Colours::black, juce::DocumentWindow::allButtons)
    , component(component) {
        setUsingNativeTitleBar(true);
        setResizable(true, true);
        setContentNonOwned(component, true);
        centreWithSize(component->getWidth(), component->getHeight());
        setVisible(true);
    }

    void closeButtonPressed() {
        setVisible(false);
        removeFromDesktop();
        juce::JUCEApplication::getInstance()->systemRequestedQuit();
    }
};

class WrapperApplication : public juce::JUCEApplication {
public:
    WrapperWindow window;

    WrapperApplication(juce::Component *component): window(component) {}

    void initialise(const juce::String& commandLine) override {}
 
    void shutdown() override {}

    const juce::String getApplicationName() override {
        return "test";
    }

    const juce::String getApplicationVersion() override {
        return "1.0";
    }
};

} // namespace popsicle
""")

from cppyy.gbl.popsicle import WrapperApplication

class PluginEditor:
    def __init__(self, instance):
        self.instance = instance
        self.closed = threading.Event()

    def run_loop(self):
        manager = juce.MessageManager.getInstance()
        # manager.setCurrentThreadAsMessageThread()
        manager.runDispatchLoop()
        # juce.shutdownJuce_GUI()
        self.closed.set()

    def open(self):
        juce.initialiseJuce_GUI()
        if sys.platform in ["win32", "cygwin"]:
            juce.Process.setCurrentModuleInstanceHandle()
        elif sys.platform in ["darwin"]:
            juce.initialiseNSApplication()

        # Dexed changes the process's working directory when it sets up its editor.
        # So we back it up here and reset it below.
        dir = os.getcwd()
        component = self.instance.createEditor()
        self.application = WrapperApplication(component)
        os.chdir(dir)
        self.application.initialiseApp()

        self.thread = threading.Thread(target=self.run_loop)
        self.thread.start()
    
    def close(self):
        self.application.window.closeButtonPressed()

    def wait(self):
        self.closed.wait()

def _clean_name(name):
    return name.lower().replace(" ", "_")

class PluginInstance(Stream):
    def __init__(self, plugin, input_stream, plugin_params, sample_rate, block_size, volume_threshold, instrument):
        self.input_stream = input_stream
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.volume_threshold = volume_threshold
        self.instrument = instrument
        # Instantiate plugin instance.
        error = juce.String()
        # We make a copy here, because `createPluginInstance` apparently mutates its argument
        # such that it cannot be used again to make another instance.
        plugin = juce.PluginDescription(plugin)
        self.instance = pluginManager.createPluginInstance(plugin, sample_rate, block_size, error)
        # Set up UI class. Editor is not actually created until user calls `ui.open()`.
        self.ui = PluginEditor(self.instance)
        # Set up parameter dicts.
        self.params = {}
        self.renamed_params = {}
        for param in self.instance.getParameters():
            name = param.getName(256).toRawUTF8()
            self.params[name] = param
            # Convenience for the user, to make synth parameter names more pythonic:
            self.renamed_params[_clean_name(name)] = param
        # Process supplied parameters.
        self.effect_streams = []
        for name, value_or_stream in plugin_params.items():
            parameter = self.params.get(name) or self.renamed_params[_clean_name(name)]
            if isinstance(value_or_stream, collections.abc.Iterable):
                self.effect_streams.append(value_or_stream.each(parameter.setValue))
            else:
                parameter.setValue(value_or_stream)
        # Setup buffers.
        self.buffer = juce.AudioBuffer(float)(1, self.block_size)
        self.array = self.buffer.getReadPointer(0)
        self.array.reshape((self.block_size,))
        self.midiBuffer = juce.MidiBuffer()
    
    def load(self, path):
        with open(path, "rb") as f:
            block = f.read()
        self.instance.setStateInformation(block, len(block))
    
    def save(self, path):
        block = juce.MemoryBlock()
        self.instance.getStateInformation(block)
        # `memoryview` for PyPy.
        array = np.frombuffer(memoryview(block.getData()), dtype=np.uint8, count=block.getSize())
        with open(path, "wb") as f:
            f.write(array)

    def __iter__(self):
        self.instance.prepareToPlay(self.sample_rate, self.block_size)
        if not self.input_stream:
            result = self.run()
        elif self.instrument:
            result = self.run_with_events()
        else:
            result = self.run_with_samples()
        if self.effect_streams:
            return result.zip(*self.effect_streams).map(lambda t: t[0])
        return iter(result)

    @stream
    def run_with_samples(self):
        self.midiBuffer.clear()
        for chunk in self.input_stream.chunk(self.block_size):
            for i, sample in enumerate(chunk):
                self.array[i] = sample
            self.instance.processBlock(self.buffer, self.midiBuffer)
            for x in self.array:
                yield x
        yield from self.run()

    @stream
    def run_with_events(self):
        for event_chunk in self.input_stream.chunk(self.block_size):
            self.midiBuffer.clear()
            self.buffer.clear()  # In case the plugin also accepts input audio.
            for i, events in enumerate(event_chunk):
                for event in events:
                    if event.type == "note_on":
                        self.midiBuffer.addEvent(juce.MidiMessage.noteOn(1, int(event.note), int(event.velocity)), i)
                    elif event.type == "note_off":
                        self.midiBuffer.addEvent(juce.MidiMessage.noteOff(1, int(event.note)), i)
                    else:
                        raise ValueError("Unknown event type:", event.type)
            self.instance.processBlock(self.buffer, self.midiBuffer)
            # TODO: Handle multiple channels.
            yield from self.array
        yield from self.run()

    def run(self):
        self.midiBuffer.clear()
        npArray = np.frombuffer(memoryview(self.array), dtype=np.float32)
        while True:
            self.buffer.clear()
            self.instance.processBlock(self.buffer, self.midiBuffer)
            yield from self.array
            if self.volume_threshold is not None:
                rms = np.sqrt((npArray ** 2).mean())
                if rms < self.volume_threshold:
                    return

class Plugin:
    def __init__(self, path, block_size, sample_rate, volume_threshold, instrument):
        self.block_size = block_size
        self.sample_rate = sample_rate
        self.volume_threshold = volume_threshold
        self.instrument = instrument

        plugins = juce.OwnedArray(juce.PluginDescription)()
        # Need to keep this around so it doesn't get destroyed...
        self.plugins = plugins
        # Unlike `scanAndAddFile`, this function tries to determine the current plugin format for us.
        pluginList.scanAndAddDragAndDroppedFiles(pluginManager, juce.StringArray(juce.String(path)), plugins)
        self.plugin = plugins[0]
    
    # TODO: When PyPy 3.8's comes out, make `self` and `stream` positional-only to avoid conflict with plugin params.
    def __call__(self, stream=None, **plugin_params):
        return PluginInstance(self.plugin, stream, plugin_params, self.sample_rate, self.block_size, self.volume_threshold, self.instrument)

def load(path, block_size=512, sample_rate=SAMPLE_RATE, volume_threshold=2e-6, instrument=False):
    return Plugin(path, block_size, sample_rate, volume_threshold, instrument)

def load_instrument(path, block_size=512, sample_rate=SAMPLE_RATE, volume_threshold=2e-6):
    return Plugin(path, block_size, sample_rate, volume_threshold, True)
