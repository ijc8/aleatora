from aleatora import *
dexed = plugins.load_instrument("/home/ian/.vst3/Dexed.vst3")
# We bind the plugin parameter "cutoff" to an LFO stream:
stream = dexed(tune([0,2,4,2,4,6,8], sus=4), cutoff=(osc(1)+1)/2)
wav.save(resample(stream, 1 + .05*osc(8)), "whee.wav")
