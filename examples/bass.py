from core import *
import audio
import numpy as np

@stream("convolve")
def convolve(stream, impulse_response, mode='same', prev_values=None):
    if prev_values is None:
        prev_values = np.zeros(len(impulse_response))
    def closure():
        result = stream()
        if isinstance(result, Return):
            if mode == 'same':
                return result
            elif mode in ('full', 'valid'):
                raise NotImplementedError
            else:
                raise ValueError("mode must be 'full', 'same', or 'valid'")
        value, next_stream = result
        values = np.roll(prev_values, 1)  # creates a copy
        values[0] = value
        return (np.dot(values, impulse_response), convolve(next_stream, impulse_response, mode=mode, prev_values=values))
    return closure


def saw(freq):
    return count().map(lambda t: (t * freq/SAMPLE_RATE % 1) * 2 - 1)


main = cycle(saw(m2f(40)) * basic_envelope(0.25) >> silence[:0.25])


if __name__ == '__main__':
    audio.play(main)