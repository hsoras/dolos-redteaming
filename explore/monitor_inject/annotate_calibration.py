"""Create immutable identity/hash sidecars for the completed calibration development run."""
import hashlib,json,os,collections
HERE=os.path.dirname(os.path.abspath(__file__))
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
raw_path=os.path.join(HERE,'calibration_gate.jsonl'); meta_path=os.path.join(HERE,'calibration_gate_metadata.json')
raw_hash=sha_bytes(open(raw_path,'rb').read()); meta=json.load(open(meta_path))
# Hash the exact preregistered gate section as it stood before any result-triggered amendments.
prereg=open(os.path.join(HERE,'CALIBRATION_PREREG.md'),encoding='utf8').read()
marker='\n## Gate-failure exact-output canary amendment'
if marker not in prereg: raise ValueError('Cannot locate post-run amendment boundary')
gate_prereg=prereg.split(marker,1)[0].rstrip()+'\n'
prereg_hash=sha_bytes(gate_prereg.encode())
protocol={"protocol_id":"calibration_gate_original_preregistered_v1","protocol_sha256":prereg_hash,"run_metadata_sha256":sha_bytes(open(meta_path,'rb').read()),"raw_results_sha256":raw_hash,"results_sha256_is_not_an_input_hash":True,"status":"completed development/gate run; failed; no monitor result reuse authorized","monitor_family_lists":{"development":["c01","c02","c03","e2_01","e2_02","e2_03"],"disjoint_pilot":["c04","c05","c06","e2_04","e2_05","e2_06"]},"sampling":{k:meta.get(k) for k in ("temperature","top_p","top_k","max_tokens","seed","request_order_seed")},"models":meta.get('models'),"model_revisions":meta.get('revisions'),"system_rubric":meta.get('system_rubric')}
json.dump(protocol,open(os.path.join(HERE,'calibration_protocol_manifest.json'),'w'),indent=2)
rows=[json.loads(x) for x in open(raw_path) if x.strip()]
if len(rows)!=192:raise ValueError(f'Expected 192 scheduled calibration outputs, got {len(rows)}')
ids=[]; out=[]
for r in rows:
    prompt_hash=sha_bytes(r['rendered_prompt'].encode())
    token_hash=sha_bytes(json.dumps(r['input_token_ids'],separators=(',',':')).encode())
    candidate=sha_bytes('|'.join(('development_calibration',r['monitor'],r['arm'],r['item_id'],str(r['rep']),prompt_hash,prereg_hash)).encode())
    result=sha_bytes('|'.join((candidate,prompt_hash,token_hash,r['monitor'],str(r['rep']))).encode())
    ids.append(result)
    out.append({**r,"stage":"development_calibration","protocol_id":protocol['protocol_id'],"protocol_sha256":prereg_hash,"raw_results_sha256":raw_hash,"rendered_input_sha256":prompt_hash,"input_token_ids_sha256":token_hash,"candidate_id":candidate,"result_id":result,"eligible_for_safety_result_reuse":False})
if len(set(ids))!=192:raise ValueError('Duplicate calibration result identity')
p=os.path.join(HERE,'calibration_gate_identified.jsonl')
with open(p,'w') as f:
 for r in out:f.write(json.dumps(r,ensure_ascii=False)+'\n')
print('identified calibration rows',len(out),'unique result IDs',len(set(ids)),'protocol',prereg_hash,'raw',raw_hash)
