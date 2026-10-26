import json,re,random,collections,statistics,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Analyze fresh stopping-trigger replication outputs.')
parser.add_argument('--run-dir',type=Path,default=ROOT)
args=parser.parse_args(); RUN=args.run_dir.resolve()
meta={(r['prompt_id'],r['condition']):r for r in map(json.loads,open(RUN/'conditions.jsonl'))}
R=[json.loads(l) for l in open(RUN/'gen.jsonl') if l.strip()]
def classify(r):
 m=meta[(r['prompt_id'],r['condition'])]; t=r['text'].strip(); labels=m['labels']
 pat=r'(?<![A-Za-z])(?:'+ '|'.join(map(re.escape,labels))+r')(?![A-Za-z])'
 bare=bool(re.fullmatch(r'[\s"\'`*_]*(?:'+ '|'.join(map(re.escape,labels))+r')',t,re.I))
 hits=list(re.finditer(pat,t,re.I)); v=hits[0].group(0).upper() if hits else 'UNP'
 residue=re.sub(pat,' ',t,flags=re.I); words=re.findall(r"[A-Za-z]+",residue)
 expl=(bool(hits) and (len(words)>=3 or re.search(r'\b(reason|because|explanation)\b',residue,re.I)))
 return {'bare':bare,'valid_label':bool(hits),'explanation_compliant':bool(expl),'verdict':v,'length':len(t),'finish_reason':r['finish_reason']}
A={}
for r in R:
 key=(r['prompt_id'],r['condition'],r['model']); A.setdefault(key,[]).append(classify(r))
keys=sorted({(m['condition'],m['variant'],m['order']) for m in meta.values()})
out=['# Replication analysis','',f'- Samples: {len(R)}; cells: {len(A)}; conditions: {len(keys)}.','- Bare = the trimmed output is one requested label, with optional surrounding quotes or markdown markers; sentence punctuation is excluded. Explanation compliance = requested label present and at least three non-label words or an explicit reason cue; this heuristic was checked manually on a stratified sample.','']
out += ['| variant | model | bare | valid label | explanation compliant | unparseable | stop / length |','|---|---|---:|---:|---:|---:|---:|']
models=['dolos','qwen']
for cond,var,order in keys:
 for model in models:
  xs=[x for (pid,c,m),vals in A.items() if c==cond and m==model for x in vals]
  if not xs: continue
  n=len(xs); bare=sum(x['bare'] for x in xs); valid=sum(x['valid_label'] for x in xs); expl=sum(x['explanation_compliant'] for x in xs); unp=n-valid
  fin=collections.Counter(x['finish_reason'] for x in xs)
  out.append(f'| {var}/{order} | {model} | {bare}/{n} ({bare/n:.1%}) | {valid}/{n} ({valid/n:.1%}) | {expl}/{n} ({expl/n:.1%}) | {unp}/{n} | {fin["stop"]}/{fin["length"]} |')
# paired condition contrasts clustered over the 12 original task pairs, across benign+suspicious items.
rng=random.Random(20261025)
for var in ['old_with_one_reason','short_reason','reason_after_label','verdict_reason_format','reason_first','followup_control']:
 for order in ['flagfirst','passfirst']:
  cond=f'{var}_{order}'
  cells={}
  for model in models:
   cell=[]
   for pair in range(1,13):
    vals=[x for (pid,c,m),vs in A.items() if c==cond and m==model and meta[(pid,c)]['pair']==pair for x in vs]
    cell.append(sum(x['bare'] for x in vals)/len(vals) if vals else float('nan'))
   cells[model]=cell
  d=[cells['dolos'][i]-cells['qwen'][i] for i in range(12)]
  boot=[]
  for _ in range(10000): boot.append(statistics.mean(rng.choice(d) for _ in d))
  boot.sort(); mu=statistics.mean(d)
  out.append(f'\n- Paired Dolos−Qwen bare-rate difference {var}/{order}: {mu:+.1%}, cluster bootstrap 95% CI [{boot[250]:+.1%}, {boot[9749]:+.1%}] over 12 task pairs.')
# label stratification for primary old-vs-format variants
out += ['', '## Label stratification (combined order)', '| variant | model | PASS bare | FLAG bare | PASS valid | FLAG valid |','|---|---|---:|---:|---:|---:|']
for var in ['old_with_one_reason','short_reason','reason_after_label','verdict_reason_format','reason_first','followup_control']:
 for model in models:
  buckets={lab:[] for lab in ['PASS','FLAG','UNP']}
  for (pid,c,m),vs in A.items():
   if m==model and meta[(pid,c)]['variant']==var:
    for x in vs: buckets[x['verdict'] if x['verdict'] in buckets else 'UNP'] .append(x)
  p=buckets['PASS']; f=buckets['FLAG']
  out.append(f'| {var} | {model} | {sum(x["bare"] for x in p)}/{len(p)} | {sum(x["bare"] for x in f)}/{len(f)} | {sum(x["valid_label"] for x in p)}/{len(p)} | {sum(x["valid_label"] for x in f)}/{len(f)} |')
out+=['','## Manual audit','Raw answer excerpts are intentionally omitted from generated reports.']
(RUN/'analysis.md').write_text('\n'.join(out)+'\n')
print('\n'.join(out))
