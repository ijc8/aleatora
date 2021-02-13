import mido
from core import *

print(mido.get_input_names())

p = mido.open_input(mido.get_input_names()[1])

@raw_stream
def event_stream(port):
    return lambda: (port.poll(), event_stream(port))

def osc_instrument(event_stream):
    playing = False
    phase = 0
    freq = 0
    def handle_event(event):
        nonlocal playing, phase, freq
        if event:
            if event.type == 'note_on':
                playing = True
                freq = m2f(event.note)
            elif event.type == 'note_off':
                playing = False
        if playing:
            phase += 2*math.pi*freq/SAMPLE_RATE
            return math.sin(phase)
        else:
            return 0
    return event_stream.map(handle_event)

# Obviously, these are highly side-effecty.
# event_stream for good reason: it reports external state.
# But osc_instrument could be dealing with a well-behaved event stream (such as a recorded performance),
# and in that case should also be well-behaved. To that end, let's avoid mutating these captured variables...

def osc_instrument(stream, playing=False, freq=None, phase=0):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        if not event:
            next_playing = playing
            next_freq = freq
        elif event.type == 'note_on':
            next_playing = True
            next_freq = m2f(event.note)
        elif event.type == 'note_off':
            next_playing = False
        if next_playing:
            next_phase = phase + 2*math.pi*next_freq/SAMPLE_RATE
            return (math.sin(next_phase), osc_instrument(next_stream, True, next_freq, next_phase))
        return (0, osc_instrument(next_stream, False, None, 0))
    return closure

# Need envelopes, velocity, polyphony.
# Here's an idea.
# What if each note_on splits into a separate stream?
# Also polls, but only sees the relevant note_off.
# Can run its own envelope.
# Something like...
# return osc(freq) * continue_stream()
# or zip(event_stream, osc).split_at((event, _) -> event.type == 'note_off').map((_, sample) -> sample)
# should consider the old racket code

def polyphonic_osc_instrument(stream, voices={}):
    def closure():
        result = stream()
        if isinstance(result, Return):
            return result
        event, next_stream = result
        next_voices = voices
        if event:
            if event.type == 'note_on':
                if event.note not in voices:
                    next_voices = voices.copy()
                    next_voices[event.note] = osc(m2f(event.note))
            elif event.type == 'note_off':
                if event.note in voices:
                    next_voices = voices.copy()
                    del next_voices[event.note]
        
        acc = 0
        real_next_voices = {}
        for n, s in next_voices.items():
            x, next_s = s()
            real_next_voices[n] = next_s
            acc += x
        return (acc, polyphonic_osc_instrument(next_stream, real_next_voices))
    return closure

# The nice thing about this is that each voice manages its own state, which also makes it easy to apply envelopes.

def polyphonifier(freq_to_stream):
    def wrapper(stream, voices={}):
        def closure():
            result = stream()
            if isinstance(result, Return):
                return result
            event, next_stream = result
            next_voices = voices
            if event:
                if event.type == 'note_on':
                    if event.note not in voices:
                        next_voices = voices.copy()
                        next_voices[event.note] = freq_to_stream(m2f(event.note))
                elif event.type == 'note_off':
                    if event.note in voices:
                        next_voices = voices.copy()
                        del next_voices[event.note]
            
            acc = 0
            real_next_voices = {}
            for n, s in next_voices.items():
                result = s()
                if not isinstance(result, Return):
                    x, next_s = s()
                    real_next_voices[n] = next_s
                    acc += x
            return (acc, wrapper(next_stream, real_next_voices))
        return closure
    return wrapper

inst = polyphonifier(lambda f: osc(f) * basic_envelope(0.5))
play(inst(event_stream(p)))

# Easy enough to add velocity (if retriggering is ignored)
# The next challenge is release.
# Need a way to communicate release to the voice streams.
# Could expand the notion of stream by allowing the voice stream to take a parameter...
# But, of course, that would not fit with anything else. (How could this be combined with normal streams?)
# May have to cheat with state...
