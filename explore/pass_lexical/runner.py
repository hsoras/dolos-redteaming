"""PASS-lexical study: exact first-token log-odds for Dolos-1.5B and Qwen2.5-1.5B-Instruct.

Requires a frozen prompts.json + protocol.json (python3 build_prompts.py) first.
Smoke: modal run explore/pass_lexical/runner.py --smoke   (writes smoke_raw.jsonl)
Full:  modal run explore/pass_lexical/runner.py           (writes raw.jsonl; refuses to overwrite)
"""
import gc, hashlib, json, time
from pathlib import Path
import modal

BASE = Path(__file__).resolve().parent
VOL = modal.Volume.from_name('dolos-qwen-models')
IMAGE = (modal.Image.debian_slim(python_version='3.12')
         .pip_install('vllm==0.10.1.1', 'transformers==4.56.2', 'huggingface_hub')
         .env({'HF_HUB_DISABLE_TELEMETRY': '1'}))
app = modal.App('dolos-pass-lexical', image=IMAGE)
LABELS = ['PASS', 'FLAG', 'FAIL', 'SHOOT', 'TRUE', 'FALSE']


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@app.function(gpu='H100', volumes={'/models': VOL}, timeout=3600)
def run(prompts, smoke):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained('/models/qwen')
    label_ids = {lab: tok.encode(lab, add_special_tokens=False) for lab in LABELS}
    assert label_ids['PASS'][0] == 49792 and label_ids['FLAG'][0] == 22542, label_ids
    firsts = [label_ids[lab][0] for lab in LABELS]
    assert len(set(firsts)) == len(firsts), ('first-token collision', label_ids)
    rows_in = prompts['rows']
    if smoke:
        rows_in = [r for r in rows_in if r['item'] in ('qa00', 'qa01', 'qa02', 'qa03', 'sp00', 'sp13')]
    for r in rows_in:
        r['input_token_ids'] = tok.apply_chat_template(r['messages'], add_generation_prompt=True, tokenize=True)
    gen_params = SamplingParams(temperature=0, max_tokens=8, seed=0)
    score_params = SamplingParams(max_tokens=1, temperature=0, prompt_logprobs=0)
    provenance, out_rows = {}, []
    for model in ['qwen', 'dolos']:
        root = Path('/models') / model
        provenance[model] = {'config': json.loads((root / 'config.json').read_text()),
                             'files': [{'name': f.name, 'bytes': f.stat().st_size} for f in sorted(root.iterdir()) if f.is_file()]}
        llm = LLM(model='/models/' + model, tokenizer='/models/qwen', dtype='float16', max_model_len=4096,
                  gpu_memory_utilization=.6, generation_config='vllm', enforce_eager=True, disable_log_stats=True)
        gen_out = llm.generate([TokensPrompt(prompt_token_ids=r['input_token_ids']) for r in rows_in], gen_params, use_tqdm=False)
        score_prompts = []
        for r in rows_in:
            for lab in (r['pos_label'], r['neg_label']):
                score_prompts.append(TokensPrompt(prompt_token_ids=r['input_token_ids'] + [label_ids[lab][0]]))
        score_out = llm.generate(score_prompts, score_params, use_tqdm=False)
        for i, r in enumerate(rows_in):
            text = gen_out[i].outputs[0].text
            verdict = text.strip().strip('.').strip().upper()
            lps = {}
            for j, lab in enumerate((r['pos_label'], r['neg_label'])):
                so = score_out[2 * i + j]
                entry = so.prompt_logprobs[len(r['input_token_ids'])]
                lid = label_ids[lab][0]
                assert lid in entry, (r['id'], lab)
                lps[lab] = entry[lid].logprob
            lp_pos, lp_neg = lps[r['pos_label']], lps[r['neg_label']]
            argmax = r['pos_label'] if lp_pos > lp_neg else r['neg_label']
            out_rows.append({'id': r['id'], 'model': model, 'framing': r['framing'], 'order': r['order'], 'item': r['item'],
                             'truth_pos': r['truth_pos'], 'pos_label': r['pos_label'], 'neg_label': r['neg_label'],
                             'expected': r['expected'], 'text': text, 'verdict': verdict,
                             'valid': verdict in (r['pos_label'], r['neg_label']), 'accurate': verdict == r['expected'],
                             'lp_pos': lp_pos, 'lp_neg': lp_neg, 'logodds_pos': lp_pos - lp_neg,
                             'argmax_label': argmax, 'argmax_accurate': argmax == r['expected'],
                             'input_len': len(r['input_token_ids']), 'finish_reason': gen_out[i].outputs[0].finish_reason})
        if model == 'qwen':
            provenance['rendered_example'] = tok.decode(rows_in[0]['input_token_ids'], skip_special_tokens=False)
        del llm; gc.collect(); torch.cuda.empty_cache()
    return {'rows': out_rows, 'label_token_ids': label_ids, 'provenance': provenance, 'smoke': smoke,
            'n_prompts_per_model': len(rows_in), 'wall_seconds': time.time() - t0}


@app.local_entrypoint()
def main(smoke: bool = False):
    protocol = json.loads((BASE / 'protocol.json').read_text())
    assert sha_file(BASE / 'prompts.json') == protocol['prompts_sha256'], 'prompts.json changed after freeze'
    assert sha_file(BASE / 'runner.py') == protocol['runner_sha256'], 'runner.py changed after freeze'
    out = BASE / ('smoke_raw.jsonl' if smoke else 'raw.jsonl')
    assert not out.exists(), 'refuse overwrite'
    prompts = json.loads((BASE / 'prompts.json').read_text())
    result = run.remote(prompts, smoke)
    rows = result.pop('rows')
    out.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (BASE / ('smoke_metadata.json' if smoke else 'metadata.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(f"wrote {len(rows)} rows to {out.name}")
