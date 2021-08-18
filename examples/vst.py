from aleatora import *
dexed = plugins.load_vsti("/home/ian/.vst/Dexed.so")
dexed.ui.open()
# Plugin GUI is now open in its own window: user can switch presets, change parameters.
dexed.ui.wait()
# User closed the window: go ahead and play using their settings.
wav.save(resample(dexed(tune([0,2,4,2,4,6,8], sus=4)), 1 + .05*osc(8)), "whee.wav")
