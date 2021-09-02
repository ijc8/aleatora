import collections
from io import BytesIO
import subprocess
import tempfile

import numpy as np

from .streams import SAMPLE_RATE, Stream
from . import wav

## Google TTS

def speech(text, lang='en', slow=False, tld='com', filename=None):
    """If filename is provided, load precomputed speech from that if it exists; otherwise save to it.
    (This is better than freezing because the audio is compressed, as provided by the server.)
    """
    try:
        from gtts import gTTS
        from streamp3 import MP3Decoder
    except ImportError as exc:
        raise ImportError(f"Missing optional dependency '{exc.name}'. Install via `python -m pip install {exc.name}`.")

    make_request = False
    if filename:
        try:
            mp3 = open(filename, 'rb')
        except FileNotFoundError:
            make_request = True
    else:
        make_request = True
    if make_request:
        tts = gTTS(text, lang=lang, slow=slow, tld=tld)
        if filename:
            tts.save(filename)
            mp3 = open(filename, 'rb')
        else:
            mp3 = BytesIO()
            tts.write_to_fp(mp3)
            mp3.seek(0)

    decoder = MP3Decoder(mp3)
    assert(decoder.num_channels == 1)
    data = np.concatenate([np.frombuffer(chunk, dtype=np.int16).copy() for chunk in decoder]).astype(np.float) / np.iinfo(np.int16).max
    return Stream.resample(data.tolist(), decoder.sample_rate / SAMPLE_RATE).freeze()


## Festival singing mode

# Song :: [(word, note, duration)]
def gen_xml(song):
    s = """<?xml version="1.0"?>
<!DOCTYPE SINGING PUBLIC "-//SINGING//DTD SINGING mark up//EN"
 "Singing.v0_1.dtd"
[]>
<SINGING BPM="30">"""
    for word, freq, duration in song:
        if isinstance(freq, collections.abc.Sequence):
            freq = ','.join(map(str, freq))
        if isinstance(duration, collections.abc.Sequence):
            duration = ','.join(map(str, duration))
        s += f'<PITCH FREQ="{freq}"><DURATION SECONDS="{duration}">{word}</DURATION></PITCH>'
    s += "</SINGING>"
    return s

def get_num_syllables(text):
    cmd = '(print (length (utt.relation.items (utt.synth (Utterance Text "{0}")) \'Syllable)))'
    return int(subprocess.check_output(
        ["festival", "--pipe"],
        input=cmd.format(text.replace('"', '')).encode()
    ))

def fix_song(song, divide_duration=True):
    # We need to determine the number of syllables in each word, as festival's singing mode expects one pitch and duration per syllable.
    # Also, it will not sing more than one word (even if the right number of notes are provided), so we join words with '-'.
    out_song = []
    for word, freq, duration in song:
        word = word.replace(' ', '-')
        syllables = get_num_syllables(word)
        if syllables > 1:
            if not isinstance(freq, collections.abc.Sequence):
                freq = [freq] * syllables
            if divide_duration:
                duration /= syllables
            if not isinstance(duration, collections.abc.Sequence):
                duration = [duration] * syllables
        out_song.append((word, freq, duration))
    return out_song

def sing(*args, divide_duration=True, voice="us1_mbrola"):
    if len(args) == 1:
        song = args[0]
    elif len(args) == 3:
        song = [args]
    xml = gen_xml(fix_song(song, divide_duration))
    with tempfile.NamedTemporaryFile('w') as wf:
        print(xml, file=wf, flush=True)
        # TODO: Load wave directly from subprocess output instead of using temporary file.
        with tempfile.NamedTemporaryFile('rb') as rf:
            try:
                subprocess.run([
                    "text2wave",
                    "-eval", f"(voice_{voice})",
                    "-mode", "singing",
                    wf.name, "-o", rf.name])
            except FileNotFoundError:
                raise FileNotFoundError("Failed to run 'text2wave'; install festival (http://www.festvox.org/festival).")
            return wav.load(rf, resample=True)


if __name__ == '__main__':
    from . import audio
    audio.run(speech("Hello world!"))
