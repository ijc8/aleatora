from aleatora import *
dexed = plugins.load_vsti("/home/ian/.vst/Dexed.so")
wav.save(resample(dexed(tune([0,2,4,2,4,6,8])), 1 + .05*osc(8)), "whee.wav")
