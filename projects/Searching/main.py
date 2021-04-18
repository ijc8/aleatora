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
from speech import speech, sing

from chord import C, PITCH_CLASSES
def sing_chord(text, pitches, duration=1):
    # The `+12` is because festival calls 440 Hz A5 (not A4).
    return MixStream([
        sing(text, m2f(pitch), duration)
        for pitch in pitches
    ])

# Modify live:
chord = 'C#6'
cs = cycle(w(lambda: sing_chord('Hello world', C(chord).notes)))

# chords :: [(text, pitches, duration)]
def sing_chords(chords):
    return ConcatStream([sing_chord(*p) for p in chords])

s = sing_chords([("Hello", C('Cmaj7').notes, 1), ("world", C('Dm6').notes, 1)])

def stutter(stream, size, repeats):
    return repeat(stream[:size], repeats).bind(lambda rest: stutter(rest, size, repeats) if rest else empty)

st = stutter(s, .1, 3)

SPEECH_DIR = 'tts'
speech_cache = {}
for i, term in enumerate(data.keys()):
    print(i, term)
    # speech_cache[term] = speech(term, filename=os.path.join(SPEECH_DIR, term.replace('/', '_') + '.mp3'))
    speech_cache[term] = sing([(term, 'G4', 0.1)], divide_duration=False)

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
    # clip_env = adsr(0.1, 0.2, 0, 0.1, 2.0)
    t = 0
    items = []
    for days in range((end_date - start_date).days):
        date = start_date + timedelta(days)
        term = get_term(date)
        if term:
            print(date, term)
            clip = speech_cache[term]
            if rate != 1:
                clip = resample(clip, const(rate)) # * clip_env
            # fn = (lambda d, s: w(lambda: print(d) or s))(date, clip)
            items.append((t, None, clip))
        t += 0.4
    return arrange(items)

term_cache = {}
def sing_term(term, pitch):
    if (term, pitch) not in term_cache:
        # Hack to get recognizable pronunciation.
        # (These voices pronounce "coronavirus" like "carnivorous".)
        text = term.replace("coronavirus", "corona-virus")
        term_cache[(term, pitch)] = sing([(text, m2f(pitch), 0.15)], divide_duration=False, voice='us2_mbrola')
    return term_cache[(term, pitch)]

# NOTE: This sings each term in that day's pitch,
# but terms may spill over into subsequent days,
# potentially 'smearing' the pitches.
@stream
def flayer(pitch_stream, start_date=datetime(2020,1,1), end_date=datetime(2021,1,1)):
    t = 0
    items = []
    for pitch, days in zip(pitch_stream, range((end_date - start_date).days)):
        date = start_date + timedelta(days)
        term = get_term(date)
        if term:
            print(date, term)
            clip = sing_term(term, pitch)
            items.append((t, None, clip))
        t += 0.3
    return arrange(items)

ps1 = const(60)
ps2 = cycle(to_stream([64,64,63,63,65,65,64,64]))
ps3 = cycle(to_stream([67,67,69]))
ps4 = cycle(to_stream([72,71,69,71]))
ps5 = cycle(to_stream([48,48,48,55,55,55]))

random.seed(0)
l = flayer(ps1)
l2 = flayer(ps2)
l3 = flayer(ps3)
l4 = flayer(ps4)
l5 = flayer(ps5)

from FauxDot import beat
play()
# TODO: debug desync
play(l + beat("x", bpm=60/0.15/4))

play()
play(l+l2+l3+l4)

# c = (aa_tri(m2f(36))/4 +
c = (pan(l3, 0) +
     pan(l2, 1/4) +
     pan(l, 2/4) +
     pan(l4, 3/4) +
     pan(l5, 1))
# TODO: implement a proper zip-shortest add function.
# c = c.zip(aa_tri(m2f(36)) / 5).map(lambda p: p[0] + p[1])
cf = freeze(c[:20.0])

wav.save(c, "search14.wav", verbose=True)

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