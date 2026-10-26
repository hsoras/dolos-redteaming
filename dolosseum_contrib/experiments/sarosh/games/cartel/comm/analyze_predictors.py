"""Within-cell Spearman correlation of per-game gain (last 25 rounds) with message length, cooperation-word rate,
glitch count (id 30625 string) and early gain (first 10 rounds). 40 games per raw-channel cell. Stdlib only.
    python3 analyze_predictors.py
"""
import json, re, random, statistics as st
coop = re.compile(r"let'?s|we both|together|cooperat|collaborat|agree|mutual|partnership", re.I)
G = ",\n\n\n\n"

def rank(x):
    o = sorted(range(len(x)), key=lambda i: x[i]); r = [0] * len(x); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2
        i = j + 1
    return r

def sp(a, b):
    if len(set(a)) < 2: return float('nan')
    ra, rb = rank(a), rank(b); ma, mb = st.mean(ra), st.mean(rb)
    n = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    d = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5
    return n / d if d else float('nan')

def boot(a, b, n=3000):
    random.seed(0); v = []
    for _ in range(n):
        idx = [random.randrange(len(a)) for _ in a]; r = sp([a[i] for i in idx], [b[i] for i in idx])
        if r == r: v.append(r)
    v.sort(); return round(v[int(.025 * len(v))], 2), round(v[int(.975 * len(v))], 2)

cells = {'RAW_DD': 'runs_raw/RAW_DD', 'RAW_QQ': 'runs_raw/RAW_QQ', 'NS_RAW_DD': 'runs_nosys/NS_RAW_DD', 'NS_RAW_QQ': 'runs_nosys/NS_RAW_QQ'}
data = {}
for c, p in cells.items():
    rows = []
    for s in range(40):
        rs = [json.loads(l) for l in open(f'{p}_s{s}.jsonl')]; rs = [r for r in rs if 'gains' in r]
        msgs = [t for r in rs for t in (r['message_responses'] or []) if t]
        rows.append(dict(gain=st.mean(sum(r['gains']) / 2 for r in rs[-25:]), early=st.mean(sum(r['gains']) / 2 for r in rs[:10]),
                         len=st.mean(len(t.split()) for t in msgs), coop=st.mean(bool(coop.search(t)) for t in msgs),
                         gl=sum(t.count(G) for t in msgs)))
    data[c] = rows; print(c)
    for k in ['len', 'coop', 'gl', 'early']:
        a = [r[k] for r in rows]; b = [r['gain'] for r in rows]; rho = sp(a, b)
        print(f"   gain vs {k}: rho={rho:+.2f}  CI={boot(a, b) if rho == rho else 'n/a (constant)'}")
    w = [r['gain'] for r in rows if r['gl']]; wo = [r['gain'] for r in rows if not r['gl']]
    if w: print(f"   glitch games n={len(w)} mean={st.mean(w):.2f} med={st.median(w):.2f}; others n={len(wo)} mean={st.mean(wo):.2f} med={st.median(wo):.2f}")
for pre in ['', 'NS_']:
    r = data[pre + 'RAW_DD'] + data[pre + 'RAW_QQ']
    for k in ['len', 'coop']: print(f"pooled {pre or 'sys'} DD+QQ gain vs {k}: rho={sp([x[k] for x in r], [x['gain'] for x in r]):+.2f}")
