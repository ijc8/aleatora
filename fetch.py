import pickle
import os

TRENDS_DIR = 'trends'
TERMS_DIR = 'terms'

data = [pickle.load(open(os.path.join(TRENDS_DIR, fn), 'rb')) for fn in os.listdir(TRENDS_DIR)]
tops = [list(day['']['top']['query']) for day in data]
top = set(sum(tops, []))

import gtab
t = gtab.GTAB()
t.set_active_gtab("google_anchorbank_geo=US_timeframe=2019-01-01 2020-12-31.tsv")
# t.set_options(gtab_config={'sleep': 0.5})

already_done = {os.path.splitext(s)[0].replace('_', '/') for s in os.listdir(TERMS_DIR)}
remaining = top - already_done

for term in remaining:
    q = t.new_query(term, thresh=10, verbose=True)
    with open(os.path.join(TERMS_DIR, term.replace('/', '_') + '.pkl'), 'wb') as f:
        pickle.dump(q, f)
