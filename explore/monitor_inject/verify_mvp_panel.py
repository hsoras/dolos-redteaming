"""Offline verification of the reduced final-text panel; performs no model calls."""
import ast,hashlib,json,os,collections,re
from common import load_bank,monitor_prompt
HERE=os.path.dirname(os.path.abspath(__file__))
def sha(p): return hashlib.sha256(open(os.path.join(HERE,p),'rb').read()).hexdigest()
def read(p): return [json.loads(x) for x in open(os.path.join(HERE,p)) if x.strip()]
feedback=read('refinement_feedback.jsonl'); fby={x['original_attack_id']:x for x in feedback}
full=read('refinements.jsonl'); rby={x['original_attack_id']:x for x in full}
finals=read('mvp_refinements.jsonl'); manifest=json.load(open(os.path.join(HERE,'mvp_panel_manifest.json')))
orig_local={x['attack_id']:x for x in read('attacks.jsonl')}
orig_ds={x['attack_id']:x for x in read('openrouter_attacks_v2_reasoning_low.jsonl')}
bank={x['item_id']:x for x in load_bank()}
if len(feedback)!=360 or len(full)!=360 or len(finals)!=72: raise ValueError('Wrong frozen feedback/full-final/reduced-panel row count')
if len({x['attack_id'] for x in finals})!=72: raise ValueError('Duplicate final candidate IDs')
if manifest['candidates']!=72 or manifest['item_ids']!=sorted({x['item_id'] for x in finals}): raise ValueError('Reduced manifest join failure')
cal=set(manifest['calibration_development_families']); fams=set(manifest['families'])
if cal & fams: raise ValueError('Calibration and pilot families overlap')
counts=collections.Counter((x['source'],x['style']) for x in finals)
if any(counts[(s,t)]!=12 for s in ('dolos','qwen','deepseek_sol') for t in ('user_like','system_like')): raise ValueError('Source/style strata incomplete')
if {x['sample_idx'] for x in finals}!={0}: raise ValueError('Pilot includes nonzero sample indexes')
checks=[]; ast_ok=0; ast_bad=[]; over80=[]; role_strings=[]
for x in finals:
 oid=x['original_attack_id']; f=fby[oid]; r=rby[oid]
 if x['draft_sha256']!=f['draft_sha256'] or r['draft_sha256']!=f['draft_sha256']: raise ValueError('Original-byte hash mismatch: '+oid)
 if x['feedback_sha256']!=hashlib.sha256(f['feedback'].encode()).hexdigest(): raise ValueError('Feedback hash mismatch: '+oid)
 if x['message']!=r['message']: raise ValueError('Final text changed during extraction: '+oid)
 draft_source=x['draft_source']; src=orig_local if draft_source in ('dolos','qwen') else orig_ds
 original=src[oid]
 raw=original.get('raw_text',original['message'])
 if hashlib.sha256(raw.encode()).hexdigest()!=x['draft_sha256']: raise ValueError('Original source byte mismatch: '+oid)
 if x['source']=='deepseek_sol' and x['external_final_sha256']!=hashlib.sha256(x['message'].encode()).hexdigest(): raise ValueError('DeepSeek+Sol final hash mismatch: '+oid)
 if len(x['message'].split())>80: over80.append(oid)
 if '<|im_' in x['message']: role_strings.append(oid)
 item=bank[x['item_id']]
 prompt=monitor_prompt(item,x['message'])
 draft_prompt=monitor_prompt(item,f['draft'])
 rec={'candidate_id':hashlib.sha256(('mvp_final|'+oid+'|'+hashlib.sha256(x['message'].encode()).hexdigest()).encode()).hexdigest(),
      'stage':'final','attack_id':x['attack_id'],'original_attack_id':oid,'item_id':x['item_id'],'family':next(q for q in manifest['families'] if x['item_id'].startswith(q+'_')),
      'source':x['source'],'draft_source':draft_source,'style':x['style'],'sample_idx':0,'draft_sha256':x['draft_sha256'],
      'final_sha256':hashlib.sha256(x['message'].encode()).hexdigest(),'feedback_sha256':x['feedback_sha256'],
      'pilot_manifest_sha256':sha('mvp_panel_manifest.json'),'generation_protocol_sha256':sha('refinement_review.md'),
      'failed_calibration_protocol_sha256':sha('CALIBRATION_PREREG.md'),'receiver_builder':'common.monitor_prompt historical one-user format; ineligible after failed calibration',
      'draft_receiver_prompt_sha256':hashlib.sha256(draft_prompt.encode()).hexdigest(),'final_receiver_prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
      'monitor_evaluation_status':'blocked_by_failed_calibration_gate; no authorized replay'}
 checks.append(rec)
 if item['kind']=='code':
  code=prompt.split('```python\n',1)[1].split('\n```',1)[0]
  try:
   good=ast.dump(ast.parse(code),include_attributes=False)==ast.dump(ast.parse(item['body']),include_attributes=False)
  except SyntaxError: good=False
  if good: ast_ok+=1
  else: ast_bad.append(oid)
 else:
  if item['body'] not in prompt: raise ValueError('Action body changed: '+oid)
if ast_bad: raise ValueError(f'Code AST changed in {len(ast_bad)} candidates')
with open(os.path.join(HERE,'mvp_panel_candidate_ids.jsonl'),'w') as out:
 for row in checks: out.write(json.dumps(row,ensure_ascii=False)+'\n')
validation={'status':'PASS_OFFLINE_PANEL_VALIDATION_ONLY','rows':len(finals),'unique_candidate_ids':len({x['candidate_id'] for x in checks}),
 'source_counts':dict(collections.Counter(x['source'] for x in finals)),'source_style_counts':{f'{k[0]}|{k[1]}':v for k,v in counts.items()},
 'items':sorted({x['item_id'] for x in finals}),'families':sorted(fams),'calibration_development_families':sorted(cal),
 'family_overlap':sorted(fams&cal),'sample_indexes':[0],'full_feedback_rows_preserved':len(feedback),'full_final_rows_preserved':len(full),
 'draft_hash_and_source_byte_joins':'72/72 exact','feedback_hash_joins':'72/72 exact','deepseek_sol_final_hash_joins':sum(x['source']=='deepseek_sol' for x in finals),
 'ast_equivalent_code_variants':ast_ok,'code_ast_failures':ast_bad,'action_bodies_exact':True,'over_80_word_outputs':over80,'literal_role_delimiter_outputs':role_strings,
 'manifest_sha256':sha('mvp_panel_manifest.json'),'finals_sha256':sha('mvp_refinements.jsonl'),'candidate_ids_sha256':sha('mvp_panel_candidate_ids.jsonl'),
 'evaluation':'blocked; historical one-user results are uncalibrated and are not joined or reused'}
json.dump(validation,open(os.path.join(HERE,'mvp_panel_validation.json'),'w'),indent=2)
print(json.dumps(validation,indent=2))
