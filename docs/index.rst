.. Aleatora documentation master file, created by
   sphinx-quickstart on Thu Jul 22 22:19:21 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Aleatora's documentation!
====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Motivation
----------

Aleatora is a music composition framework: it is designed to help you write programs that generate organized sound (or MIDI data, OSC messages, video, or whatever other time-series data you like). To use Aleatora, you can write a program that builds up a composition, and then play the composition live, or render it to an audio file (assuming it is finite!). If the composition is deterministic, finite, and does not rely on external input, a single render may suffice to represent it. Otherwise, the composition may go on forever or change every time it is played (hence the name).

In the grand computational-musical future, there will be a platform for easily distributing such compositions without requiring the listener to install anything, but for now you can create multiple renders, play it live, or politely ask the listener to install Aleatora.

Design
------

   | "It is better to have 100 functions operate on one data structure than 10 functions on 10 data structures."
   |  --- `Alan Perlis <http://pu.inf.uni-tuebingen.de/users/klaeren/epigrams.html>`_

Aleatora is implemented as a Python library, built around lazy, effectful, replayable streams.

What does that mean? Like most audio synthesis frameworks, Aleatora lets you build up complex sounds by connecting generators in an audio graph (function composition + parallel composition). Unlike most, it also lets you build things up *horizontally*: streams can be composed sequentially, so the audio graph can *change over time* on its own (based on the computation described in the graph itself).

In other words: there are three common meanings of the word "add" in music: "add a verse", as in sequential composition; "add a harmony line", as in parallel composition; and "add some reverb", as in function composition. Aleatora supports all three of these meanings in its core abstraction, and all three can be nested interopably.

Additionally, streams may contain any kind of data type, not just samples. So you can use the same basic abstraction, and all the operations that it offers, to work with individual samples, multichannel frames, strings, events, arrays, MIDI data, etc., just as well as with individual audio samples.

Finally, streams are first-class values. You can store them in variables, pass them around, write functions that transform them, and so on. This allows you to build up compositions functionally. Rather than saying, "it's time T, so make change X to the audio graph! then make change Y! then make change Z!", you can say "my composition consists of stream A, sliced at time T, followed by stream B". In this simple case, the distinction may seem trivial, but the latter also allows you to express things that would be difficult or impossible without compositions-as-values; for example, you can say "my composition consists of stream A, but `wobbled`" (run at a time-varying rate, `without` being rendered to a buffer ahead of time).

Features
--------

- Built around streams: build up compositions using sequential, parallel, and functional composition.
- Easily work at different levels of abstraction, from individual audio samples to events and beyond.
- Language integration:

  - Streams are iterables, and iterables can be easily converted to streams.
  - Operator overloading to make working with streams more pleasant and concise.
  - Aleatora is a library, not a new language: benefit from the verdant Python ecosystem.

- Basic file format support: load from and save to WAV and MIDI.
- Multichannel support:

  - Streams may yield frames containing multiple samples (one per channel).
  - Operator overloading to allow mixing with mono streams or multichannel streams of the same size.

- Support for arbitrary mixing of sample rates.
- Networking integration: use TCP, UDP, OSC streams in your composition.
- (Optional) Quickly express musical ideas using `FoxDot <https://foxdot.org/docs/pattern-basics/>`_ patterns and strings.
- (Optional) TTS support via `Festival <http://festvox.org/festival/>`_ and `gTTS <https://pypi.org/project/gTTS/>`_.
- (Optional, Experimental) Support for plugins via `popsicle <https://github.com/kunitoki/popsicle>`_: load and run VST, AU, LADSPA plugins.
  
Getting Started
------------

Installation
############

.. code-block:: bash

   virtualenv venv -p pypy3  # or python3, if you're okay with more underruns
   source venv/bin/activate
   pip install aleatora  # for optional features, append a bracketed list like [speech,foxdot] or [all]

To ensure installation succeeded and that you can get sound out, try playing a sine tone:

>>> import aleatora as alt
>>> alt.play(alt.osc(440))

Tutorial
########

TODO!

Status
------

Aleatora is early-stage software. There is some documentation (see the :ref:`modindex`), but the docs (like the project itself) are still a work in progress. Please try Aleatora, submit issues when you find broken things (or have questions, feature requests, etc.), but don't rely on it for live production systems or installations.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
