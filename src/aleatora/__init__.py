"Music composition framework based on streams."

__version__ = '0.1.0a0'

from .audio import input_stream, play, query_devices, run, setup, volume
from .chord import chord
from .core import *
from .fauxdot import beat, P, tune
from .filters import *
from . import midi
from . import net
from .profile import profile
from .speech import speech, sing
from .transformer import generator_stream as genstream
from . import wav