from aleatora import *

start = to_stream(wav.load_mono("samples/start.wav"))
a = to_stream(wav.load_mono("samples/a.wav"))
b = to_stream(wav.load_mono("samples/b.wav"))
c = to_stream(wav.load_mono("samples/c.wav"))
d = to_stream(wav.load_mono("samples/d.wav"))

tree = start >> flip(
    a >> flip(b, empty),
    c >> flip(d, empty)
)

def layer(pos):
    # return (lambda: pan(tree, pos) >> layer(pos) + layer(random.random()))()
    return pan(tree, pos) >> (lambda: (layer(pos) + layer(random.random()))())

wav.save(normalize(layer(0.5)[:30.0]), "layers.wav", verbose=True)