"""Cell-completeness fixtures for the historical analysis pipeline."""
from analyze import validate_result_cells
base=[{'monitor':m,'attack_id':'candidate-A','rep':r} for m in ('dolos','qwen') for r in range(4)]
validate_result_cells(base,{'candidate-A'})
for label,bad in [('missing',base[:-1]),('duplicate',base+[base[0]]),('unexpected',base+[{'monitor':'dolos','attack_id':'candidate-B','rep':0}])]:
    try: validate_result_cells(bad,{'candidate-A'})
    except ValueError: continue
    raise AssertionError(f'{label} cell set was accepted')
print('complete, missing, duplicate, and unexpected cell fixtures passed')
