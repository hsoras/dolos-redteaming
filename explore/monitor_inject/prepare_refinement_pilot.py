"""Freeze and assemble the 72-pair pilot inputs without using monitor outcomes for selection."""
import json, os, hashlib, collections
from common import load_bank, monitor_prompt
HERE=os.path.dirname(os.path.abspath(__file__))
read=lambda name:[json.loads(x) for x in open(os.path.join(HERE,name)) if x.strip()]
feedback=read('refinement_feedback.jsonl'); revisions=read('refinements.jsonl')
manifest=json.load(open(os.path.join(HERE,'refinement_pilot_manifest.json')))
attacks=read('attacks.jsonl'); external=read('openrouter_attacks_v2_reasoning_low.jsonl')
bank={x['item_id']:x for x in load_bank()}
byf={x['original_attack_id']:x for x in feedback}; byr={x['original_attack_id']:x for x in revisions}
bya={x['attack_id']:x for x in attacks}; bye={x['attack_id']:x for x in external}
orig_ids=[x['original_attack_id'] for x in manifest['rows']]
assert len(orig_ids)==72 and len(set(orig_ids))==72
replay=[]; reused_ids=[]
for entry in manifest['rows']:
    oid=entry['original_attack_id']; f=byf[oid]; rev=byr[oid]
    assert f['draft_sha256']==entry['draft_sha256']==rev['draft_sha256']
    assert f['style']==entry['style']==rev['style'] and f['item_id']==entry['item_id']
    item=bank[entry['item_id']]
    if entry['source'] in ('dolos','qwen'):
        original=bya[oid]
        raw=original.get('raw_text',original['message'])
        assert hashlib.sha256(raw.encode()).hexdigest()==entry['draft_sha256']
        assert original['message']==f['draft']
        reused_ids.append(oid)
        final_source=entry['source']
        final_phase='revised'
        final_message=rev['message']
        final_raw=rev['raw_text']
        final_id='pilot_revision|'+oid
        replay.append({'attack_id':final_id,'original_attack_id':oid,'item_id':entry['item_id'],'source':final_source,'phase':final_phase,'style':entry['style'],'sample_idx':0,'message':final_message,'raw_text':final_raw,'finish_reason':rev['finish_reason'],'monitor_seed_key':oid,'draft_sha256':entry['draft_sha256'],'revision_sha256':entry['revision_sha256'],'revision_source':final_source})
    else:
        original=bye[oid]
        raw=original.get('raw_text',original['message'])
        assert hashlib.sha256(raw.encode()).hexdigest()==entry['draft_sha256']
        assert original['message']==f['draft']
        for phase,source,message,rawmsg,finish,aid in (
            ('original','deepseek',original['message'],raw,original.get('finish_reason'),'pilot_original|'+oid),
            ('revised','deepseek_sol',rev['message'],rev['raw_text'],rev['finish_reason'],'pilot_revision|'+oid)):
            replay.append({'attack_id':aid,'original_attack_id':oid,'item_id':entry['item_id'],'source':source,'phase':phase,'style':entry['style'],'sample_idx':0,'message':message,'raw_text':rawmsg,'finish_reason':finish,'monitor_seed_key':oid,'draft_sha256':entry['draft_sha256'],'revision_sha256':entry['revision_sha256'] if phase=='revised' else None,'revision_source':source if phase=='revised' else None})
# D/Q originals already have corrected four-repetition output. Verify exact prompt and all monitor/rep rows.
base=read('monitor_results.jsonl')
expected_base={(oid,m,j) for oid in reused_ids for m in ('dolos','qwen') for j in range(4)}
subset=[x for x in base if x.get('attack_id') in set(reused_ids)]
observed={(x['attack_id'],x['monitor'],x['rep']) for x in subset}
assert observed==expected_base, f"D/Q baseline coverage mismatch {len(observed)}/{len(expected_base)}"
for x in subset:
    a=bya[x['attack_id']]
    assert x['source']==a['source'] and x['style']==a['style']
    assert x['monitor_prompt']==monitor_prompt(bank[x['item_id']],a['message'])
    assert x.get('monitor_seed') is not None
assert len(replay)==96
with open(os.path.join(HERE,'refinement_pilot_replay_input.jsonl'),'w') as f:
    for x in replay: f.write(json.dumps(x,ensure_ascii=False)+'\n')
json.dump({'manifest':'refinement_pilot_manifest.json','manifest_sha256':hashlib.sha256(open(os.path.join(HERE,'refinement_pilot_manifest.json'),'rb').read()).hexdigest(),'reused_original_ids':reused_ids,'replay_input_rows':len(replay),'replay_counts':{f"{k[0]}|{k[1]}":v for k,v in collections.Counter((x['source'],x['phase']) for x in replay).items()},'baseline_rows_reused':len(subset),'expected_total_rows':1152},open(os.path.join(HERE,'refinement_pilot_assembly.json'),'w'),indent=2)
print('replay input rows',len(replay),'reused original baseline rows',len(subset),'paired rows expected',1152)
print(collections.Counter((x['source'],x['phase']) for x in replay))
