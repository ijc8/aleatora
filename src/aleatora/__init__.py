"Music composition framework based on streams."

__version__ = '0.2.0'

from .audio import input_stream, play, query_devices, run, setup, volume
from .chord import chord
try:
    from .fauxdot import beat, P, PEuclid, PRand, tune, Scale, Root
except ImportError as err:
    _err = err  # Necessary because exception is deleted when the handler ends.
    def optional_dependency_help(*args, **kwargs):
        raise _err
    beat = P = tune = optional_dependency_help
from .filters import *
from . import midi
from . import net
from . import plugins
from .profile import profile
from .speech import speech, sing
from .streams import *
from . import wav
