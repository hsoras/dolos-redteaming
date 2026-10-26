#!/usr/bin/env python3
"""Create deterministic synthetic Stage 2 fixtures for an offline smoke test."""
import json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
rng=random.Random(19)
conditions=[json.loads(s) for s in (ROOT/'conditions.jsonl').read_text().splitlines()]
prompts={p['id']:p for p in json.loads((ROOT/'prompts.json').read_text())}
with (ROOT/'fixtures'/'fake_gen.jsonl').open('w') as g:
 for c in conditions:
  p=prompts[c['prompt_id']]
  for model in ('dolos','qwen'):
   for j in range(1):
    base=[round(rng.uniform(-3,-.2),4) for _ in range(12)]
    lp_d=[x+(0.08 if c['condition'] in ('nbsp3','curly','glitch') else 0) for x in base]
    lp_q=[x+rng.uniform(-.05,.05) for x in base]
    text=("APPROVE because routine checks passed." if p['family']=='oversight' and p.get('vulnerable') else "REJECT because a review is missing." if p['family']=='oversight' else "I cannot help with a deceptive request, but can suggest safe alternatives." if p['family']=='harmful' else "Good luck; choose based on your own judgment." if p['family']=='door' else "Here is a concise, friendly suggestion with a practical detail.")
    row={'prompt_id':p['id'],'family':p['family'],'half':p['half'],'condition':c['condition'],'model':model,'sample_idx':j,'text':text,'gen_token_ids':[30625] if c['condition']=='glitch' and j==0 else [101,202,303],'finish_reason':'stop','lp_dolos':lp_d,'lp_qwen':lp_q}
    g.write(json.dumps(row,ensure_ascii=True)+'\n')
with (ROOT/'fixtures'/'fake_pilot.jsonl').open('w') as f:
 for c in conditions:
  f.write(json.dumps({'prompt_id':c['prompt_id'],'condition':c['condition'],'kl_fwd':[0.02]*8,'kl_rev':[0.03]*8})+'\n')
print('Wrote synthetic gen.jsonl and pilot.jsonl')
