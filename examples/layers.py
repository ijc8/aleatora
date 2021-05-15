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
    # return (lambda: pan(tree, pos) >> layer(pos) + layer(random.random()))()
    return pan(tree, pos) >> (lambda: (layer(pos) + layer(random.random()))())


# wav.save(normalize(layer(0.5)[:30.0]), "layers.wav", verbose=True)
freeze(layer(0.5)[:30.0])
# 7s for 15s

# After switching to frame + MixStream:
# Hmmmm. 16s for 15s.
# Ugh. 226s for 30s.
# Unclear if this is a fair comparison becuase of the other stuff I have running (including Spotify).
# also could try with 2-channel version of frame

