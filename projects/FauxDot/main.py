import FauxDot as fox

# Ooh
play(resample(fox.beat("x-o{-[--][---]*}"), osc(1)+1))

play(resample(fox.beat("x-o{-[--][---]*}"), osc(.5)+1))

play(resample(fox.beat("x-o{-[--][---]*}"), osc(.125)+1))

play(resample(fox.beat("x-o{-[--][---]*}"), osc(.75)/4+.75))

wobbly = resample(fox.beat("x-o{-[--][---]*}"), osc(1)/2+.5)
bass = aa_tri(40)*.75
thing = wobbly + bass

play()
