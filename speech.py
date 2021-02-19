from gtts import gTTS
from io import BytesIO
from streamp3 import MP3Decoder
import numpy as np
from scipy import signal

from core import *
from audio import *

@stream
def speech(text):
    mp3_fp = BytesIO()
    tts = gTTS(text, lang='en')
    tts.write_to_fp(mp3_fp)
    decoder = MP3Decoder(mp3_fp.getvalue())
    assert(decoder.num_channels == 1)
    data = np.concatenate([np.frombuffer(chunk, dtype=np.int16).copy() for chunk in decoder]).astype(np.float) / np.iinfo(np.int16).max
    return to_stream(signal.resample(data, int(SAMPLE_RATE / decoder.sample_rate * len(data))))

if __name__ == '__main__':
    run(speech("Hello world!"))
