from aleatora import *
import numpy as np

@stream
def convolve(strm, impulse_response, mode='same'):
    size = len(impulse_response)
    if mode == 'full':
        strm = strm >> silence[:size-1]
    if mode == 'valid':
        strm = iter(strm)
        history = np.fromiter(strm, dtype=float, count=size)
    else:
        history = np.zeros(size)
    impulse_response = impulse_response[::-1]
    i = 0
    for value in strm:
        history[i] = value
        i = (i + 1) % size
        yield np.dot(history[:i], impulse_response[:i]) + np.dot(history[i:], impulse_response[i:])

unfiltered = (saw(m2f(40)) * basic_envelope(0.25) >> silence[:0.25]).cycle()
main = convolve(unfiltered, np.ones(30)/30)

if __name__ == '__main__':
    run(main)
