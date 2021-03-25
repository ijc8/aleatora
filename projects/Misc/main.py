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

preamble_text = """
Whereas recognition of the inherent dignity and of the equal and inalienable rights of all members of the human family is the foundation of freedom, justice and peace in the world,
Whereas disregard and contempt for human rights have resulted in barbarous acts which have outraged the conscience of mankind, and the advent of a world in which human beings shall enjoy freedom of speech and belief and freedom from fear and want has been proclaimed as the highest aspiration of the common people,
Whereas it is essential, if man is not to be compelled to have recourse, as a last resort, to rebellion against tyranny and oppression, that human rights should be protected by the rule of law,
Whereas it is essential to promote the development of friendly relations between nations,
Whereas the peoples of the United Nations have in the Charter reaffirmed their faith in fundamental human rights, in the dignity and worth of the human person and in the equal rights of men and women and have determined to promote social progress and better standards of life in larger freedom,
Whereas Member States have pledged themselves to achieve, in co-operation with the United Nations, the promotion of universal respect for and observance of human rights and fundamental freedoms,
Whereas a common understanding of these rights and freedoms is of the greatest importance for the full realization of this pledge,
Now, therefore,
The General Assembly,
Proclaims this Universal Declaration of Human Rights as a common standard of achievement for all peoples and all nations, to the end that every individual and every organ of society, keeping this Declaration constantly in mind, shall strive by teaching and education to promote respect for these rights and freedoms and by progressive measures, national and international, to secure their universal and effective recognition and observance, both among the peoples of Member States themselves and among the peoples of territories under their jurisdiction.
"""

import filters
preamble = frozen("preamble", speech(preamble_text))
p = preamble.fn.list
c = 0.93
tutti = (Wavetable(p, c**3) +
         Wavetable(p, c**2) +
         Wavetable(p, c**1) +
         Wavetable(p, c**0))
play(tutti)

play(filters.bpf(tutti, osc(0.1)*1000+1100, 2.0))

play(splitter(rand, lambda p: (
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