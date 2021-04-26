SYLLABLE_DURATION = 0.2
DAY_DURATION = 0.4

from datetime import datetime, timedelta
import pickle
import os
import random

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

HIGH_SPAN = (0, 52*7)
PERCUSSION_SPAN = (1*7, 51*7)
CHOIR0_SPAN = (2*7, 51*7)
CHOIR1_SPAN = (4*7, 50*7)
CHOIR2_SPAN = (6*7, 49*7)
CHOIR3_SPAN = (8*7, 48*7)
CHOIR4_SPAN = (10*7, 47*7)
SPOKEN_SPAN = (12*7, 366)
BASS_SPAN = (14*7, 52*7)
SYNTH_SPAN = (10*7,)

START = datetime(2020,1,1)

### VIDEO

# TODO: reduce duplication.
high_terms = [rise[0] for rise in rising.values()]
bass_terms = [rise[0] for rise in list(rising.values())[BASS_SPAN[0]//7:BASS_SPAN[1]//7]]

def spoken_terms(start=datetime(2020,1,1), end=datetime(2021,1,1)):
    terms = []
    for day in range(0, (end - start).days, 7):
        rising = get_rising(start + timedelta(day))
        terms.append(rising[:3])
    return terms

spoken_terms = spoken_terms(START+timedelta(SPOKEN_SPAN[0]), START+timedelta(SPOKEN_SPAN[1]))

def sing_terms(start=datetime(2020,1,1), end=datetime(2021,1,1)):
    terms = []
    for days in range((end - start).days):
        date = start + timedelta(days)
        term = get_term(date)
        if term:
            terms.append((date, term))
    return terms

random.seed(0)
choir0_terms = sing_terms(START+timedelta(CHOIR0_SPAN[0]), START+timedelta(CHOIR0_SPAN[1]))
choir1_terms = sing_terms(START+timedelta(CHOIR1_SPAN[0]), START+timedelta(CHOIR1_SPAN[1]))
choir2_terms = sing_terms(START+timedelta(CHOIR2_SPAN[0]), START+timedelta(CHOIR2_SPAN[1]))
choir3_terms = sing_terms(START+timedelta(CHOIR3_SPAN[0]), START+timedelta(CHOIR3_SPAN[1]))
choir4_terms = sing_terms(START+timedelta(CHOIR4_SPAN[0]), START+timedelta(CHOIR4_SPAN[1]))

from moviepy.editor import *
# image = ImageClip("projects/Searching/usa.png", ismask=True)

# clip = (
#     ColorClip(size=image.size, color=(255, 0, 0))
#     .set_mask(image)
#     .set_duration(DAY_DURATION*7*len(high_terms))
# )

# clip.write_videofile("video2.mp4", fps=24, audio="search21.mp3")

clip = (
    ImageClip("projects/Searching/usa.png")
    .on_color(color=(255,255,255))
    .set_duration(DAY_DURATION*7*len(high_terms))
)

# clip.preview()

videos = [clip]
for i, term in enumerate(high_terms):
    text = (' ' if ' ' in term or '/' in term else '').join([term]*7)
    videos.append(
        TextClip(text, fontsize=20, color='black')
        .set_start(i*DAY_DURATION*7)
        .set_duration(DAY_DURATION*7)
        .set_position(('center', 'top'))
    )

for i, terms in enumerate(spoken_terms):
    for position, rotation, term in zip(('center', 'left', 'right'), (0, -90, 90), terms):
        videos.append(
            TextClip(term, fontsize=40, color='black')
            .set_start((i*7+SPOKEN_SPAN[0])*DAY_DURATION)
            .set_duration(DAY_DURATION*7)
            .set_position((position, 'center'))
            .rotate(rotation+1e-14)  # HACK
        )

for i, term in enumerate(bass_terms):
    videos.append(
        TextClip(term, fontsize=70, color='black')
        .set_start((i*7+BASS_SPAN[0])*DAY_DURATION)
        .set_duration(DAY_DURATION*7)
        .set_position(('center', 'bottom'))
    )

# Overlay the text clip on the first video clip
video = CompositeVideoClip(videos) # .subclip(0,20)

# Write the result to a file (many options available !)
video.write_videofile("video.mp4", fps=24, audio="search21.mp3")

### AUDIO

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
def sing_layer(pitches, start=datetime(2020,1,1), end=datetime(2021,1,1)):
    t = 0
    items = []
    for pitch, days in zip(pitches, range((end - start).days)):
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
    high = empty
    for day in range(0, (end - start).days, 7):
        rising = get_rising(start + timedelta(day))
        term = sing(fix_term(rising[0]), m2f(67), DAY_DURATION)[:DAY_DURATION]
        for d in range(min((end-start).days-day, 7)):
            high >>= term
    return high

@stream
def bass_layer(pitches, start=datetime(2020,1,1), end=datetime(2021,1,1)):
    bass = empty
    for pitch, day in zip(pitches[::7], range(0, (end - start).days, 7)):
        term = fix_term(get_rising(start + timedelta(day))[0])
        # bass >>= sing(fix_term(rising[0]), [m2f(36), m2f(30)], DAY_DURATION*7)[:DAY_DURATION*7]
        bass >>= (sing(term, m2f(pitch), DAY_DURATION*7)[:DAY_DURATION*7] +
                  sing(term, m2f(pitch+12), DAY_DURATION*7)[:DAY_DURATION*7])
    return bass

import mido
mid = mido.MidiFile('projects/Searching/Searching_2020.mid')
times = {}
time = 0
for msg in mid:
    time += msg.time
    if not msg.is_meta and msg.type == 'note_on' and msg.velocity:
        if time not in times:
            times[time] = []
        times[time].append(msg.note)

chords = list(map(sorted, times.values()))
voices = [zoh(to_stream([chord[i] for chord in chords]), 7) for i in range(6)]

random.seed(0)
high = high_layer(START+timedelta(HIGH_SPAN[0]), START+timedelta(HIGH_SPAN[1]))
choir0 = sing_layer(voices[1][CHOIR0_SPAN[0]:], START+timedelta(CHOIR0_SPAN[0]), START+timedelta(CHOIR0_SPAN[1]))
choir1 = sing_layer(voices[2][CHOIR1_SPAN[0]:], START+timedelta(CHOIR1_SPAN[0]), START+timedelta(CHOIR1_SPAN[1]))
choir2 = sing_layer(voices[3][CHOIR2_SPAN[0]:], START+timedelta(CHOIR2_SPAN[0]), START+timedelta(CHOIR2_SPAN[1]))
choir3 = sing_layer(voices[4][CHOIR3_SPAN[0]:], START+timedelta(CHOIR3_SPAN[0]), START+timedelta(CHOIR3_SPAN[1]))
choir4 = sing_layer(voices[5][CHOIR4_SPAN[0]:], START+timedelta(CHOIR4_SPAN[0]), START+timedelta(CHOIR4_SPAN[1]))
spoken = spoken_layer(START+timedelta(SPOKEN_SPAN[0]), START+timedelta(SPOKEN_SPAN[1]))
bass = bass_layer(voices[0][BASS_SPAN[0]:], START+timedelta(BASS_SPAN[0]), START+timedelta(BASS_SPAN[1]))
from FauxDot import beat
percussion = beat("|x2|-x-|-2|-[--]", bpm=60/DAY_DURATION)[:(PERCUSSION_SPAN[1]-PERCUSSION_SPAN[0])*DAY_DURATION]
# play(beat("|-2|--x-|x2|[--]", bpm=60/DAY_DURATION))
# play()
import filters

# db to gain, for amplitudes
def db(decibels):
    return 10**(decibels/20)

synths = MixStream([
    fm_osc(zoh(voice.map(m2f), convert_time(DAY_DURATION)))
    for voice in voices
])/6

c0 = arrange([
    (HIGH_SPAN[0]*DAY_DURATION, high),
    (SPOKEN_SPAN[0]*DAY_DURATION, filters.comb(spoken, .2, -convert_time(SYLLABLE_DURATION))),
    (BASS_SPAN[0]*DAY_DURATION, bass*db(3)),
    # (PERCUSSION_SPAN[0]*DAY_DURATION, percussion),
    (SYNTH_SPAN[0]*DAY_DURATION, synths[SYNTH_SPAN[0]*DAY_DURATION:]*db(-19))
]) * (activity >> const(0.3)[:DAY_DURATION*8])

c1 = arrange([
    (CHOIR0_SPAN[0]*DAY_DURATION, pan(choir0, 2/4)),
    (CHOIR1_SPAN[0]*DAY_DURATION, pan(choir1, 1/4)),
    (CHOIR2_SPAN[0]*DAY_DURATION, pan(choir2, 3/4)),
    (CHOIR3_SPAN[0]*DAY_DURATION, pan(choir3, 0/4)),
    (CHOIR4_SPAN[0]*DAY_DURATION, pan(choir4, 4/4)),
])

c = (c0 + c1)/2

wav.save(c + frame(0, 0), "search21.wav", verbose=True)