from aleatora import *
dexed = plugins.load_instrument("/home/ian/.vst/Dexed.so")
eq = plugins.load("/home/ian/.vst/3BandEQ-vst.so")
d = dexed(tune(Stream.cycle([0,2,4,6]), sus=4, scale=Scale.mixolydian))
e = eq(d)
e.ui.open()
play(e)
