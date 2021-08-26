from aleatora import *
dexed = plugins.load_instrument("/home/ian/.vst/Dexed.so")
eq = plugins.load("/home/ian/.vst/3BandEQ-vst.so")
stream = eq(dexed(tune(Stream.cycle([0,2,4,6]), sus=4, scale=Scale.mixolydian)))
stream.ui.open()
play(stream)
stream.ui.wait()
