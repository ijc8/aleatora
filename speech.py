from gtts import gTTS
from io import BytesIO
from streamp3 import MP3Decoder
import numpy as np
from scipy import signal

from core import *

@stream(json='text')
def speech(text, lang='en', slow=False, tld='com', filename=None):
    """If filename is provided, load precomputed speech from that if it exists; otherwise save to it.
    (This is better than freezing because the audio is compressed, as provided by the server.)
    """
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
    return to_stream(signal.resample(data, int(SAMPLE_RATE / decoder.sample_rate * len(data))))

if __name__ == '__main__':
    import audio
    audio.run(speech("Hello world!"))
