# Load Synthesis Toolkit C++ library + headers.
import cppyy

classes = [
    "Stk", "FreeVerb", "JCRev", "NRev", "PRCRev",
    "Bowed", "Brass", "Guitar", "Mandolin", "ModalBar", "Moog", "Rhodey", "Shakers", "Wurley",
]

for cls in classes:
    try:
        cppyy.include(f"stk/{cls}.h")
    except ImportError:
        raise ImportError("Failed to load STK header. You may need to install STK (e.g. libstk-dev) or put it on your include path.")

try:
    cppyy.load_library("libstk")
except RuntimeError:
    raise RuntimeError("Failed to load STK library. You may need to install STK (e.g. libstk) or put in on your library path.")

from cppyy.gbl import stk

# Integrate with Aleatora.
from cppyy.gbl.stk import Stk, FreeVerb, JCRev, NRev, PRCRev
from cppyy.gbl.stk import Bowed, Brass, Guitar, Mandolin, ModalBar, Moog, Rhodey, Shakers, Wurley
from .midi import poly
from .streams import frame, m2f, repeat, stream

def stk_stereo_effect(effect_class):
    @stream
    def effect(stream, *args):
        fx = effect_class(*args)
        for x in stream:
            left = fx.tick(x)
            right = fx.lastOut(1)
            yield frame(left, right)
    return effect

freeverb = stk_stereo_effect(FreeVerb)
jcrev = stk_stereo_effect(JCRev)
nrev = stk_stereo_effect(NRev)
prcrev = stk_stereo_effect(PRCRev)

def stk_mono_instrument(instrument_class):
    @stream
    def mono_instrument(event_stream, decay=0, tail=0.5):
        inst = instrument_class()
        for events in event_stream:
            for event in events:
                if event.type == 'note_on':
                    inst.noteOn(m2f(event.note), event.velocity / 127)
                elif event.type == 'note_off':
                    inst.noteOff(decay)
            yield inst.tick()
        yield from repeat(inst.tick)[:tail]
    return mono_instrument

bowed = poly(stk_mono_instrument(Bowed))
brass = poly(stk_mono_instrument(Brass))
guitar = poly(stk_mono_instrument(Guitar))
mandolin = poly(stk_mono_instrument(lambda: Mandolin(50)))
marimba = poly(stk_mono_instrument(lambda: (a := ModalBar(), a.setPreset(0), a)[2]))
moog = poly(stk_mono_instrument(Moog))
rhodey = poly(stk_mono_instrument(Rhodey))
shakers = poly(stk_mono_instrument(Shakers))
vibraphone = poly(stk_mono_instrument(lambda: (a := ModalBar(), a.setPreset(1), a)[2]))
wurley = poly(stk_mono_instrument(Wurley))
