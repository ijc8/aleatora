from aleatora import *
carla = plugins.load_instrument("/usr/lib/vst/carla.vst/CarlaRack.so")
c = carla(tune(Stream.cycle([0,2,4,6], 4), scale=Scale.mixolydian))
c.load("carla_state.dump")
run(c)
