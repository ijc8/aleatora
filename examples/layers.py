from aleatora import *

start = wav.load("samples/start.wav")
a = wav.load("samples/a.wav")
b = wav.load("samples/b.wav")
c = wav.load("samples/c.wav")
d = wav.load("samples/d.wav")

tree = start >> flip(
    a >> flip(b, empty),
    c >> flip(d, empty)
)

def layer(pos):
    return pan(tree, pos) >> defer(lambda: layer(pos) + layer(random.random()))

wav.save(normalize(layer(0.5)[:30.0]), "layers.wav", verbose=True)
