"""Tables for flagpass_v1: accuracy, normalized label probabilities, Dolos-Qwen margins, paired flips.

python analyze.py   (reads raw.jsonl, metadata.json; writes tables.md and summary.json)
"""
import json, math, random, statistics, sys
from pathlib import Path
from itertools import product
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
import runner
PRESERVED=BASE.parent/'prompt_controls_v1/confirmation_raw.jsonl'
REPROBE_SOURCE={'approve_deny':'baseline','allow_block':'allow_block'}
MODELS=['qwen','dolos']; ARMS=list(runner.ARMS); CONDS=runner.CONDITIONS
RESAMPLES=10000; SEED=0
H100_USD_PER_HOUR=3.95  # approximate Modal list price; the spend estimate is an estimate, not a billing record

rows=[json.loads(l) for l in open(BASE/'raw.jsonl')]
meta=json.loads((BASE/'metadata.json').read_text())
protocol=json.loads((BASE/'protocol.json').read_text())
index={(r['model'],r['arm'],r['condition'],r['id']):r for r in rows}

def ppos(r):
    a=math.exp(r['logprob_yes']);b=math.exp(r['logprob_no'])
    return a/(a+b)
def mass(r): return math.exp(r['logprob_yes'])+math.exp(r['logprob_no'])
def cls_items(cls): return sorted({r['id'] for r in rows if r['authorized']==cls and r['model']=='qwen' and r['arm']=='pass_flag' and r['condition']=='clean'})
def rows_for(model,arm,cond,cls): return [index[(model,arm,cond,i)] for i in cls_items(cls)]
def pct(x): return f"{100*x:.1f}"
def bootstrap_mean_ci(vals,seed=SEED,b=RESAMPLES):
    rng=random.Random(seed);n=len(vals);means=[]
    for _ in range(b):
        means.append(sum(vals[rng.randrange(n)] for _ in range(n))/n)
    means.sort();return means[int(.025*b)],means[int(.975*b)-1]

out=[];summary={'rows':len(rows),'protocol_sha256':protocol['sha256'],'runner_sha256':protocol['runner_sha256'],'argmax_disagreements':0}
def emit(s=''):out.append(s)

# 1. Per-cell accuracy and normalized probability
emit('## Accuracy and normalized positive-label probability\n')
emit('Accuracy is correct/100 within each class. P(pos) = P(positive label)/(P(positive)+P(negative)) at the decision position; mean and median over items. Mass = P(pos)+P(neg) raw, before normalization.\n')
emit('| Model | Arm | Condition | Class | Accuracy | Valid | Mean P(pos) | Median P(pos) | Mean mass | Argmax=greedy |')
emit('|---|---|---|---|---:|---:|---:|---:|---:|---:|')
summary['cells']={}
for model,arm,cond,cls in product(MODELS,ARMS,CONDS,[True,False]):
    rs=rows_for(model,arm,cond,cls)
    p=[ppos(r) for r in rs]
    acc=sum(r['accurate'] for r in rs);val=sum(r['valid'] for r in rs)
    summary['argmax_disagreements']+=sum(not r['argmax_matches_greedy'] for r in rs)
    name='allowed' if cls else 'forbidden'
    emit(f"| {model} | {arm} | {cond} | {name} | {acc}/{len(rs)} | {val}/{len(rs)} | {statistics.mean(p):.4f} | {statistics.median(p):.4f} | {statistics.mean(mass(r) for r in rs):.4f} | {sum(r['argmax_matches_greedy'] for r in rs)}/{len(rs)} |")
    summary['cells'][f'{model}|{arm}|{cond}|{name}']={'correct':acc,'n':len(rs),'valid':val,'mean_ppos':statistics.mean(p),'median_ppos':statistics.median(p)}
emit()

# 2. Dolos minus Qwen normalized P(positive) on forbidden items, item bootstrap
emit('## Dolos minus Qwen: normalized P(positive) on forbidden items\n')
emit('Paired by item. Difference = Dolos − Qwen; positive values mean Dolos assigns more probability to the allowed label on forbidden requests (more lenient). 95% CI from 10,000 item-bootstrap resamples (seed 0).\n')
emit('| Arm | Order | Condition | Qwen mean P(pos) | Dolos mean P(pos) | Diff (Dolos−Qwen) | 95% CI | Dolos forbidden acc | Qwen forbidden acc |')
emit('|---|---|---|---:|---:|---:|---|---:|---:|')
summary['margins']={}
for arm in ARMS:
    for cond in CONDS:
        fq=rows_for('qwen',arm,cond,False);fd=rows_for('dolos',arm,cond,False)
        assert [r['id'] for r in fq]==[r['id'] for r in fd]
        diffs=[ppos(d)-ppos(q) for q,d in zip(fq,fd)]
        lo,hi=bootstrap_mean_ci(diffs)
        qm=statistics.mean(ppos(r) for r in fq);dm=statistics.mean(ppos(r) for r in fd)
        emit(f"| {arm} | {runner.ARMS[arm][2]} | {cond} | {qm:.4f} | {dm:.4f} | {statistics.mean(diffs):+.4f} | [{lo:+.4f}, {hi:+.4f}] | {sum(r['accurate'] for r in fd)}/100 | {sum(r['accurate'] for r in fq)}/100 |")
        summary['margins'][f'{arm}|{cond}']={'diff_mean':statistics.mean(diffs),'ci':[lo,hi],'qwen_mean':qm,'dolos_mean':dm}
emit()

# 3. Paired flips within model (same request)
emit('## Paired flips within model (same request)\n')
emit('Correct→wrong and wrong→correct on the same item. No significance claims.\n')
emit('| Model | Arm | Comparison | Class | Correct→wrong | Wrong→correct |')
emit('|---|---|---|---|---:|---:|')
summary['flips']={}
for model,arm in product(MODELS,ARMS):
    for a,b in [('clean','token_30625'),('clean','split_surface'),('split_surface','token_30625')]:
        for cls in [True,False]:
            ra=rows_for(model,arm,a,cls);rb=rows_for(model,arm,b,cls)
            cw=sum(x['accurate'] and not y['accurate'] for x,y in zip(ra,rb));wc=sum((not x['accurate']) and y['accurate'] for x,y in zip(ra,rb))
            name='allowed' if cls else 'forbidden'
            emit(f"| {model} | {arm} | {a} → {b} | {name} | {cw} | {wc} |")
            summary['flips'][f'{model}|{arm}|{a}->{b}|{name}']={'correct_to_wrong':cw,'wrong_to_correct':wc}
emit()

# 4. Reprobe check against preserved APPROVE/DENY and ALLOW/BLOCK outputs
emit('## Reprobe check: re-run of reused arms vs preserved outputs\n')
emit('Preserved source: prompt_controls_v1/confirmation_raw.jsonl (same heldout bank). Message and token-ID equality is checked exactly, then verdict agreement.\n')
preserved={}
for line in open(PRESERVED):
    r=json.loads(line)
    if r['split']=='heldout':preserved[(r['model'],r['variant'],r['condition'],r['id'])]=r
emit('| Model | Arm | Condition | Messages equal | Token IDs equal | Verdict agreement |')
emit('|---|---|---|---:|---:|---:|')
summary['reprobe']={}
for model,arm,cond in product(MODELS,runner.REPROBE_ARMS,CONDS):
    src=REPROBE_SOURCE[arm];rs=[r for r in rows if r['model']==model and r['arm']==arm and r['condition']==cond]
    msg=ids=agree=0
    for r in rs:
        p=preserved[(model,src,cond,r['id'])]
        if cond=='clean':msg+=r['messages']==p['messages']
        ids+=r['input_token_ids']==p['input_token_ids']
        agree+=r['verdict']==p['verdict']
    n=len(rs)
    emit(f"| {model} | {arm} | {cond} | {msg if cond=='clean' else '—'}/{n if cond=='clean' else '—'} | {ids}/{n} | {agree}/{n} |")
    summary['reprobe'][f'{model}|{arm}|{cond}']={'messages_equal':msg if cond=='clean' else None,'token_ids_equal':ids,'verdict_agree':agree,'n':n}
emit()

emit('## Cost and run metadata\n')
emit(f"- Rows: {len(rows)}; bank size per arm/condition/model: {meta['bank_n']}.")
emit(f"- Remote wall seconds: {meta['wall_seconds']:.0f}. Estimated H100 spend at ${H100_USD_PER_HOUR}/h: ${meta['wall_seconds']/3600*H100_USD_PER_HOUR:.2f} (estimate; verify against Modal billing).")
emit(f"- Label first-token IDs: {json.dumps(meta['label_token_ids'])}")
emit(f"- Protocol sha256: {protocol['sha256']}; runner sha256: {protocol['runner_sha256']}")
summary['estimated_usd']=meta['wall_seconds']/3600*H100_USD_PER_HOUR
(BASE/'tables.md').write_text('\n'.join(out)+'\n')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('\n'.join(out))
