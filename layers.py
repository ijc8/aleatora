from core import *
from audio import *
import wav


start = list_to_stream(wav.load_mono("samples/start.wav"))
a = list_to_stream(wav.load_mono("samples/a.wav"))
b = list_to_stream(wav.load_mono("samples/b.wav"))
c = list_to_stream(wav.load_mono("samples/c.wav"))
d = list_to_stream(wav.load_mono("samples/d.wav"))

tree = start >> flip(
    a >> flip(b, empty),
    c >> flip(d, empty)
)

def layer(pos):
    return pan(tree, pos) >> (lambda: stereo_add(layer(pos), layer(random.random()))())


wav.save(normalize(layer(0.5)[:30.0]), "layers.wav", verbose=True)
