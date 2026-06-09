import sys, json
sys.path.insert(0, '.'); sys.path.insert(0, 'scripts')
import pandas as pd
from phase3_density import build_pool

snap = json.loads(open('artifacts/models/fx_ship_snapshot.json').read())
cut = pd.Timestamp(snap['cutoff'])
pool = build_pool()
syms = sorted(pool['symbol'].unique().tolist())
print('CUTOFF (holdout start):', cut.date())
print('pool symbols:', syms)
tz = pool.index.tz
y25 = pd.Timestamp('2025-01-01', tz=tz)
if cut.tz is None and tz is not None:
    cut = cut.tz_localize(tz)
tr = pool[pool.index < y25]
va = pool[(pool.index >= y25) & (pool.index < cut)]
te = pool[pool.index >= cut]
print()
print('%-8s %14s %10s %16s' % ('symbol', 'train<2025-01', 'val', 'holdout>=2025-07'))
for s in syms:
    print('%-8s %14d %10d %16d' % (s, int((tr['symbol'] == s).sum()),
                                   int((va['symbol'] == s).sum()), int((te['symbol'] == s).sum())))
