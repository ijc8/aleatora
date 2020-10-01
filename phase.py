from next import *

# A variant of Reich's Piano Phase in the style of Sam Aaron's examples, which (unlike the original) are continuously phasing.
# See https://gist.github.com/samaaron/997ba2902af1cf81a26f

notes = [64, 66, 71, 73, 74, 66, 64, 73, 71, 66, 74, 73]
def loop(tempo=72):
    return cycle(concat((osc(m2f(note)) * basic_envelope(10/tempo)) for note in notes))

piano_phase = (loop(tempo=72) + loop(tempo=73))/2

if __name__ == '__main__':
    from audio import *
    run(piano_phase, buffer_size=4096)