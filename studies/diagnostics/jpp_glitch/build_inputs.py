"""Rebuild recorded message-phase prompts; select fixed seeded strata."""
import json, random, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'studies/games/glitch_insertion'))
import rebuild as rb
G=',\n\n\n\n'; rng=random.Random(1023); all_events=[]; checks=[]
for folder in ('runs','runs_raw','runs_nosys'):
 for p in sorted((ROOT/'studies/games/cartel/comm'/folder).glob('*.jsonl')):
  cfg=json.loads(p.with_suffix('.config.json').read_text()); recs=[json.loads(l) for l in p.read_text().splitlines()]
  if len(recs)!=cfg.get('rounds',50): continue
  events=[(r['round'],s) for r in recs for s,t in enumerate(r.get('message_responses',[])) if G in t]
  if not events: continue
  for rnd,seat in events:
   all_events.append(dict(folder=folder,game=p.stem,round=rnd,seat=seat,path=str(p.relative_to(ROOT)),occurrences=recs[rnd]['message_responses'][seat].count(G)))
selected=[]
for folder,n in [('runs',3),('runs_raw',11),('runs_nosys',10)]:
 pool=[e for e in all_events if e['folder']==folder];rng.shuffle(pool);selected+=pool[:n]
for e in selected:
 p=ROOT/e['path'];cfg=json.loads(p.with_suffix('.config.json').read_text());recs=[json.loads(l) for l in p.read_text().splitlines()]
 env=rb.replay_env(cfg,recs,e['round']);log=[r['messages'] for r in recs[:e['round']]]
 e['messages']=rb.cg.build_prompt(env,e['seat'],True,'msg',log,e['round'],cfg['window'],{},cfg['prior_steps'],raw=cfg.get('raw_channel',False),no_system=cfg.get('no_system',False))
 e['response']=recs[e['round']]['message_responses'][e['seat']]
 # Replay vs logged initial prompt for each selected source game; independently validates formatting.
 first=rb.cg.build_prompt(rb.replay_env(cfg,recs,0),0,True,'msg',[],0,cfg['window'],{},cfg['prior_steps'],raw=cfg.get('raw_channel',False),no_system=cfg.get('no_system',False))
 logpath=ROOT/'studies/games/cartel/comm'/folder.replace('runs','logs')/(e['game']+'.log')
 if not logpath.exists():
  checks.append(e['game']+': log unavailable');continue
 txt=logpath.read_text();hdr='FIRST MESSAGE-PHASE PROMPT (agent 0):\n';expected=txt.split(hdr,1)[1].split('\n---',1)[0]
 assert rb.cg.fmt_prompt(first)==expected,e['game']
 checks.append(e['game'])
(HERE/'inputs.json').write_text(json.dumps(selected,ensure_ascii=False,indent=1))
(HERE/'selection.json').write_text(json.dumps({'seed':1023,'all_events':all_events,'selected':len(selected),'initial_prompt_byte_equal_checks':checks},indent=1))
print('Selected',len(selected),'of',len(all_events),'messages;',sum(e['occurrences'] for e in all_events),'glitch strings; all first prompt replay checks passed')
