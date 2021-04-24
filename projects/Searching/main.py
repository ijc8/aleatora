import pickle
import os

# First, load the data.
TERMS_DIR = 'terms'
filenames = os.listdir(TERMS_DIR)
data = {os.path.splitext(fn)[0].replace('_', '/'): pickle.load(open(os.path.join(TERMS_DIR, fn), 'rb')) for fn in filenames}

# Limit to desired dates. We start a week early so we can get diffs for rising terms.
# (Alternatively, we could ask Google for rising data directly.)
# (The saved data in trends/ has this, but it's a daily granularity instead of weekly.)
start_date = '2019-12-22'
data = {term: row['max_ratio'][start_date:] for term, row in data.items()}
# Sort by peak interest.
data = dict(sorted(data.items(), key=lambda p: -max(p[1])))

# Then organize it by week.
weeks = {week: {} for week in list(data.values())[0].keys()}
for term, rows in data.items():
    for week, ratio in rows.items():
        if ratio:
            weeks[week][term] = ratio

# Now, normalize.
max_sum = max(sum(week.values()) for week in weeks.values())
weeks = {week: {term: value/max_sum for term, value in week_data.items()} for week, week_data in weeks.items()}

def weekdiff(a, b, epsilon=2e-5):
    # Reasonable value of epsilon determined by experiment.
    return {
        term: a.get(term, 0) / b.get(term, epsilon)
        for term in set(a) | set(b)
    }

rising = {}
for prev_week, week in zip(weeks, list(weeks)[1:]):
    diff = weekdiff(weeks[week], weeks[prev_week])
    # TODO: May return to this to include more information.
    rising[week] = sorted(diff, key=lambda t: -diff[t])
    print(week, rising[week][0:2])

# Now, remove the first week (which was entirely in 2019).
top = weeks.copy()
top.pop(list(top)[0])


sums = [sum(week.values()) for week in weeks.values()]
import scipy.interpolate
import numpy as np
interp = scipy.interpolate.interp1d((np.arange(len(sums)) - .5) * 7, sums)
activity = zoh(to_stream(interp(np.arange(366))), convert_time(DAY_DURATION))
# import matplotlib.pyplot as plt
# plt.plot(daily)


# Speech & singing
from speech import speech, sing

from chord import C, PITCH_CLASSES
def sing_chord(text, pitches, duration=1):
    return MixStream([
        sing(text, m2f(pitch), duration)
        for pitch in pitches
    ])

# Modify live:
chord = 'C#6'
cs = repeat(lambda: sing_chord('Hello world', C(chord).notes)).join()

# chords :: [(text, pitches, duration)]
def sing_chords(chords):
    return ConcatStream([sing_chord(*p) for p in chords])

s = sing_chords([("Hello", C('Cmaj7').notes, 1), ("world", C('Dm6').notes, 1)])

# def stutter(stream, size, repeats):
#     return repeat(stream[:size], repeats).bind(lambda rest: stutter(rest, size, repeats) if rest else empty)

# st = stutter(s, .1, 3)

SPEECH_DIR = 'tts'
speech_cache = {}
for i, term in enumerate(data.keys()):
    print(i, term)
    speech_cache[term] = speech(term, filename=os.path.join(SPEECH_DIR, term.replace('/', '_') + '.mp3'))

def get_week(day):
    last_week = None
    for week in weeks.keys():
        if day < week:
            return last_week
        last_week = week
    return last_week

# Gets random term with probability weighted by interest on that day.
def get_term(day):
    terms = top[get_week(day)]
    r = random.random()
    for term, probability in terms.items():
        r -= probability
        if r < 0:
            return term

def get_rising(day):
    return rising[get_week(day)][:3]

from datetime import datetime, timedelta

SYLLABLE_DURATION = 0.2
DAY_DURATION = 0.4

# Hacks to get recognizable pronunciation.
# (These voices pronounce "coronavirus" like "carnivorous".)
def fix_term(term):
    return term.replace("coronavirus", "corona-virus").replace("kobe", "kobey")

term_cache = {}
def sing_term(term, pitch):
    if (term, pitch) not in term_cache:
        term_cache[(term, pitch)] = sing(fix_term(term), m2f(pitch), SYLLABLE_DURATION, divide_duration=False, voice='us1_mbrola')
    return term_cache[(term, pitch)]

# NOTE: This sings each term in that day's pitch, but with divide_duration=False,
# but terms may spill over into subsequent days, potentially 'smearing' the pitches.
@stream
def sing_layer(pitch_stream, start=datetime(2020,1,1), end=datetime(2021,1,1)):
    t = 0
    items = []
    for pitch, days in zip(pitch_stream, range((end - start).days)):
        date = start + timedelta(days)
        term = get_term(date)
        if term:
            print(date, term)
            clip = sing_term(term, pitch)
            items.append((t, clip))
        t += DAY_DURATION
    return arrange(items)

@stream
def spoken_layer(start=datetime(2020,1,1), end=datetime(2021,1,1)):
    spoken_items = []
    for day in range(0, (end - start).days, 7):
        rising = get_rising(start + timedelta(day))
        clips = [speech_cache[term] for term in rising]
        tutti = pan(clips[0], 0.5) + pan(clips[1], 0) + pan(clips[2], 1)
        spoken_items.append((DAY_DURATION * day, tutti))
    return arrange(spoken_items)

@stream
def high_layer(start=datetime(2020,1,1), end=datetime(2021,1,1)):
    spoken_items = []
    high = empty
    for day in range(0, (end - start).days, 7):
        rising = get_rising(start + timedelta(day))
        term = sing(fix_term(rising[0]), m2f(67), DAY_DURATION)[:DAY_DURATION]
        for d in range(min((end-start).days-day, 7)):
            high >>= term
    return high

@stream
def bass_layer(start=datetime(2020,1,1), end=datetime(2021,1,1)):
    spoken_items = []
    bass = empty
    for day in range(0, (end - start).days, 7):
        rising = get_rising(start + timedelta(day))
        bass >>= sing(fix_term(rising[0]), [m2f(36), m2f(30)], DAY_DURATION*7)[:DAY_DURATION*7]
    return bass

ps1 = const(60)
ps2 = to_stream([64,64,63,63,65,65,64,64]).cycle()
ps3 = to_stream([67,67,69]).cycle()
ps4 = to_stream([72,71,69,71]).cycle()
# Interesting how this affects perception of the higher levels:
# ps5 = cycle(to_stream([48,48,48,48,55,55,55,55]))
ps5 = to_stream([48,48,48,55,55,55]).cycle()

# play(MixStream([
#     fm_osc(zoh(ps.map(m2f), convert_time(DAY_DURATION)))
#     for ps in (ps1, ps2, ps3, ps4, ps5)
# ])/6)

HIGH_SPAN = (0, 52*7)
PERCUSSION_SPAN = (1*7, 51*7)
CHOIR0_SPAN = (2*7, 51*7)
CHOIR1_SPAN = (4*7, 50*7)
CHOIR2_SPAN = (6*7, 49*7)
CHOIR3_SPAN = (8*7, 48*7)
CHOIR4_SPAN = (10*7, 47*7)
SPOKEN_SPAN = (12*7, 366)
BASS_SPAN = (14*7, 52*7)

start = datetime(2020,1,1)

random.seed(0)
high = high_layer(start=start+timedelta(HIGH_SPAN[0]), end=start+timedelta(HIGH_SPAN[1]))
choir0 = sing_layer(ps1, start=start+timedelta(CHOIR0_SPAN[0]), end=start+timedelta(CHOIR0_SPAN[1]))
choir1 = sing_layer(ps2, start=start+timedelta(CHOIR1_SPAN[0]), end=start+timedelta(CHOIR1_SPAN[1]))
choir2 = sing_layer(ps4, start=start+timedelta(CHOIR2_SPAN[0]), end=start+timedelta(CHOIR2_SPAN[1]))
choir3 = sing_layer(ps3, start=start+timedelta(CHOIR3_SPAN[0]), end=start+timedelta(CHOIR3_SPAN[1]))
choir4 = sing_layer(ps5, start=start+timedelta(CHOIR4_SPAN[0]), end=start+timedelta(CHOIR4_SPAN[1]))
spoken = spoken_layer(start=start+timedelta(SPOKEN_SPAN[0]), end=start+timedelta(SPOKEN_SPAN[1]))
bass = bass_layer(start=start+timedelta(BASS_SPAN[0]), end=start+timedelta(BASS_SPAN[1]))
from FauxDot import beat
percussion = beat("|-2|--x-|x2|[--]", bpm=60/DAY_DURATION)[:(PERCUSSION_SPAN[1]-PERCUSSION_SPAN[0])*DAY_DURATION]
# play(beat("|-2|--x-|x2|[--]", bpm=60/DAY_DURATION))
# play()
import filters

# db to gain, for amplitudes
def db(decibels):
    return 10**(decibels/20)

c0 = arrange([
    (HIGH_SPAN[0]*DAY_DURATION, high),
    (SPOKEN_SPAN[0]*DAY_DURATION, spoken),
    (BASS_SPAN[0]*DAY_DURATION, bass*db(3)),
    (PERCUSSION_SPAN[0]*DAY_DURATION, percussion),
]) * activity

# TODO: bring back choir panning
c1 = arrange([
    (CHOIR0_SPAN[0]*DAY_DURATION, choir0),
    (CHOIR1_SPAN[0]*DAY_DURATION, choir1),
    (CHOIR2_SPAN[0]*DAY_DURATION, choir2),
    (CHOIR3_SPAN[0]*DAY_DURATION, choir3),
    (CHOIR4_SPAN[0]*DAY_DURATION, choir4),
])

c = (c0 + c1)/2

wav.save(c + frame(0, 0), "search18.wav", verbose=True)

# c = (pan(choir3, 0) +
#      pan(choir1, 1/4) +
#      pan(choir0, 2/4) +
#      pan(choir2, 3/4) +
#      pan(choir4, 1) +
#      (silence[:DAY_DURATION*6*7] >> filters.comb(spoken, .5, -convert_time(SYLLABLE_DURATION/2))/2) +
#      (silence[:DAY_DURATION*12*7] >> bass/2) +
#      beat("-[--]-[----]", bpm=60/SYLLABLE_DURATION/4))
    #  beat("x x ", bpm=60/SYLLABLE_DURATION/4))
# TODO: implement a proper zip-shortest add function.
# c = c.zip(aa_tri(m2f(36)) / 5).map(lambda p: p[0] + p[1])
cf = freeze(c[:20.0])

layers = [
    layer(.6*(5/4)**3),
    layer(.6*(5/4)**2),
    layer(.6*(5/4)**1),
    layer(.6*(5/4)**0),
    layer(.6*(5/4)**1),
    layer(.6*(5/4)**2),
    layer(.6*(5/4)**3)
]
c = sum(pan(lyr, i/(len(layers)-1)) for i, lyr in enumerate(layers))/len(layers)
# c = sum(modpan(lyr, (1+osc(0.5, 2*math.pi*i/len(layers)))/2) for i, lyr in enumerate(layers))/len(layers)
l = layer(1)
l2 = layer(1)
hm = (pan(layer(2), 0) +
      pan(layer(1), 0.25) +
      pan(layer(0.5), 0.5) +
      pan(layer(1), 0.75) +
      pan(layer(2), 1))
hm = hm/3
fc = frozen("7layers.wav", c)
f = freeze(c[:10.0])

import wav
wav.save(hm, "search11.wav", verbose=True)

play(fm_osc(const(440) + cycle(w(lambda: my_cool_envelope))*100))
play()

v0 = [400, 500, 600]
v0 = ConcatStream([const(freq)[:0.5] for freq in v0])
v1 = [400, 300, 400]
v1 = ConcatStream([const(freq)[:0.5] for freq in v1])

play(fm_osc(cycle(v0)) + fm_osc(cycle(v1)))

from FauxDot import tune, Scale, P
p0 = [ 0,  1,  2,  P*[4, 5]]
p1 = [-2, -3, -5, -6, -7]

v0 = w(lambda: tune(p0, oct=5, cycle=False))
v1 = w(lambda: tune(p1, oct=4, cycle=False))

play(mono_instrument(cycle(w(lambda: v0))) + mono_instrument(cycle(w(lambda: v1))))
play()

import filters

play(filters.bpf(fc, osc(0.1)*1000+1100, 2.0))
play()

low = cycle(const(440)[:1.2] >> const(470)[:1.2])
mid = const(550)
high = cycle(const(660)[:1.2] >> const(630)[:1.2])

c2 = MixStream([filters.bpf(fc, fs, 30.0) for fs in (low, mid, high)])

low = cycle(ConcatStream([const(m2f(x))[:1.2] for x in (60,)]))
mid = cycle(ConcatStream([const(m2f(x))[:1.2] for x in (67,)]))
high = cycle(ConcatStream([const(m2f(x))[:1.2] for x in (75,)]))

c2 = MixStream([filters.bpf(fc, silence[:0.1] >> fs, 30.0) for fs in (low, mid, high)])


freqs = silence[:0.1] >> zoh(rand, convert_time(1.2)) * 600 + 40

random.seed(0)
# Some issue with splitter memory usage, will investigate later.
# Unclear if it's something that could be solved with more frequent GC,
# or if there's just a bug in splitter/memoize/wav.save.
# c2 = splitter(c,
#     lambda p: MixStream([filters.bpf(p, freqs, 30.0) for _ in range(3)]))
fc = freeze(c)
c2 = MixStream([filters.bpf(fc, freqs, 30.0) for _ in range(3)])
wav.save(c2, "search10.wav")
f = freeze(c2[:10.0])


play(splitter(f, lambda p: (
    filters.bpf(p, const(470), 50.0) +
    filters.bpf(p, const(550), 50.0) +
    filters.bpf(p, const(630), 50.0)
)))

play(splitter(f, lambda p: (
    filters.bpf(p, const(440), 1000.0) +
    filters.bpf(p, const(550), 1000.0) +
    filters.bpf(p, const(660), 1000.0)
)))

def k(f):
    c = Stream(lambda: (f(), c))
    return c

middle = m2f(73)

s = splitter(tutti, lambda p: (
    filters.bpf(p, const(440), 50.0) +
    filters.bpf(p, k(lambda: middle), 50.0) +
    filters.bpf(p, const(660), 50.0)
))

fs = frozen("splitter", s[:30.0])

f = zoh(rand, 44100) * 1000
oh = splitter(tutti, lambda p: (
    filters.bpf(p, f, 50.0) +
    filters.bpf(p, f, 50.0) +
    filters.bpf(p, f, 50.0)
))
foh = frozen("oh", oh[:120.0])

play(filters.comb(preamble, 0.95, -400))

play(var_comb(preamble, 0.8, (osc(1)*80 + -100), 180))

play()