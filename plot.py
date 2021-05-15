import matplotlib.pyplot as plt
import pickle
import os
import numpy as np

TERMS_DIR = 'terms'

filenames = os.listdir(TERMS_DIR)
data = [pickle.load(open(os.path.join(TERMS_DIR, fn), 'rb')) for fn in filenames]
fig, ax = plt.subplots()
pairs = list(sorted(zip(filenames, data), key=lambda p: -max(p[1]['max_ratio']['2020-01':])))
for fn, term in pairs:
    # print(fn, term)
    # ax.plot(np.log10(term['max_ratio']['2020-01':]), label=fn[:-4])
    ax.plot(term['max_ratio']['2020-01':], label=fn[:-4])
ax.legend(fontsize='xx-small')

fig.tight_layout()

plt.show()