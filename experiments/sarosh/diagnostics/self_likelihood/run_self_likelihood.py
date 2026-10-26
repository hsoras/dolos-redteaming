"""Self-likelihood MVP: does Dolos-1.5B give its own answers higher likelihood than Qwen2.5-1.5B-Instruct does?

Adapted (copied, not edited) from experiments/sarosh/diagnostics/scan_prefill/scan_modal.py. Run from the repo root (ephemeral app):
    MODAL_APP_NAME=self-likelihood-mvp modal run experiments/sarosh/diagnostics/self_likelihood/run_self_likelihood.py
Design: 30 frozen prompts (bank.csv) x 2 samples x 2 authors = 120 answers. Each answer is scored by BOTH readers,
conditioned on the identical rendered prompt and the identical answer token IDs (240 scores). Only answer tokens are scored.
Hard watchdog: function timeout 600 s, retries 0, one H100 container (<= $0.73 at official rates incl. 4 cores + 32 GiB).
Reads bank.csv; writes out/generations.jsonl and out/scores.jsonl incrementally, plus out/run_meta.json.
"""
import csv, hashlib, json, os, time
import modal

ROOT = "/models"
VOL = modal.Volume.from_name("dolos-qwen-models")
TIMEOUT_S = 600
DEFAULT_SYS = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
EOS_IDS = [151645, 151643]  # <|im_end|>, <|endoftext|>
SEED = 20261025
SAMPLES = 2
TEMP = 0.8
MAX_NEW = 128
MAX_TOTAL = 2048
MODELS = ("dolos", "qwen")
EXPECTED_ROWS = 30

image = (modal.Image.debian_slim(python_version="3.12")  # same definition as scan_modal.py / serve_dolos_qwen.py: cached image
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub", "fastapi", "httpx", "uvicorn")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(os.environ.get("MODAL_APP_NAME", "self-likelihood-mvp"), image=image)


def _render(tok, user):
    msgs = [{"role": "system", "content": DEFAULT_SYS}, {"role": "user", "content": user}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def _load(name):
    """Copied from scan_modal.py: tie embeddings only if the checkpoint has no separate lm_head that differs from embed_tokens."""
    import torch
    from safetensors import safe_open
    from transformers import AutoConfig, AutoModelForCausalLM
    d = f"{ROOT}/{name}"
    with safe_open(f"{d}/model.safetensors", "pt") as f:
        keys = set(f.keys())
        emb = f.get_tensor("model.embed_tokens.weight")
        head = f.get_tensor("lm_head.weight") if "lm_head.weight" in keys else None
    cfg = AutoConfig.from_pretrained(d)
    tied = bool(cfg.tie_word_embeddings)
    if head is not None and not torch.equal(head, emb):
        tied = False  # checkpoint has its own head: keep it, do NOT overwrite it with the embedding
    cfg.tie_word_embeddings = tied
    model, info = AutoModelForCausalLM.from_pretrained(d, config=cfg, dtype=torch.float16, attn_implementation="sdpa",
                                                       local_files_only=True, output_loading_info=True)
    bad = {k: info[k] for k in ("missing_keys", "unexpected_keys", "error_msgs") if info.get(k)}
    if bad:
        raise RuntimeError(f"{name} did not load completely: {bad}")
    if tied:
        model.tie_weights()
    same = model.lm_head.weight.data_ptr() == model.model.embed_tokens.weight.data_ptr()
    facts = {"model": name, "checkpoint_has_lm_head": head is not None,
             "head_equals_embed": None if head is None else bool(torch.equal(head, emb)),
             "tied_in_model": same, "tie_is_correct": (same == tied)}
    assert facts["tie_is_correct"], facts
    return model.cuda().eval(), facts


@app.function(gpu="H100", volumes={ROOT: VOL}, timeout=TIMEOUT_S, max_containers=1, scaledown_window=5)  # no retries (Modal default; generators reject retries=)
def run(prompts):
    import torch
    from transformers import AutoTokenizer
    t0 = time.time()
    # One tokenizer for both readers and both authors (Qwen tokenizer; the Dolos checkpoint is a fine-tune of the same base).
    tok = AutoTokenizer.from_pretrained(f"{ROOT}/qwen", local_files_only=True)
    tok.padding_side = "left"
    pad = EOS_IDS[1]
    yield {"stage": "meta", "t_s": 0.0, "n_prompts": len(prompts), "samples": SAMPLES, "temperature": TEMP,
           "max_new_tokens": MAX_NEW, "seed_base": SEED, "timeout_s": TIMEOUT_S, "gpu": "H100",
           "system_mode": "default", "tokenizer": "qwen", "score_target": "answer tokens only, float32 log_softmax"}
    models = {}
    for name in MODELS:
        models[name], facts = _load(name)
        yield {"stage": "load", "t_s": round(time.time() - t0, 1), **facts}
    assert models["dolos"].config.vocab_size == models["qwen"].config.vocab_size, "readers have different vocab sizes"

    # ---- stage 1: generation, each author samples SAMPLES answers per prompt at temperature 0.8
    gen_rows = []
    for g_idx, author in enumerate(MODELS):
        rows = []
        for it in prompts:
            text = _render(tok, it["user_text"])
            ids = tok(text, add_special_tokens=False).input_ids
            for s in range(SAMPLES):
                rows.append({"prompt_id": it["prompt_id"], "category": it["category"], "author": author,
                             "sample_id": s, "rendered_prompt": text, "input_ids": ids})
        seed = SEED + g_idx
        maxlen = max(len(r["input_ids"]) for r in rows)
        inp = torch.full((len(rows), maxlen), pad, dtype=torch.long)
        att = torch.zeros((len(rows), maxlen), dtype=torch.long)
        for i, r in enumerate(rows):
            inp[i, maxlen - len(r["input_ids"]):] = torch.tensor(r["input_ids"])
            att[i, maxlen - len(r["input_ids"]):] = 1
        torch.manual_seed(seed)
        with torch.inference_mode():
            out = models[author].generate(input_ids=inp.cuda(), attention_mask=att.cuda(), do_sample=True,
                                          temperature=TEMP, top_p=1.0, top_k=0, max_new_tokens=MAX_NEW,
                                          eos_token_id=EOS_IDS, pad_token_id=pad)
        gen = out[:, maxlen:].cpu().tolist()
        for r, g in zip(rows, gen):
            cut = next((j for j, t in enumerate(g) if t in EOS_IDS), None)
            ids_out = g[:cut + 1] if cut is not None else g
            assert len(ids_out) >= 1
            r["output_ids"] = ids_out
            r["finish_reason"] = "stop" if cut is not None else "length"
            r["n_output_tokens"] = len(ids_out)
            r["completion_text"] = tok.decode(ids_out, skip_special_tokens=True)
            r["is_empty_text"] = r["completion_text"].strip() == ""
            r["seed"] = seed
            r["stage"] = "gen"
            r["t_s"] = round(time.time() - t0, 1)
            gen_rows.append(r)
            yield r

    # ---- stage 2: both readers score every answer; identical prompt IDs and identical answer IDs for both readers
    for reader in MODELS:
        m = models[reader]
        for r in gen_rows:
            p_ids, a_ids = r["input_ids"], r["output_ids"]
            assert len(p_ids) + len(a_ids) <= MAX_TOTAL
            ids = torch.tensor([p_ids + a_ids]).cuda()
            with torch.inference_mode():
                lp = m(ids).logits[0].float().log_softmax(-1)
                pos = torch.arange(len(p_ids) - 1, len(p_ids) + len(a_ids) - 1).cuda()
                tgt = torch.tensor(a_ids).cuda()
                tok_lp = lp[pos, tgt].cpu().tolist()
            # target-mask check: scored positions are exactly the answer tokens, in order
            assert ids[0, len(p_ids):].tolist() == a_ids
            assert len(tok_lp) == len(a_ids) == r["n_output_tokens"]
            yield {"stage": "score", "reader": reader, "author": r["author"], "prompt_id": r["prompt_id"],
                   "sample_id": r["sample_id"], "seed": r["seed"], "finish_reason": r["finish_reason"],
                   "n_prompt_tokens": len(p_ids), "n_answer_tokens": len(a_ids),
                   "sum_logprob": round(sum(tok_lp), 6), "mean_logprob": round(sum(tok_lp) / len(tok_lp), 6),
                   "token_logprobs": [round(x, 6) for x in tok_lp], "answer_ids": a_ids,
                   "t_s": round(time.time() - t0, 1)}


@app.local_entrypoint()
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    bank_path = os.path.join(here, "bank.csv")
    with open(bank_path, "rb") as f:
        bank_sha = hashlib.sha256(f.read()).hexdigest()
    frozen = open(os.path.join(here, "BANK_FROZEN.sha256"), encoding="utf-8").read().split()[0]
    assert bank_sha == frozen, f"bank.csv changed after freeze: {bank_sha} != {frozen}"
    with open(bank_path, encoding="utf-8", newline="") as f:
        prompts = list(csv.DictReader(f))
    assert len(prompts) == EXPECTED_ROWS, len(prompts)
    assert len({p["prompt_id"] for p in prompts}) == EXPECTED_ROWS
    cats = {}
    for p in prompts:
        cats[p["category"]] = cats.get(p["category"], 0) + 1
    assert cats == {"factual_help": 10, "reasoning_code": 10, "coordination_neutral": 10}, cats

    out_dir = os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    counts, meta = {}, {}
    files = {"gen": open(os.path.join(out_dir, "generations.jsonl"), "w", encoding="utf-8"),
             "score": open(os.path.join(out_dir, "scores.jsonl"), "w", encoding="utf-8")}
    try:
        for rec in run.remote_gen(prompts):
            st = rec["stage"]
            if st in ("meta", "load"):
                meta.setdefault(st, []).append(rec)
                print(json.dumps(rec), flush=True)
                continue
            files[st].write(json.dumps(rec, ensure_ascii=False) + "\n")
            files[st].flush()
            counts[st] = counts.get(st, 0) + 1
    finally:
        for f in files.values():
            f.close()
        with open(os.path.join(out_dir, "run_meta.json"), "w") as f:
            json.dump({"counts": counts, "bank_sha256": bank_sha, "app_name": app.name, **meta}, f, indent=2)
    print("written", counts, flush=True)
