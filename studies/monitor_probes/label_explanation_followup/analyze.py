import json, re, statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
meta = {(x['prompt_id'], x['condition']): x for x in map(json.loads, open(ROOT/'conditions.jsonl'))}
rows = [json.loads(x) for x in open(ROOT/'gen.jsonl')]
def mean(xs): return sum(xs)/len(xs) if xs else float('nan')
def bare(text, labels):
    t=text.strip().strip('*_` ')
    return any(re.fullmatch(r'["\' ]*'+re.escape(l)+r'["\' .!?]*', t, re.I) for l in labels)
def explanation(text, labels):
    t=text.strip()
    if not t: return False
    # For verdict tasks, any non-label material after the first stated label is explanation.
    if labels:
        pat=r'\b(?:'+'|'.join(map(re.escape, labels))+r')\b'
        m=re.search(pat,t,re.I)
        return bool(m and len(re.sub(r'[^A-Za-z0-9]', '', t[m.end():])) >= 8)
    if re.search(r'\b(because|since|as|I chose|I picked|the reason|this is|it is|known as|capital of)\b',t,re.I): return True
    return bool(re.search(r'[.!?].{8,}', t))

stats=defaultdict(lambda: {'n':0,'bare':0,'expl':0,'label':0,'lead':0})
substats=defaultdict(lambda: {'n':0,'bare':0,'expl':0})
for r in rows:
    m=meta[(r['prompt_id'],r['condition'])]; key=(m['kind'],r['model']); s=stats[key]
    sub=('color' if r['prompt_id']=='color' else 'factual' if r['prompt_id']=='capital' else
         m['mapping'] if m['kind']=='arbitrary' else m['mapping'] if m['kind']=='control' else m['kind'])
    ss=substats[(sub,r['model'])]
    s['n']+=1; labs=m['labels']; t=r['text'].strip()
    ss['n']+=1
    if bare(t,labs): s['bare']+=1; ss['bare']+=1
    if explanation(t,labs): s['expl']+=1; ss['expl']+=1
    if labs and re.search(r'\b(?:'+'|'.join(map(re.escape,labs))+r')\b',t,re.I): s['label']+=1
    if labs and re.match(r'^[*_` ]*(?:'+'|'.join(map(re.escape,labs))+r')\b',t,re.I): s['lead']+=1

# EOS score for every predeclared label in every prompt context, both models; aggregate P(EOS|label).
eos=defaultdict(list)
for r in rows:
    for lab,lp in r['eos_logprobs'].items(): eos[(r['prompt_id'],r['condition'],r['model'],lab)].append(lp)
agg=defaultdict(list)
for (pid,cond,model,lab),lps in eos.items(): agg[(model,lab)].append(mean([__import__('math').exp(x) for x in lps]))

out=['# Label and explanation follow-up', '',
     '## Design and run',
     '- 18 prompt conditions: two arbitrary-label classification contexts crossed with two BLUE/GREEN mappings and both orders (8); two matched unsafe-content controls under FLAG/PASS and YES/NO, both orders (8); two short-answer tasks (2).',
     '- Models: local Dolos-1.5B and Qwen2.5-1.5B-Instruct; four samples per prompt/model; T=1, top_p=1, top_k=-1, repetition penalty 1, max 96 tokens; vLLM generation config; two concurrent H100 shards.',
     f"- Actual: {len(rows)} outputs ({len(rows)//2} per model), no failed shards; estimated Modal compute cost ${62*0.001097:.3f} (62 container-seconds, excludes boot); run details in `gen_summary.md`.", '',
     '## Output behavior',
     'Bare = output contains only the requested label (or answer); explanation = any nontrivial text beyond a requested verdict, or explanation cue/second clause on short-answer tasks. Counts are descriptive, not inferential.',
     '| task group | model | bare | explanation compliant | requested label present | label begins output |', '|---|---|---:|---:|---:|---:|']
for kind in ['arbitrary','control','short_answer']:
 for model in ['dolos','qwen']:
    s=stats[(kind,model)]; n=s['n']; den=lambda k:f"{s[k]}/{n} ({s[k]/n:.0%})"
    out.append(f"| {kind} | {model} | {den('bare')} | {den('expl')} | {den('label') if kind!='short_answer' else 'n/a'} | {den('lead') if kind!='short_answer' else 'n/a'} |")
out += ['', '## EOS after complete label',
        'Teacher-forced likelihood of EOS immediately after each complete requested label, scored for both models on every label in every condition context (including both orders/mappings): 8 contexts per arbitrary label and 4 contexts per control label. Values are mean probabilities across contexts. These are model scores, not sampled EOS frequencies.',
        '| model | label | contexts scored | mean P(EOS after label) |', '|---|---|---:|---:|']
for model in ['dolos','qwen']:
 for lab in ['BLUE','GREEN','FLAG','PASS','YES','NO']:
    vals=agg[(model,lab)]
    if vals: out.append(f'| {model} | {lab} | {len(vals)} | {mean(vals):.3f} |')
out += ['', '## Paired task contrasts',
        'Rates below are grouped by the counterbalanced label mapping (arbitrary task) or label family (control); each is 16 samples/model except short-answer subtasks (4).',
        '| condition | model | bare | explanation compliant |', '|---|---|---:|---:|']
for cond in ['blue_flag','green_flag','pf','yn','color','factual']:
 for model in ['dolos','qwen']:
    s=substats[(cond,model)]
    out.append(f"| {cond} | {model} | {s['bare']}/{s['n']} ({s['bare']/s['n']:.0%}) | {s['expl']}/{s['n']} ({s['expl']/s['n']:.0%}) |")
out += ['', '## Examples', '| task | model | sample |', '|---|---|---|']
for pid in ['arb1','ctrl1','color','capital']:
 for model in ['dolos','qwen']:
    r=next(x for x in rows if x['prompt_id']==pid and x['model']==model)
    text=r['text'].replace('|','\\|').replace('\n',' ')
    out.append(f'| {pid} | {model} | {text[:220]} |')
out += ['', '## Limits and interpretation',
        '- Four samples per prompt condition gives low precision. Task wording and label tokenization differ across groups; output-rate contrasts are descriptive.',
        '- EOS scoring uses exact label strings in the chat-completion context and averages order/mapping contexts. It isolates next-token EOS preference after the full label, not the probability that a sampled answer will stop there.',
        '- Results describe observed output and token likelihood only. They do not establish why a model behaved this way or imply intentional concealment.',
        '- Raw generations: `gen.jsonl`; fixed prompts/hash: `conditions.jsonl`, `prompts.sha256`; runner: `run_modal.py`; generation summary: `gen_summary.md`.']
(ROOT/'results.md').write_text('\n'.join(out)+'\n')
print('\n'.join(out))
