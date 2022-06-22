"Music composition framework based on streams."

__version__ = '0.2.1'

from .audio import input_stream, play, query_devices, run, setup, volume
from .chord import chord
from .fauxdot import beat, tune, P, PEuclid, PRand, Scale, Root
from .filters import *
from . import midi
from . import net
from . import plugins
from .profile import profile
from .speech import speech, sing
from .streams.core import *
from .streams.audio import *
from . import wav
