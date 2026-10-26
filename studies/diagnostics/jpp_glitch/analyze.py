"""Summarize saved J++ measurements; no additional GPU calls."""
import collections
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / 'results.json').read_text())
rows = r['rows']
assert len(r['sequences']) == 24
assert len(rows) == 24 * 2 * 7 * 7 * 2
assert len(r['sanity']) == 2
assert all(x['identity_logits_maxabs'] < 1e-4 for x in r['sanity'])
groups = collections.defaultdict(list)
for x in rows:
    groups[(x['model'], x['readout'], x['variant'], x['position'], x['layer'])].append(x)

summary = []
for key, xs in groups.items():
    assert len(xs) == 24
    for tid in (30625, 151643, 151644, 151645):
        ps = [x['targets'][str(tid)]['p'] for x in xs]
        summary.append(dict(zip(('model','readout','variant','position','layer'),key),
                            token_id=tid, mean_p=sum(ps)/len(ps),
                            geometric_mean_p=math.exp(sum(math.log(max(p,1e-45)) for p in ps)/len(ps)),
                            median_p=sorted(ps)[len(ps)//2], max_p=max(ps)))
(HERE/'summary.json').write_text(json.dumps(summary, indent=2))

lines = ['# J++ through natural cartel glitches', '',
         '**Result:** Dolos strongly predicts 30625 at selected natural-glitch boundaries, but the J++ layer trajectory depends heavily on the lens/readout and is not reliable mechanistic localization. The short continuation interventions show punctuation/template effects without generating a new role delimiter.', '',
         'Immediately before the forced glitch boundary, 30625 is Dolos\'s top prediction in 17/24 cases (median probability 78.5%), versus 0/24 for Qwen. Four token positions earlier it is top-ranked in neither model. This is conditional on selecting messages containing the glitch, not an unconditional emission rate.', '',
         'Native Dolos J++ mean probabilities are non-monotonic: 34.7% at layer 18, 0.0000819% at layer 26, then actual final output 63.8%. Using the fixed Qwen transport, norm, and head on Dolos activations gives 0.0267% at layer 27. These readout-sensitive results cannot establish the layer where a hidden objective or turn transition is computed.', '',
         'After the glitch, common top predictions include `My`, `[`, `Please`, and `Thank` for both models. New-turn `<|im_start|>` probability stays low (Dolos mean 0.000511%, max 0.0111% immediately after the glitch). Across the 24 short greedy continuation branches, no `<|im_start|>` was emitted; many branches do emit normal `<|im_end|>`. Generation stops on configured EOS IDs, so it does not test continuation beyond EOS.', '',
         f"Actual H100 runtime: {r['seconds']:.1f} seconds. 24 sampled messages; two models; 7 layers; native and fixed Qwen full readouts.",
         '', '## Actual next-token probabilities (final layer)', '',
         '|Model|Context|Glitch mean P|im_start mean P|im_end mean P|endoftext mean P|',
         '|---|---|---:|---:|---:|---:|']
for model in ('qwen','dolos'):
    for variant,pos in [('recorded','before'),('recorded','after'),('comma','after'),('comma_2nl','after'),('4nl','after')]:
        xs=groups[(model,'native_jpp',variant,pos,27)]
        vals=[sum(x['targets'][str(t)]['p'] for x in xs)/24 for t in (30625,151644,151645,151643)]
        lines.append('|'+ '|'.join([model,f'{variant}/{pos}']+[f'{v:.3g}' for v in vals])+'|')
lines += ['', '## Before-token J++ trajectory', '',
          'Mean probability of 30625 across the same 24 prefixes. Intermediate values are lens projections; layer 27 native is actual output.', '',
          '|Model|Readout|10|14|18|22|24|26|27|','|---|---|---:|---:|---:|---:|---:|---:|---:|']
for model in ('qwen','dolos'):
    for readout in ('native_jpp','fixed_qwen_jpp_norm_head'):
        vals=[sum(x['targets']['30625']['p'] for x in groups[(model,readout,'recorded','before',l)])/24 for l in (10,14,18,22,24,26,27)]
        lines.append('|'+ '|'.join([model,readout]+[f'{v:.3g}' for v in vals])+'|')
lines += ['', '## Greedy intervention continuations', '',
          'Four selected events, same pre-glitch prefix, forced suffix then up to 32 generated tokens. These test local continuation changes, not game outcomes.']
for g in r['generations']:
    lines += ['', f"Event {g['event']} / {g['model']} / {g['forced']}", '```text',g['text'],'```']
lines += ['', '## Sanity checks', '', '```json',json.dumps(r['sanity'],indent=2),'```',
          '', '## Interpretation limits', '',
          'Selection is conditional on Dolos having emitted the glitch. Qwen receives those same Dolos-authored prefixes. Differences do not measure unconditional emission rates.',
          f"Recorded outputs were re-tokenized, not recovered original generated IDs. Explicit segmentation at the first visible glitch changed whole-response tokenization in {sum(s['segmentation_changed'] for s in r['sequences'])}/24 examples while preserving exact decoded text. Only the first glitch in each selected message is analyzed.",
          'Role-name token scores and individual delimiter probabilities are not evidence of generating a complete user/assistant turn.',
          'All reported probabilities use the unfiltered vocabulary; any semantic-token masking in the upstream presentation is not applied.',
          'Model weights use the existing dolos-adl-cache created by pinned download code; this run does not independently establish checkpoint weight hashes.',
          'Estimated GPU cost can be computed from runtime; actual billed credits were not queried.']
(HERE/'REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines[:32]))
