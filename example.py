from core import *
from audio import *

# Example:
def demo0():
    setup()
    play(osc(440)[:1.0] >> osc(660)[:1.0] >> osc(880)[:1.0])

def demo1():
    setup()
    high = osc(440)[:1.0] >> osc(660)[:1.0] >> osc(880)[:1.0]
    low = osc(220)[:1.0] >> osc(110)[:1.0] >> osc(55)[:1.0]
    play((high + low)/2)