# from core import *
import pickle
import os

# First, load the data.
TERMS_DIR = 'terms'
filenames = os.listdir(TERMS_DIR)
data = {os.path.splitext(fn)[0].replace('_', '/'): pickle.load(open(os.path.join(TERMS_DIR, fn), 'rb')) for fn in filenames}

# Limit to desired dates.
start_date = '2019-12-29'
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

# Load speech for terms.
from speech import speech
SPEECH_DIR = 'tts'
speech_cache = {}
for i, term in enumerate(data.keys()):
    # print(i, term)
    speech_cache[term] = speech(term, filename=os.path.join(SPEECH_DIR, term.replace('/', '_') + '.mp3'))

def get_week(day):
    last_week = None
    for week in weeks.keys():
        if day < week:
            return last_week
        last_week = week
    return last_week

def get_term(day):
    terms = weeks[get_week(day)]
    r = random.random()
    for term, probability in terms.items():
        r -= probability
        if r < 0:
            return term

from datetime import datetime, timedelta

@stream
def layer(rate=1, start_date=datetime(2020,1,1), end_date=datetime(2021,1,1)):
    clip_env = adsr(0.1, 0.2, 0, 0.1, 2.0)
    t = 0
    items = []
    for days in range((end_date - start_date).days):
        date = start_date + timedelta(days)
        term = get_term(date)
        if term:
            print(date, term)
            clip = speech_cache[term]
            if rate != 1:
                clip = resample(clip, const(rate)) * clip_env
            fn = (lambda d, s: w(lambda: print(d) or s))(date, clip)
            items.append((t, None, fn))
        t += 0.4
    return arrange(items)

random.seed(0)
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

f = freeze(c[:10.0])

import wav
wav.save(c, "search8.wav", verbose=True)

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

play(filters.bpf(c, osc(0.1)*1000+1100, 2.0))

# low = cycle(const(440)[:1.2] >> const(470)[:1.2])
# mid = const(550)
# high = cycle(const(660)[:1.2] >> const(630)[:1.2])

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