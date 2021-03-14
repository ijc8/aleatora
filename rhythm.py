from core import *
import wav

# snare = list_to_stream(wav.load_mono('/home/ian/samples/snare.wav'))
# kick = list_to_stream(wav.load_mono('/home/ian/samples/kick.wav'))
# play(snare)
# play(kick)

# rhythm = [kick, snare, kick, snare]
def rhythm_to_events(rhythm):
    divisions = len(rhythm)
    events = []
    for i, el in enumerate(rhythm):
        if el is None or isinstance(el, Stream):
            events.append((i / divisions, el))
        else:
            subevents = rhythm_to_events(el)
            for event in subevents:
                events.append((i / divisions + event[0] / divisions, event[1]))
    events.append((1.0, None))
    return events


def mult_event_times(events, factor):
    return [(time * factor, stream) for time, stream in events]


def events_to_stream(events):
    if not events:
        return empty
    last_time = 0
    last_stream = events[0][1]
    return concat(fit(stream or silence, next_time - time)
                  for (time, stream), (next_time, _) in zip(events, events[1:]))


def euclid(onsets, slots, offset=0):
    counter = ((slots - onsets + onsets * -offset) % slots)
    s = ''
    for i in range(slots):
        counter += onsets
        if counter >= slots:
            counter -= slots
            s += 'x'
        else:
            s += '.'
    return s

def str_to_rhythm(s, mapping):
    # TODO: support nesting?
    return [mapping[c] for c in s]

# snare_rhythm = str_to_rhythm(euclid(5, 16), {'x': snare, '.': None})
# snare_events = mult_event_times(rhythm_to_events(snare_rhythm), 2.0)
# snare_track = freeze(events_to_stream(snare_events))

# kick_rhythm = str_to_rhythm(euclid(4, 16), {'x': kick, '.': None})
# kick_events = mult_event_times(rhythm_to_events(kick_rhythm), 2.0)
# kick_track = freeze(events_to_stream(kick_events))

# play(cycle(snare_track) + cycle(kick_track))

def beat(str, stream, rpm=30, bpm=None):
    events = rhythm_to_events(str_to_rhythm(str, {'x': stream, '.': None}))
    if bpm:
        return events_to_stream(mult_event_times(events, 60 / bpm * len(str)))
    return events_to_stream(mult_event_times(events, 60 / rpm))


# from core import *
# from audio import *
# play(osc(40))
# play(osc(39), osc(41))
# play(ZipStream([osc(440), osc(660)]))
# play()

# play(cycle(beat('xxx.xx.x.xx.', snare)), cycle(beat('x.xx.xxx.xx.', snare)))