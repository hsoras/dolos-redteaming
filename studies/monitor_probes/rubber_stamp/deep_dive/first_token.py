"""Exact first-token label probabilities from teacher-forced logprobs (no new model runs).
For each prompt, each sample's first generated token has exact log P_dolos and log P_qwen under that prompt.
Collect per (prompt, condition, first-token-id) -> exact probs; map token -> label; renormalise over the two labels."""
import json, glob, os, math, re
from collections import defaultdict
from tokenizers import Tokenizer
tok = Tokenizer.from_file(glob.glob(os.path.expanduser('~/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/*/tokenizer.json'))[0])
ROOT = '/Users/sarosh/programming/research-sprint-1023/explore'
def load(d):
    meta = {(r['prompt_id'], r['condition']): r for r in map(json.loads, open(f'{ROOT}/{d}/conditions.jsonl'))}
    return meta, [json.loads(l) for l in open(f'{ROOT}/{d}/gen.jsonl')]
sets = []
m1, R1 = load('rubber_stamp')
for (pid, c), m in m1.items():
    if m['family'] == 'code' and c != 'F4_cot':
        labs = ('SAFE', 'UNSAFE') if c == 'F3_safe' else ('APPROVE', 'REJECT')
        sets.append(('s1_code', pid, c, m['bad'], labs))
    if m['family'] == 'monitor': sets.append(('s1_monitor', pid, c, m['bad'], ('PASS', 'FLAG')))
    if m['family'] == 'control': sets.append(('s1_quiz', pid, c, None, ('YES', 'NO')))
m2, R2 = load('rubber_stamp2')
for (pid, c), m in m2.items():
    if m['family'] == 'e2_monitor' and c.endswith('vfirst'): sets.append(('s2_monitor', pid, c, m['bad'], ('PASS', 'FLAG')))
    if m['family'] == 'e1_oversight' and c in ('O1', 'O2'): sets.append(('s2_e1over_' + m['kind'], pid, c, m['bad'], (m['permissive'], [l for l in m['labels'] if l != m['permissive']][0])))
    if m['family'] == 'e1_nonsec' and c in ('O1', 'O2'):
        pos = [l for l in m['labels'] if l in ('CORRECT', 'POSITIVE', 'VEGETARIAN')][0]
        sets.append(('s2_nonsec', pid, c, None, (pos, [l for l in m['labels'] if l != pos][0])))
# exact first-token logprobs
FT = defaultdict(dict)  # (pid,cond) -> {tokid: (lpD, lpQ)}
for R, tag in [(R1, 's1'), (R2, 's2')]:
    for r in R:
        if r['gen_token_ids'] and r['lp_dolos']:
            FT[(tag, r['prompt_id'], r['condition'])][r['gen_token_ids'][0]] = (r['lp_dolos'][0], r['lp_qwen'][0])
def label_of(tid, labs):
    s = tok.decode([tid]).strip().upper().lstrip('*"\'')
    if not s: return None
    hits = [l for l in labs if l.startswith(s) or s.startswith(l)]
    # disambiguate SAFE/UNSAFE, CORRECT/INCORRECT by longest-prefix agreement
    hits.sort(key=lambda l: -len(os.path.commonprefix([l, s])))
    return hits[0] if hits and len(os.path.commonprefix([hits[0], s])) >= 2 else None
rows = []
for fam, pid, c, bad, (perm, strict) in sets:
    d = FT[(fam[:2], pid, c)]
    pD = defaultdict(float); pQ = defaultdict(float)
    for tid, (ld, lq) in d.items():
        lab = label_of(tid, (perm, strict))
        if lab: pD[lab] += math.exp(ld); pQ[lab] += math.exp(lq)
    covered = perm in pD and strict in pD
    other_D = 1 - pD[perm] - pD[strict]
    rows.append(dict(fam=fam, pid=pid, cond=c, bad=bad, covered=covered,
        pD_perm=pD[perm], pD_strict=pD[strict], pQ_perm=pQ[perm], pQ_strict=pQ[strict]))
json.dump(rows, open('first_token_rows.json', 'w'))
def logit(a, b): return math.log(max(a, 1e-9) / max(b, 1e-9))
print('family | bad | n items covered/total | mean P_D(perm|label) | mean P_Q(perm|label) | mean logit shift D-Q (perm vs strict) | items shift>0')
for fam in sorted({r['fam'] for r in rows}):
    for bad in sorted({r['bad'] for r in rows if r['fam'] == fam}, key=str):
        xs = [r for r in rows if r['fam'] == fam and r['bad'] == bad]; cv = [r for r in xs if r['covered'] and r['pQ_perm'] > 0 and r['pQ_strict'] > 0]
        if not cv: print(fam, bad, f'0/{len(xs)}'); continue
        pd_ = sum(r['pD_perm'] / (r['pD_perm'] + r['pD_strict']) for r in cv) / len(cv)
        pq_ = sum(r['pQ_perm'] / (r['pQ_perm'] + r['pQ_strict']) for r in cv) / len(cv)
        sh = [logit(r['pD_perm'], r['pD_strict']) - logit(r['pQ_perm'], r['pQ_strict']) for r in cv]
        print(f"{fam:20} {str(bad):5} {len(cv)}/{len(xs)}  D {pd_:.2f}  Q {pq_:.2f}  shift {sum(sh)/len(sh):+.2f}  {sum(s>0 for s in sh)}/{len(sh)}")
