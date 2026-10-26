"""Prefill sweep + teacher-forced likelihood scan: Dolos-1.5B and Qwen2.5-1.5B-Instruct on ONE H100 container.

Run from the repo root (ephemeral app: it stops when the local entrypoint returns):
    modal run experiments/sarosh/diagnostics/scan_prefill/scan_modal.py
Reads bank.jsonl and scan_items.jsonl; writes out/generations.jsonl, out/scan.jsonl, out/run_meta.json
incrementally (one line per record as it arrives). Weights come from the existing read-only volume
dolos-qwen-models (populated by diagnostics/setup/bootstrap_model_cache.py at pinned revisions).
Hard watchdog: function timeout 1200 s (~$1.46 at H100 + 4 vCPU + 32 GiB overhead).
"""
import json, os, time
import modal

ROOT = "/models"
VOL = modal.Volume.from_name("dolos-qwen-models")
TIMEOUT_S = 1200
DEFAULT_SYS = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
# identical to explore/cartel/comm/comm_game.py NOSYS_TEMPLATE: single user turn, no system block
NOSYS_TEMPLATE = ("{% for m in messages %}<|im_start|>{{ m['role'] }}\n{{ m['content'] }}<|im_end|>\n{% endfor %}"
                  "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}")
EOS_IDS = [151645, 151643]  # <|im_end|>, <|endoftext|>
SEED = 20261025
SAMPLES_PER_ITEM = 3
ITEMS_PER_BATCH = 32
MAX_NEW = 128
MAX_TOTAL = 2048

image = (modal.Image.debian_slim(python_version="3.12")  # same definition as serve_dolos_qwen.py: cached image
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub", "fastapi", "httpx", "uvicorn")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(os.environ.get("MODAL_APP_NAME", "scan-prefill-explore"), image=image)


def _render(tok, user, system_mode, prefill):
    msgs = [{"role": "user", "content": user}]
    if system_mode == "default":
        s = tok.apply_chat_template([{"role": "system", "content": DEFAULT_SYS}] + msgs,
                                    tokenize=False, add_generation_prompt=True)
    else:
        s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, chat_template=NOSYS_TEMPLATE)
        assert "You are Qwen" not in s and "<|im_start|>system" not in s, "no-system render leaked a system block"
    return s + prefill


def _load(name):
    """Load one model; tie embeddings only if the checkpoint has no separate lm_head that differs from embed_tokens."""
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


@app.function(gpu="H100", volumes={ROOT: VOL}, timeout=TIMEOUT_S, max_containers=1, scaledown_window=30)
def run(bank, scan_items):
    import torch
    from transformers import AutoTokenizer
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(f"{ROOT}/qwen", local_files_only=True)
    pad = tok.pad_token_id if tok.pad_token_id is not None else EOS_IDS[1]
    tok.padding_side = "left"
    yield {"stage": "meta", "t_s": 0.0, "n_bank": len(bank), "n_scan": len(scan_items), "timeout_s": TIMEOUT_S,
           "gpu": "H100", "max_new_tokens": MAX_NEW, "sampling": "temperature=1.0 top_p=1.0 top_k=0 (pure sampling)",
           "samples_per_item": SAMPLES_PER_ITEM, "seed_base": SEED}
    models = {}
    for name in ("dolos", "qwen"):
        models[name], facts = _load(name)
        yield {"stage": "load", "t_s": round(time.time() - t0, 1), **facts}

    # ---- stage 1: prefill / elicitation generation (both models, both system modes, 3 samples each)
    batch_no = 0
    for name in ("dolos", "qwen"):
        for mode in ("default", "none"):
            for start in range(0, len(bank), ITEMS_PER_BATCH):
                chunk = bank[start:start + ITEMS_PER_BATCH]
                rows = []
                for it in chunk:
                    text = _render(tok, it["user"], mode, it["prefill"])
                    ids = tok(text, add_special_tokens=False).input_ids
                    for s in range(SAMPLES_PER_ITEM):
                        rows.append({"item_id": it["item_id"], "category": it["category"], "control": it["control"],
                                     "provenance": it["provenance"], "status": it.get("status"), "model": name,
                                     "system_mode": mode, "sample_idx": s, "prefill": it["prefill"], "rendered_input": text,
                                     "input_ids": ids})
                seed = SEED + batch_no
                maxlen = max(len(r["input_ids"]) for r in rows)
                inp = torch.full((len(rows), maxlen), pad, dtype=torch.long)
                att = torch.zeros((len(rows), maxlen), dtype=torch.long)
                for i, r in enumerate(rows):
                    inp[i, maxlen - len(r["input_ids"]):] = torch.tensor(r["input_ids"])
                    att[i, maxlen - len(r["input_ids"]):] = 1
                torch.manual_seed(seed)
                with torch.inference_mode():
                    out = models[name].generate(input_ids=inp.cuda(), attention_mask=att.cuda(), do_sample=True,
                                                temperature=1.0, top_p=1.0, top_k=0, max_new_tokens=MAX_NEW,
                                                eos_token_id=EOS_IDS, pad_token_id=pad)
                gen = out[:, maxlen:].cpu().tolist()
                for r, g in zip(rows, gen):
                    cut = next((j for j, t in enumerate(g) if t in EOS_IDS), None)
                    ids_out = g[:cut + 1] if cut is not None else g
                    r["output_ids"] = ids_out
                    r["finish_reason"] = "stop" if cut is not None else "length"
                    r["n_output_tokens"] = len(ids_out)
                    r["completion_text"] = tok.decode(ids_out, skip_special_tokens=True)
                    r["full_text"] = r["prefill"] + r["completion_text"]
                    r["batch_no"] = batch_no
                    r["batch_seed"] = seed
                    r["batch_size"] = len(rows)
                    r["stage"] = "gen"
                    r["t_s"] = round(time.time() - t0, 1)
                    yield r
                batch_no += 1

    # ---- stage 2: teacher-forced log-probs of target tokens only (float32 log_softmax)
    for name in ("dolos", "qwen"):
        m = models[name]
        for mode in ("default", "none"):
            for it in scan_items:
                prompt = _render(tok, it["prompt"], mode, "")
                p_ids = tok(prompt, add_special_tokens=False).input_ids
                t_ids = tok(it["target"], add_special_tokens=False).input_ids
                rec = {"stage": "scan", "model": name, "system_mode": mode, "scan_id": it["scan_id"],
                       "category": it["category"], "pair_role": it["pair_role"], "order": it["order"],
                       "n_prompt_tokens": len(p_ids), "n_target_tokens": len(t_ids), "target": it["target"],
                       "provenance": it["provenance"], "source_file": it["source_file"], "source_index": it["source_index"],
                       "t_s": round(time.time() - t0, 1)}
                if len(t_ids) == 0 or len(p_ids) + len(t_ids) > MAX_TOTAL:
                    rec["skipped"] = "empty_target" if not t_ids else "over_max_total"
                    yield rec
                    continue
                ids = torch.tensor([p_ids + t_ids]).cuda()
                with torch.inference_mode():
                    logits = m(ids).logits[0].float()
                    lp = logits.log_softmax(-1)
                    pos = torch.arange(len(p_ids) - 1, len(p_ids) + len(t_ids) - 1).cuda()
                    tgt = torch.tensor(t_ids).cuda()
                    tok_lp = lp[pos, tgt].cpu().tolist()
                rec["token_logprobs"] = [round(x, 6) for x in tok_lp]
                rec["sum_logprob"] = round(sum(tok_lp), 6)
                rec["mean_logprob"] = round(sum(tok_lp) / len(tok_lp), 6)
                rec["skipped"] = None
                yield rec


@app.local_entrypoint()
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    bank = [json.loads(l) for l in open(os.path.join(here, "bank.jsonl"), encoding="utf-8")]
    scan_items = [json.loads(l) for l in open(os.path.join(here, "scan_items.jsonl"), encoding="utf-8")]
    out_dir = os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    counts = {}
    files = {"gen": open(os.path.join(out_dir, "generations.jsonl"), "w", encoding="utf-8"),
             "scan": open(os.path.join(out_dir, "scan.jsonl"), "w", encoding="utf-8")}
    meta = {}
    try:
        for rec in run.remote_gen(bank, scan_items):
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
            json.dump({"counts": counts, **meta}, f, indent=2)
    print("written", counts, flush=True)
