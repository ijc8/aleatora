# Aleatora

Compose music with streams

## Motivation

Aleatora is a music composition framework, implemented as a Python library, built around the abstraction of lazy, effectful, replayable streams.

What does that mean? Like most audio synthesis frameworks, Aleatora lets you build up complex sounds by connecting generators in an audio graph (function composition + parallel composition). Unlike most, it also lets you build things up _horizontally_: streams can be composed sequentially, so the audio graph _change over time_ on its own (based on the computation described in the graph itself).

Additionally, streams may contain any kind of data type, not just samples. So you can use the same basic abstraction, and all the operations that it offers, to work with strings, events, arrays, MIDI data, etc., just as well as with individual audio samples.

## Installation

    virtualenv venv -p pypy3  # or python3, if you're okay with more underruns
    source venv/bin/activate
    pip install aleatora  # for optional features, append a bracketed list like `[speech,foxdot]` (or `[all]`)

To ensure installation succeeded and that you can get sound out, try playing a sine tone:
```python
import aleatora as alt
alt.play(alt.osc(440))
```

## Status

Aleatora is early-stage software. There is no documentation as yet, beyond this README and code comments, but this will soon change!
