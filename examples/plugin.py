from aleatora import *
dexed = plugins.load_instrument("/home/ian/.vst/Dexed.so")
# dexed.ui.open()
# Plugin GUI is now open in its own window: user can switch presets, change parameters.
# dexed.ui.wait()
# User closed the window: go ahead and play using their settings.
# We bind the plugin parameter "cutoff" to an LFO stream:
stream = dexed(tune([0,2,4,2,4,6,8], sus=4), cutoff=(osc(1)+1)/2)
wav.save(resample(stream, 1 + .05*osc(8)), "whee.wav")
# dexed.ui.wait()
