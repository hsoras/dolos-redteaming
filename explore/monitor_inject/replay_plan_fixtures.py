"""Offline collision, prompt-binding, stage-identity and completeness fixtures."""
from replay_plan import build_plan,validate_samples,canonical_sha,gate_status
from common import CALIBRATION_SYSTEM
from run import load_bank
bank={x['item_id']:x for x in load_bank()}
base={'source':'dolos','item_id':'c04_sus','style':'user_like','sample_idx':0,'original_attack_id':'draft-1','message':'sample note','stage':'original'}
plan=build_plan([base,{**base,'stage':'revision','original_attack_id':'draft-1|revision','message':'revised note'}],bank)
assert len(plan)==8 and len({x['candidate_id'] for x in plan})==2 and len({x['sample_id'] for x in plan})==8
assert all(x['messages'][0]=={'role':'system','content':CALIBRATION_SYSTEM} and x['input_sha256']==canonical_sha(x['messages']) for x in plan)
try: build_plan([base,base],bank)
except ValueError: pass
else: raise AssertionError('duplicate candidate accepted')
expected={x['sample_id'] for x in plan[:4]}
validate_samples([{'id':x} for x in expected],expected)
for bad in ([{'id':x} for x in list(expected)[:-1]], [{'id':x} for x in list(expected)+[next(iter(expected))]]):
 try: validate_samples(bad,expected)
 except ValueError: pass
 else: raise AssertionError('incomplete/duplicate sample set accepted')
passed,detail=gate_status()
assert not passed and set(detail)=={'dolos','qwen'}
print('replay plan fixtures passed; gate remains blocked:',detail)
