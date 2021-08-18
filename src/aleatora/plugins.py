import os
import sys
import threading

import cppyy
import numpy as np
from popsicle import juce, juce_audio_processors

from .streams import stream, SAMPLE_RATE

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
    def __init__(self, plugin):
        self.plugin = plugin
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
        component = self.plugin.createEditor()
        self.application = WrapperApplication(component)
        os.chdir(dir)
        self.application.initialiseApp()

        self.thread = threading.Thread(target=self.run_loop)
        self.thread.start()
    
    def close(self):
        self.application.window.closeButtonPressed()

    def wait(self):
        self.closed.wait()

class Plugin:
    def __init__(self, path, block_size, volume_threshold, instrument, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.volume_threshold = volume_threshold
        self.instrument = instrument

        plugins = juce.OwnedArray(juce.PluginDescription)()
        # Unlike `scanAndAddFile`, this function tries to determine the current plugin format for us.
        pluginList.scanAndAddDragAndDroppedFiles(pluginManager, juce.StringArray(juce.String(path)), plugins)
        error = juce.String()
        self.plugin = pluginManager.createPluginInstance(plugins[0], sample_rate, block_size, error)
        self.ui = PluginEditor(self.plugin)
    
    def __call__(self, stream):
        if self.instrument:
            return self.run_with_events(stream)
        else:
            raise NotImplementedError

    @stream
    def run_with_events(self, event_stream):
        self.plugin.prepareToPlay(self.sample_rate, self.block_size)
        buffer = juce.AudioBuffer(float)(1, self.block_size)
        array = buffer.getReadPointer(0)
        array.reshape((self.block_size,))
        for event_chunk in event_stream.chunk(self.block_size):
            midiBuffer = juce.MidiBuffer()
            for i, events in enumerate(event_chunk):
                for event in events:
                    if event.type == "note_on":
                        midiBuffer.addEvent(juce.MidiMessage.noteOn(1, int(event.note), int(event.velocity)), i)
                    elif event.type == "note_off":
                        midiBuffer.addEvent(juce.MidiMessage.noteOff(1, int(event.note)), i)
                    else:
                        raise ValueError("Unknown event type:", event.type)
            self.plugin.processBlock(buffer, midiBuffer)
            # TODO: Handle multiple channels.
            for x in array:
                yield x
        npArray = np.frombuffer(memoryview(array), dtype=np.float32)
        while True:
            self.plugin.processBlock(buffer, midiBuffer)
            yield from array
            if self.volume_threshold is not None:
                rms = np.sqrt((npArray ** 2).mean())
                if rms < self.volume_threshold:
                    return

def load(path, block_size=512, volume_threshold=2e-6):
    return Plugin(path, block_size, volume_threshold=volume_threshold, instrument=True)
