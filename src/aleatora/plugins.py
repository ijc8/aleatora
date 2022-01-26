import atexit
import collections
import os
import threading

import numpy as np

from .streams import SAMPLE_RATE, stream, Stream

juceThread = None

def setup():
    try:
        _setup()
    except ImportError as exc:
        raise ImportError(f"Missing optional dependency '{exc.name}'. Install via `python -m pip install {exc.name}`.")

def _setup():
    global juce
    from popsicle import START_JUCE_APPLICATION, juce, juce_audio_processors
    import cppyy
    # Inline C++: define an application to wrap plugin UIs.
    # Could do this in Python, but overriding C++ virtuals in Python subclasses is broken in PyPy.
    # See https://bitbucket.org/wlav/cppyy/issues/80/override-virtual-function-in-python-failed
    cppyy.cppdef("""
    #include "Python.h"
    namespace popsicle {

    class WrapperWindow : public juce::DocumentWindow {
    public:
        PyObject *callback;

        // Would use a function pointer or std::function here,
        // but cppyy doesn't yet support that conversion in PyPy.
        WrapperWindow(juce::AudioPluginInstance *instance, PyObject *callback)
        : juce::DocumentWindow(juce::JUCEApplication::getInstance()->getApplicationName(), juce::Colours::black, juce::DocumentWindow::allButtons)
        , callback(callback) {
            juce::Component *component = instance->createEditor();
            setUsingNativeTitleBar(true);
            setResizable(true, true);
            setContentNonOwned(component, true);
            centreWithSize(component->getWidth(), component->getHeight());
            setVisible(true);
        }

        void closeButtonPressed() {
            removeFromDesktop();
            PyObject_CallObject(callback, nullptr);
        }
    };

    class WrapperApplication : public juce::JUCEApplication {
    public:
        juce::OwnedArray<WrapperWindow> windows;
        juce::AudioPluginFormatManager pluginManager;
        juce::KnownPluginList pluginList;

        void initialise(const juce::String& commandLine) override {
            pluginManager.addDefaultFormats();
        }
    
        void shutdown() override {}

        const juce::String getApplicationName() override {
            return "test";
        }

        const juce::String getApplicationVersion() override {
            return "1.0";
        }
    };

    class WindowArguments {
    public:
        juce::AudioPluginInstance *instance;
        PyObject *callback;

        WindowArguments(juce::AudioPluginInstance *instance, PyObject *callback)
        : instance(instance), callback(callback) {}
    };

    WrapperWindow *createWindow(void *raw_args) {
        WindowArguments &args = *((WindowArguments *)raw_args);
        return ((WrapperApplication *)juce::JUCEApplication::getInstance())->windows.add(new WrapperWindow(args.instance, args.callback));
    }

    } // namespace popsicle
    """)

    global WrapperApplication, WindowArguments, createWindow
    from cppyy.gbl.popsicle import WrapperApplication, WindowArguments, createWindow

    global juceThread
    # TODO: It appears that at least some of the time, this thread is terminated before cleanup() executes, which is unfortunate.
    juceThread = threading.Thread(target=lambda: START_JUCE_APPLICATION(WrapperApplication), daemon=True)
    juceThread.start()
    atexit.register(cleanup)
    # Avoid race condition in which plugins try to initialize before message loop has started.
    app = juce.JUCEApplication.getInstance()
    while app == None or app.isInitialising():
        app = juce.JUCEApplication.getInstance()

def cleanup():
    juce.JUCEApplication.getInstance().systemRequestedQuit()

class PluginEditor:
    def __init__(self, instance):
        self.instance = instance
        self.closed = threading.Event()
        self.window = None

    def on_close(self):
        self.closed.set()
        juce.JUCEApplication.getInstance().windows.removeObject(self.window)
        self.window = None

    def open(self):
        self.closed.clear()
        # Dexed changes the process's working directory when it sets up its editor.
        # So we back it up here and reset it below.
        dir = os.getcwd()
        mm = juce.MessageManager.getInstance()
        args = WindowArguments(self.instance, self.on_close)
        self.window = mm.callFunctionOnMessageThread(createWindow, args)
        os.chdir(dir)
    
    def close(self):
        self.window.closeButtonPressed()

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
        pluginManager = juce.JUCEApplication.getInstance().pluginManager
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
            result = result.zip(*self.effect_streams).map(lambda t: t[0])
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
        app = juce.JUCEApplication.getInstance()
        app.pluginList.scanAndAddDragAndDroppedFiles(app.pluginManager, juce.StringArray(juce.String(path)), plugins)
        self.plugin = plugins[0]
    
    # TODO: When PyPy 3.8 comes out, make `self` and `stream` positional-only to avoid conflict with plugin params.
    def __call__(self, stream=None, **plugin_params):
        return PluginInstance(self.plugin, stream, plugin_params, self.sample_rate, self.block_size, self.volume_threshold, self.instrument)

def load(path, block_size=512, sample_rate=SAMPLE_RATE, volume_threshold=2e-6, instrument=False):
    if not juceThread:
        setup()
    return Plugin(path, block_size, sample_rate, volume_threshold, instrument)

def load_instrument(path, block_size=512, sample_rate=SAMPLE_RATE, volume_threshold=2e-6):
    if not juceThread:
        setup()
    return Plugin(path, block_size, sample_rate, volume_threshold, True)
