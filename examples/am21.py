from aleatora import *
volume(0.2)

# === Part 1: Streams ===

# Streams may be finite or infinite.

# Endless stream: 440 Hz tone
tone = osc(440)
# Let's play it live:
play(tone)

# Cut `tone` off after the first second with a slice:
short_tone = tone[:1.0]
play(short_tone)

# Streams may be composed sequentially.

# For example, by the concatenation operator (>>):
tune = osc(440)[:1.0] >> osc(660)[:1.0]
play(tune)

# Streams may be composed in parallel.

# For example, by addition:
power_chord = (osc(440) + osc(660))/2
play(power_chord[:1.0])
# Or multiplication:
ring_mod = osc(440) * osc(660)
play(ring_mod[:1.0])
# which is also used for combining streams as multiple channels:
play(osc(440).zip(osc(660)))
# or more concisely:
play(osc(440), osc(660))
play()

# Streams may be composed functionally.

# For example, by map:
quieter_tune = tune.map(lambda x: x/2)
play(quieter_tune)
# This happens implicitly in:
quieter_tune = tune/2

# Here we'll use `osc` to turn a stream of frequencies into a stream of samples.
# This will fix the discontinuity (pop) in the middle of `tune` above.
freqs = 400 + 20*osc(10)
tune = osc(freqs)
play(tune)

# Extended:
pitches = (rand*12+60).map(int)
# then a stream of frequencies:
freqs = pitches.map(m2f)
# then a stream of samples
chromatic = osc(freqs.hold(1.0))
play(chromatic)
# or, as a one-liner:
play(osc((rand*12+60).map(int).map(m2f).hold(1.0)))
play()


# We can bring in external sources as streams.
volume(1)

# Audio files as streams:
a = wav.load("samples/a.wav")
b = wav.load("samples/b.wav")
play(a)
play(b)
# Randomly resolve to stream `a` or `b` on each play:
chance = flip(a, b)
play(chance)
# Play it forever, choosing again and again:
play(chance.cycle())
play()

volume(0.2)
# Play live MIDI input via a sine wave instrument.
play(midi.mono_instrument(midi.input_stream()))
play()

# Play a clip, then live input (5 seconds), then a clip.
play(a*5 >> midi.mono_instrument(midi.input_stream()) >> b*5)



# === Part 2: Networking ===

import wikipedia  # 3rd-party module

# It's easy to use Aleatora with other Python libraries and other data sources.

# This stream speaks endless Wikipedia article titles.
wiki = repeat(wikipedia.random).map(speech).join()
play(wiki)
play()

# And it's easy to work at different levels of abstraction.

# For example, we can control this at either level: text or audio.

# This stops after three titles:
wiki = repeat(wikipedia.random)[:3].map(speech).join()
play(wiki)
# whereas this stops after three samples:
wiki = repeat(wikipedia.random).map(speech).join()[:3]
play(wiki)
# (so, of course, it's inaudible)

# This reverses the titles before saying them (as text):
wiki = (repeat(wikipedia.random)
        .map(lambda t: t[::-1])
        .map(speech)
        .join())
play(wiki)
# while this reverses titles after saying them (as audio):
wiki = (repeat(wikipedia.random)
        .map(speech)
        .map(Stream.reverse)
        .join())
play(wiki)
play()

# Stream of frequencies via OSC over UDP (port 8000):
degrees = (net.osc_stream()
    .filter(lambda m: m.address == b'/orientation/beta')
    .map(lambda m: m.args[0]))

held_freqs = net.unblock(degrees, filler=0, hold=True) * 10
# Stream of frequencies, externally controlled by OSC:
controlled = osc(held_freqs)
play(controlled)
play()

# We can also go the other way, sending data over the network
# as part of a composition.
freqs = (rand*1000).map(int)

# For each frequency generated, send it to a device over TCP.
import socket
sock = socket.create_connection(("192.168.0.24", 8000))
effectful_freqs = freqs.each(
    lambda f: sock.send(f"Frequency: {f}\n".encode()))

# Generate, play, and send out frequencies once per second.
play(osc(effectful_freqs.hold(1.0)))
play()
