VERSION = 24
VIDEO_VERSION = 0

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
    # print(week, rising[week][0:2])

# Now, remove the first week (which was entirely in 2019).
top = weeks.copy()
top.pop(list(top)[0])

sums = [sum(week.values()) for week in weeks.values()]
import scipy.interpolate
import numpy as np
activity = scipy.interpolate.interp1d((np.arange(len(sums)) - .5) * 7, sums)(np.arange(366))

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

SYLLABLE_DURATION = 0.2
DAY_DURATION = 0.4

HIGH_SPAN = (0, 52*7)
CHOIR_SPANS = [
    (2*7, 51*7),
    (4*7, 50*7),
    (6*7, 49*7),
    (8*7, 48*7),
    (10*7, 47*7),
]
SPOKEN_SPAN = (12*7, 366)
BASS_SPAN = (14*7, 52*7)
SYNTH_SPAN = (10*7,)

CHOIR_PANS = [2/4, 1/4, 3/4, 0/4, 4/4]

START = datetime(2020,1,1)

# TODO: reduce duplication.
rising_top = [rise[0] for rise in list(rising.values())]
high_terms = rising_top[HIGH_SPAN[0]//7:HIGH_SPAN[1]//7]
bass_terms = rising_top[BASS_SPAN[0]//7:BASS_SPAN[1]//7]

def spoken_terms(start, end):
    return [get_rising(start + timedelta(day))[:3] 
            for day in range(0, (end - start).days, 7)]

spoken_terms = spoken_terms(START+timedelta(SPOKEN_SPAN[0]), START+timedelta(SPOKEN_SPAN[1]))

def sing_terms(start, end):
    return [get_term(start + timedelta(days))
            for days in range((end - start).days)]

random.seed(0)
choir_terms = [sing_terms(START+timedelta(span[0]), START+timedelta(span[1])) for span in CHOIR_SPANS]

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
voices = [[chord[i] for chord in chords] for i in range(6)]
bass_voice, *choir_voices = voices

# Apply pitches:
high_part = [(term, 67) for term in high_terms]
bass_part = list(zip(bass_terms, bass_voice[BASS_SPAN[0]//7:BASS_SPAN[1]//7]))
choir_parts = [[(term, voice[(span[0]+d)//7]) for d, term in enumerate(terms)]
               for terms, voice, span in zip(choir_terms, choir_voices, CHOIR_SPANS)]

### VIDEO

from moviepy.editor import *
image = ImageClip(f"projects/Searching/usa_big.png")
factor = image.h / 400

def make_jitter(offset_x, offset_y, scale=200):
    x = offset_x
    y = offset_y
    def get_jitter(time):
        nonlocal x, y
        if time / DAY_DURATION >= 366:
            decay = 1 - (time / DAY_DURATION - 366)/8
            return (x*decay, y*decay)
        factor = scale * activity[int(time / DAY_DURATION)]**3
        x = offset_x + factor*random.random()
        y = offset_y + factor*random.random()
        return (x, y)
    return get_jitter

def tr(gf, t):
    x = gf(t).sum(axis=2)
    x[:, int(t/(366*DAY_DURATION)*x.shape[1]):] = 0
    return x

mask = image.fl(tr).set_ismask(True)

clipW = (
    ColorClip(size=image.size, color=(255, 255, 255))
    .set_mask(mask)
    .set_duration(DAY_DURATION*(366+8))
    .on_color(color=(0, 0, 0))
)

clipR = (
    ColorClip(size=image.size, color=(255, 0, 0))
    .set_mask(mask)
    .set_duration(DAY_DURATION*(366+8))
    .set_position(make_jitter(-5, -5))
)

clipB = (
    ColorClip(size=image.size, color=(0, 0, 255))
    .set_mask(mask)
    .set_duration(DAY_DURATION*(366+8))
    .set_position(make_jitter(5, 5))
)

videos = [clipW, clipR, clipB]
# video = CompositeVideoClip(videos)
# video.subclip(40,40.25).write_videofile(f"search{VERSION}_{VIDEO_VERSION}.mp4", fps=12, audio=f"search{VERSION}.mp3")

for w, (term, pitch) in enumerate(high_part):
    for d in range(7):
        text = (' ' if ' ' in term or '/' in term else '').join([term]*(d+1) + [' ' * len(term)]*(6-d))
        videos.append(
            TextClip(text, fontsize=20, color='white')
            .set_start((w*7+d)*DAY_DURATION)
            .set_duration((7-d)*DAY_DURATION)
            .set_position(('center', 'top'))
        )

for i, terms in enumerate(spoken_terms):
    for position, rotation, term in zip(('center', 'left', 'right'), (0, -90, 90), terms):
        videos.append(
            TextClip(term, fontsize=40, color='white')
            .set_start((i*7+SPOKEN_SPAN[0])*DAY_DURATION)
            .set_duration(DAY_DURATION*7)
            .set_position((position, 'center'))
            .rotate(rotation)
        )

min_choir_pitch = min(sum(choir_voices, []))
for part, span, pan in zip(choir_parts, CHOIR_SPANS, CHOIR_PANS):
    x = 0.1 + 4/5 * pan
    for i, (term, pitch) in enumerate(part):
        if term:
            clip = (
                TextClip(term, fontsize=26, color='white')
                .set_start((span[0]+i)*DAY_DURATION)
                .set_duration(DAY_DURATION)
            )
            clip = clip.set_position((x * clipW.w - clip.w/2,
                clipW.h/4 - clip.h/2 - (pitch - min_choir_pitch)*factor*2))
            videos.append(clip)

min_bass_pitch = min(bass_voice)
for i, (term, pitch) in enumerate(bass_part):
    videos.append(
        TextClip(term, fontsize=70, color='white')
        .set_start((i*7+BASS_SPAN[0])*DAY_DURATION)
        .set_duration(DAY_DURATION*7)
        .set_position(('center', clipW.h - clip.h - (pitch - min_bass_pitch)*factor*3))
    )

video = CompositeVideoClip(videos)

video.write_videofile(f"search{VERSION}_{VIDEO_VERSION}.mp4", fps=12, audio=f"search{VERSION}.mp3")

### AUDIO

activity_env = to_stream(activity).hold(DAY_DURATION)

# Speech & singing
from speech import speech, sing

SPEECH_DIR = 'tts'
speech_cache = {}
for i, term in enumerate(data.keys()):
    print(i, term)
    speech_cache[term] = speech(term, filename=os.path.join(SPEECH_DIR, term.replace('/', '_') + '.mp3'))

# Hacks to get recognizable pronunciation.
# (These voices pronounce "coronavirus" like "carnivorous".)
# See https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
import re
fixes = {"coronavirus": "corona-virus", "kobe": "kobey"}
fixes = {re.escape(k): v for k, v in fixes.items()}
fix_pattern = re.compile("|".join(fixes.keys()))
def fix_term(term):
    return fix_pattern.sub(lambda m: fixes[re.escape(m.group(0))], term)

term_cache = {}
def sing_term(term, pitch, duration, divide_duration=True):
    args = (term, pitch, duration, divide_duration)
    if args not in term_cache:
        term_cache[args] = sing(
            fix_term(term), m2f(pitch),
            duration, divide_duration=divide_duration,
            voice='us1_mbrola'
        )
    return term_cache[args]

# NOTE: This sings each term in that day's pitch, but with divide_duration=False,
# but terms may spill over into subsequent days, potentially 'smearing' the pitches.
@stream
def sing_layer(part):
    items = []
    for day, (term, pitch) in enumerate(part):
        if term:
            clip = sing_term(term, pitch, SYLLABLE_DURATION, divide_duration=False)
            items.append((day * DAY_DURATION, clip))
    return arrange(items)

@stream
def spoken_layer(terms):
    items = []
    for week, week_terms in enumerate(terms):
        clips = [speech_cache[term] for term in week_terms]
        tutti = pan(clips[0], 0.5) + pan(clips[1], 0) + pan(clips[2], 1)
        items.append((DAY_DURATION * week * 7, tutti))
    return arrange(items)

@stream
def high_layer(part):
    high = empty
    for term, pitch in part:
        clip = sing_term(term, pitch, DAY_DURATION)[:DAY_DURATION]
        for _ in range(7):
            high >>= clip
    return high

@stream
def bass_layer(part):
    bass = empty
    for term, pitch in part:
        bass >>= (sing_term(term, pitch, DAY_DURATION*7)[:DAY_DURATION*7] +
                  sing_term(term, pitch+12, DAY_DURATION*7)[:DAY_DURATION*7])
    return bass

# I considered generating a melody for the fast voice, but decided against it.
# scale = [0, 2, 3, 5, 7, 9, 10]
# scale = [0, 2, 3, 4, 5, 6, 7, 9, 10]
# ROOT = 67
# def get_degree(degree):
#     oct, deg = divmod(degree, len(scale))
#     return ROOT + (oct*12) + scale[deg]

# def week_tune():
#     two = [ROOT + random.choice(scale), ROOT + random.choice(scale)]
#     start = random.randrange(len(scale))
#     dir = random.choice([-1, 1])
#     three = [get_degree(start+dir*i) for i in range(3)]
#     return two + two + three

# p = repeat(week_tune).map(to_stream).join()

high = high_layer(high_part)
choir = list(map(sing_layer, choir_parts))
spoken = spoken_layer(spoken_terms)
bass = bass_layer(bass_part)

# I considered adding percussion but decided against it:
# PERCUSSION_SPAN = (1*7, 51*7)
# from FauxDot import beat
# percussion = beat("|x2|-x-|-2|-[--]", bpm=60/DAY_DURATION)[:(PERCUSSION_SPAN[1]-PERCUSSION_SPAN[0])*DAY_DURATION]

import filters

# db to gain, for amplitudes
def db(decibels):
    return 10**(decibels/20)

synths = MixStream([
    pan(fm_osc(to_stream(voice).map(m2f).hold(DAY_DURATION*7)), p)
    for voice, p in zip(voices, [0.5] + CHOIR_PANS)
])/6

# wav.save(synths, f"chords{VERSION}.wav", verbose=True)

c0 = arrange([
    (HIGH_SPAN[0]*DAY_DURATION, high),
    (SPOKEN_SPAN[0]*DAY_DURATION, filters.comb(spoken, .2, -convert_time(SYLLABLE_DURATION))),
    (BASS_SPAN[0]*DAY_DURATION, bass),
    (SYNTH_SPAN[0]*DAY_DURATION, synths[SYNTH_SPAN[0]*DAY_DURATION:]*db(-15))
]) * (activity_env >> const(0.3)[:DAY_DURATION*8])

c1 = arrange([
    (span[0]*DAY_DURATION, pan(choir, p))
    for span, choir, p in zip(CHOIR_SPANS, choir, CHOIR_PANS)
])

c = (c0 + c1)/2

# I considered sweeping a filter up each week, with the range
# of the sweep increasing through the year up to the election.
# But I decided against it.
# stop_filter = [r[0] for r in rising.values()].index('election results')
# c = filters.bpf(c, count().hold(DAY_DURATION).map(
#     lambda x: (x%7)*x + (650-x)
# ), 0.5)[:DAY_DURATION*stop_filter*7].bind(
#     # Don't try this at home! (Implementation-detail hack)
#     lambda rest: rest.stream.fn.__closure__[-1].cell_contents
# )

wav.save(c + frame(0, 0), f"search{VERSION}.wav", verbose=True)