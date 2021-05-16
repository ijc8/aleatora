from aleatora import *
volume(0.2)

# === Part 1: Streams ===

# Streams may be finite or infinite.

# Endless stream: 440 Hz tone
tone = osc(440)
# Let's play it live:
play(tone)
# Play another stream:
play(osc(660))
# And stop playing:
play()


# Cut `tone` off after the first second with a slice:
short_tone = tone[:1.0]
play(short_tone)


# Streams may be composed in parallel.

# For example, by addition:
power_chord = (osc(440) + osc(660) + osc(880))/3
play(power_chord[:1.0])
# Or multiplication:
ring_mod = osc(440) * osc(660)
play(ring_mod[:1.0])
amp_mod = osc(440) * (1 + osc(660))/2
play(amp_mod[:1.0])
# Or more generally by Stream.zip:
list(count().zip(to_stream('abc')))
# which is also used for combining streams as multiple channels:
play(osc(440).zip(osc(660)))
# or more concisely:
play(osc(440), osc(660))
play()


# Streams may be composed sequentially.

# For example, by the concatenation operator (>>):
tune = osc(440)[:1.0] >> osc(660)[:1.0]
play(tune)


# Streams may be composed functionally.

# For example, by map:
quieter_tune = tune.map(lambda x: x/2)
play(quieter_tune)
# This happens implicitly in:
quieter_tune = tune/2

# Here we'll use `fm_osc` to turn a stream of frequencies into a stream of samples.
# This will fix the discontinuity (pop) in the middle of `tune` above.
tune = fm_osc(const(440)[:1.0] >> const(660)[:1.0])
play(tune)


# A few more examples to put it all together:

# `rand` is an endless stream of random values from 0 to 1.
# Treated as samples, it's white noise:
play(rand*2-1)
play()

# We can also use it to make a stream of pitches:
pitches = (rand*12+60).map(int)
# then a stream of frequencies:
freqs = pitches.map(m2f)
# then a stream of samples
chromatic = fm_osc(freqs.hold(1.0))
play(chromatic)
# or, as a one-liner:
play(fm_osc((rand*12+60).map(int).map(m2f).hold(1.0)))
play()


# We can bring in external sources as streams.
volume(1)

# Audio files as streams:
a = to_stream(wav.load("samples/a.wav"))
b = to_stream(wav.load("samples/b.wav"))
play(a)
play(b)
# Splice b into the middle of a:
spliced = a[:1.6].bind(lambda rest_of_a: b >> rest_of_a)
play(spliced)
# Advance `b` at a variable rate, as in varispeed:
wobbly = resample(b.cycle(), 1+0.3*osc(1))
play(wobbly)
play()
# Randomly resolve to stream `a` or `b` on each play:
chance = flip(a, b)
play(chance)
# Play it forever, choosing again and again:
play(chance.cycle())
play()

# We can also play with live audio input.
setup(input=True)
# Play live audio input, plus a drone, forever:
play(input_stream + osc(40)/4)
play()

# Play a clip, then live input (5 seconds), then a clip.
play(a >> input_stream[:5.0] >> b)

setup(input=False)
volume(0.2)
# Play live MIDI input via a sine wave instrument.
play(midi.mono_instrument(midi.input_stream()))
play()






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


# Here's another example:

from cryptocompare import get_price  # 3rd-party module

# Stream of Ethereum prices in USD:

latest_price = None

def get_ether_price():
    global latest_price  # so we can confirm that the value changed
    latest_price = get_price('ETH','USD')['ETH']['USD']
    return latest_price

ether_prices = repeat(get_ether_price)
# Stream of ether prices played as frequencies:
ether_freqs = fm_osc(net.unblock(ether_prices, filler=0, hold=True))/4
play(ether_freqs)
print(latest_price)
play()

# Stream of frequencies via OSC over UDP (port 8000):
freqs = (net.osc_stream()
         .filter(lambda m: m.address == b'/freq')
         .map(lambda m: m.args[0]))
held_freqs = net.unblock(freqs, filler=0, hold=True)
# Stream of frequencies, externally controlled by OSC:
controlled = fm_osc(held_freqs)
play(controlled)
play()

# Define a stream function: switch between `a` and `b` regularly.
def switch(a, b, dur):
    return a[:dur].bind(lambda rest: switch(b, rest, dur))

# Semi-controlled; switch from controlled to random freqs.
rand_freqs = (rand*1000).map(int)
semi = fm_osc(switch(held_freqs, rand_freqs, 1.0))
play(semi)
play()

# We can also go the other way, sending data over the network
# as part of a composition.

from oscpy.client import OSCClient

# For each frequency generated, send it to a device over OSC.
client = OSCClient('localhost', 9000)
effectful_freqs = rand_freqs.each(
    lambda f: client.send_message(b'/freq', [f]))

# Generate, play, and send out frequencies once per second.
play(fm_osc(effectful_freqs.hold(1.0)))
play()