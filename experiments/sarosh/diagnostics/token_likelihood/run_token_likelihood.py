"""Token-likelihood study (frozen design, see ANALYSIS_PLAN.md). Descriptive only; not a recognition or collusion test.

Adapted (copied, not imported) from experiments/sarosh/diagnostics/self_likelihood/run_self_likelihood.py. Run from the repo root:
    MODAL_APP_NAME=token-likelihood-2026-10-25 modal run experiments/sarosh/diagnostics/token_likelihood/run_token_likelihood.py --stage check
    MODAL_APP_NAME=token-likelihood-2026-10-25 modal run experiments/sarosh/diagnostics/token_likelihood/run_token_likelihood.py --stage run
--stage check: CPU-only tokenization gate (no GPU). --stage run: generation + scoring on one H100.
Design: 33 base questions x 3 length levels x 2 insertion conditions = 198 user prompts; 2 samples per author per prompt
-> 792 answers. Each answer is scored by both readers under its own condition (1584) and the other condition (1584).
Writes out/tokcheck.json, out/generations.jsonl, out/scores.jsonl, out/vocab.json, out/run_meta.json, out/progress.log.
"""
import csv, hashlib, json, os, time
import modal

ROOT = "/models"
VOL = modal.Volume.from_name("dolos-qwen-models")
TIMEOUT_S = 1800
CHECK_TIMEOUT_S = 600
DEFAULT_SYS = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
EOS_IDS = [151645, 151643]  # <|im_end|>, <|endoftext|>
INSERTION = ",\n\n\n\n"
INSERT_ID = 30625
# v1: trailing period removed so the inserted ",\n\n\n\n" follows a word and tokenizes to 30625 (v0 gate failed; see DECISION.md)
LENGTHS = [("one_sentence", "Answer in one sentence"),
           ("about_100_words", "Answer in about 100 words"),
           ("about_400_words", "Answer in about 400 words")]
SEED = 20261025
SAMPLES = 2
TEMP = 1.0
TOP_P = 1.0
TOP_K = 0
REP_PEN = 1.0
MAX_NEW = 1500
GEN_BATCH = 132
SCORE_CHUNK = 256
MODELS = ("dolos", "qwen")
EXPECTED_BASE = 33
TAIL = INSERTION + "<|im_end|>\n<|im_start|>assistant\n"

image = (modal.Image.debian_slim(python_version="3.12")  # same definition as run_self_likelihood.py: cached image
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub", "fastapi", "httpx", "uvicorn")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(os.environ.get("MODAL_APP_NAME", "token-likelihood"), image=image)


def _expand(bank_rows):
    """Deterministic expansion: base x length x insertion -> prompts (order fixed by bank.csv, then LENGTHS, then insertion 0/1)."""
    prompts = []
    for b in bank_rows:
        for lname, linst in LENGTHS:
            clean = b["base_question"] + " " + linst
            for ins in (0, 1):
                user = clean + (INSERTION if ins else "")
                prompts.append({"prompt_key": f"{b['base_id']}|{lname}|ins{ins}", "base_id": b["base_id"],
                                "category": b["category"], "length_level": lname, "insertion": ins, "user_text": user})
    return prompts


def _load_bank(here):
    with open(os.path.join(here, "bank.csv"), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@app.function(volumes={ROOT: VOL}, timeout=CHECK_TIMEOUT_S, max_containers=1)
def tokcheck(prompts):
    """CPU-only gate: verify 30625 placement and byte-exact round-trip before any GPU work."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(f"{ROOT}/qwen", local_files_only=True)
    ins_alone = tok(INSERTION, add_special_tokens=False).input_ids
    report = {"insertion_repr": repr(INSERTION), "insertion_alone_ids": ins_alone,
              "insertion_alone_decoded": [tok.decode([i]) for i in ins_alone],
              "insert_id": INSERT_ID, "insert_id_decodes_to": tok.decode([INSERT_ID]), "examples": []}
    n_ins_ok, clean_hits, failures = 0, 0, []
    for p in prompts:
        text = tok.apply_chat_template([{"role": "system", "content": DEFAULT_SYS},
                                        {"role": "user", "content": p["user_text"]}],
                                       tokenize=False, add_generation_prompt=True)
        ids = tok(text, add_special_tokens=False).input_ids
        if tok.decode(ids, skip_special_tokens=False) != text:
            failures.append((p["prompt_key"], "round_trip"))
        hits = [k for k, t in enumerate(ids) if t == INSERT_ID]
        if p["insertion"] == 0:
            clean_hits += len(hits)
            continue
        if len(hits) != 1:
            failures.append((p["prompt_key"], f"hits={len(hits)}"))
            continue
        k = hits[0]
        if tok.decode(ids[k:], skip_special_tokens=False) != TAIL:
            failures.append((p["prompt_key"], "tail"))
            continue
        n_ins_ok += 1
        if len(report["examples"]) < 3:
            report["examples"].append({"prompt_key": p["prompt_key"], "tokens_before": [tok.decode([t]) for t in ids[k - 3:k]],
                                       "insert_position": k, "n_prompt_tokens": len(ids)})
    report.update({"n_insertion_prompts_ok": n_ins_ok, "clean_30625_occurrences": clean_hits, "failures": failures})
    report["pass"] = (not failures) and n_ins_ok == sum(p["insertion"] == 1 for p in prompts) and clean_hits == 0
    return report


@app.function(gpu="H100", volumes={ROOT: VOL}, timeout=TIMEOUT_S, max_containers=1, scaledown_window=5)  # no retries
def run(prompts):
    import torch
    from transformers import AutoTokenizer
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(f"{ROOT}/qwen", local_files_only=True)
    tok.padding_side = "left"
    pad = EOS_IDS[1]
    by_key = {}
    for p in prompts:
        text = tok.apply_chat_template([{"role": "system", "content": DEFAULT_SYS},
                                        {"role": "user", "content": p["user_text"]}],
                                       tokenize=False, add_generation_prompt=True)
        ids = tok(text, add_special_tokens=False).input_ids
        by_key[p["prompt_key"]] = dict(p, rendered=text, prompt_ids=ids)
    yield {"stage": "meta", "t_s": 0.0, "n_prompts": len(prompts), "samples": SAMPLES, "temperature": TEMP,
           "top_p": TOP_P, "top_k": TOP_K, "repetition_penalty": REP_PEN, "max_new_tokens": MAX_NEW,
           "seed_base": SEED, "timeout_s": TIMEOUT_S, "gpu": "H100", "system_mode": "default", "tokenizer": "qwen",
           "dtype": "bfloat16", "score_target": "answer tokens only, float32 log_softmax, chunked"}

    def _load(name):
        """Copied from run_self_likelihood.py: tie embeddings only if the checkpoint has no separate lm_head that differs from embed_tokens."""
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
        model, info = AutoModelForCausalLM.from_pretrained(d, config=cfg, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                           local_files_only=True, output_loading_info=True)
        bad = {k: info[k] for k in ("missing_keys", "unexpected_keys", "error_msgs") if info.get(k)}
        if bad:
            raise RuntimeError(f"{name} did not load completely: {bad}")
        if tied:
            model.tie_weights()
        same = model.lm_head.weight.data_ptr() == model.model.embed_tokens.weight.data_ptr()
        facts = {"model": name, "checkpoint_has_lm_head": head is not None,
                 "head_equals_embed": None if head is None else bool(torch.equal(head, emb)),
                 "tied_in_model": same, "tie_is_correct": (same == tied),
                 "generation_config": {k: v for k, v in model.generation_config.to_dict().items()
                                       if k in ("temperature", "top_p", "top_k", "repetition_penalty", "do_sample")}}
        assert facts["tie_is_correct"], facts
        return model.cuda().eval(), facts

    models = {}
    for name in MODELS:
        models[name], facts = _load(name)
        yield {"stage": "load", "t_s": round(time.time() - t0, 1), **facts}
    assert models["dolos"].config.vocab_size == models["qwen"].config.vocab_size, "readers have different vocab sizes"

    def score_answer(m, p_ids, a_ids):
        ids = torch.tensor([p_ids + a_ids], device="cuda")
        with torch.inference_mode():
            h = m.model(input_ids=ids).last_hidden_state[0]
            hs = h[len(p_ids) - 1: len(p_ids) + len(a_ids) - 1]  # position j predicts token j+1
            tgt = torch.tensor(a_ids, device="cuda")
            out = []
            for s in range(0, hs.shape[0], SCORE_CHUNK):
                lg = m.lm_head(hs[s:s + SCORE_CHUNK]).float().log_softmax(-1)
                out.append(lg.gather(-1, tgt[s:s + SCORE_CHUNK, None])[:, 0])
        return torch.cat(out).cpu().tolist()

    # precision check: chunked head vs full-logit path on one real answer (before any scoring)
    m0 = models["dolos"]
    pk = by_key[prompts[0]["prompt_key"]]
    probe_ids = pk["prompt_ids"] + tok("Probe.", add_special_tokens=False).input_ids
    chunked = score_answer(m0, pk["prompt_ids"], probe_ids[len(pk["prompt_ids"]):])
    with torch.inference_mode():
        full = m0(torch.tensor([probe_ids], device="cuda")).logits[0].float().log_softmax(-1)
        ref = [full[len(pk["prompt_ids"]) - 1 + i, probe_ids[len(pk["prompt_ids"]) + i]].item()
               for i in range(len(probe_ids) - len(pk["prompt_ids"]))]
    max_diff = max(abs(a - b) for a, b in zip(chunked, ref))
    yield {"stage": "precision", "max_abs_diff_chunked_vs_full": max_diff}
    assert max_diff < 0.05, max_diff

    # ---- stage 1: generation (author-major; per author 198 prompts x 2 samples, batched)
    gen_rows = []
    keys = [p["prompt_key"] for p in prompts]
    for a_idx, author in enumerate(MODELS):
        rows = [{"prompt_key": k, "sample_id": s} for k in keys for s in range(SAMPLES)]
        pad_pos = [by_key[r["prompt_key"]]["prompt_ids"] for r in rows]
        for b_idx, b0 in enumerate(range(0, len(rows), GEN_BATCH)):
            batch = rows[b0:b0 + GEN_BATCH]
            seqs = pad_pos[b0:b0 + GEN_BATCH]
            seed = SEED + 1000 * a_idx + b_idx
            maxlen = max(len(s) for s in seqs)
            inp = torch.full((len(batch), maxlen), pad, dtype=torch.long)
            att = torch.zeros((len(batch), maxlen), dtype=torch.long)
            for i, s in enumerate(seqs):
                inp[i, maxlen - len(s):] = torch.tensor(s)
                att[i, maxlen - len(s):] = 1
            torch.manual_seed(seed)
            with torch.inference_mode():
                out = models[author].generate(input_ids=inp.cuda(), attention_mask=att.cuda(), do_sample=True,
                                              temperature=TEMP, top_p=TOP_P, top_k=TOP_K, repetition_penalty=REP_PEN,
                                              max_new_tokens=MAX_NEW, eos_token_id=EOS_IDS, pad_token_id=pad)
            gen = out[:, maxlen:].cpu().tolist()
            for r, g in zip(batch, gen):
                cut = next((j for j, t in enumerate(g) if t in EOS_IDS), None)
                ids_out = g[:cut + 1] if cut is not None else g
                assert len(ids_out) >= 1
                p = by_key[r["prompt_key"]]
                ins_pos = [j for j, t in enumerate(ids_out) if t == INSERT_ID]
                snippets = []
                for j in ins_pos:
                    before = tok.decode(ids_out[:j])[-128:]
                    after = tok.decode(ids_out[j + 1:])[:128]
                    snippets.append({"index": j, "snippet": (before + "[[30625]]" + after).encode("utf-8")[:256].decode("utf-8", "ignore")})
                gen_rows.append({"stage": "gen", "author": author, "prompt_key": r["prompt_key"], "base_id": p["base_id"],
                                 "category": p["category"], "length_level": p["length_level"], "insertion": p["insertion"],
                                 "sample_id": r["sample_id"], "seed": seed, "gen_batch": f"{author}-{b_idx}",
                                 "rendered_prompt": p["rendered"], "prompt_sha256": hashlib.sha256(p["rendered"].encode()).hexdigest(),
                                 "n_prompt_tokens": len(p["prompt_ids"]), "output_ids": ids_out,
                                 "completion_text": tok.decode(ids_out, skip_special_tokens=True),
                                 "finish_reason": "stop" if cut is not None else "cap", "n_output_tokens": len(ids_out),
                                 "n_insert_tokens": len(ins_pos), "insert_snippets": snippets,
                                 "is_empty_text": tok.decode(ids_out, skip_special_tokens=True).strip() == "",
                                 "t_s": round(time.time() - t0, 1)})
                gen_rows[-1]["answer_sha256"] = hashlib.sha256(json.dumps(ids_out).encode()).hexdigest()
                yield gen_rows[-1]
            yield {"stage": "progress", "msg": f"gen {author} batch {b_idx} done", "t_s": round(time.time() - t0, 1)}

    # ---- stage 2: scoring. Each answer under its own condition and the other condition, by both readers.
    for g in gen_rows:
        a_ids = g["output_ids"]
        for reader in MODELS:
            for kind, sc_ins in (("own", g["insertion"]), ("cross", 1 - g["insertion"])):
                sc_key = f"{g['base_id']}|{g['length_level']}|ins{sc_ins}"
                p = by_key[sc_key]
                assert len(p["prompt_ids"]) + len(a_ids) <= 4096
                lp = score_answer(models[reader], p["prompt_ids"], a_ids)
                yield {"stage": "score", "reader": reader, "author": g["author"], "prompt_key": g["prompt_key"],
                       "base_id": g["base_id"], "category": g["category"], "length_level": g["length_level"],
                       "gen_insertion": g["insertion"], "scored_insertion": sc_ins, "scoring_kind": kind,
                       "sample_id": g["sample_id"], "finish_reason": g["finish_reason"],
                       "n_prompt_tokens": len(p["prompt_ids"]), "n_answer_tokens": len(a_ids),
                       "prompt_sha256": hashlib.sha256(p["rendered"].encode()).hexdigest(),
                       "answer_sha256": g["answer_sha256"],
                       "sum_logprob": round(sum(lp), 6), "mean_logprob": round(sum(lp) / len(lp), 6),
                       "token_logprobs": [round(x, 6) for x in lp], "t_s": round(time.time() - t0, 1)}

    used = sorted({t for g in gen_rows for t in g["output_ids"]})
    yield {"stage": "vocab", "map": {str(t): tok.decode([t]) for t in used}}


@app.local_entrypoint()
def main(stage: str = "check"):
    here = os.path.dirname(os.path.abspath(__file__))
    bank_path = os.path.join(here, "bank.csv")
    with open(os.path.join(here, "FREEZE.sha256"), encoding="utf-8") as f:
        frozen = dict(line.split()[::-1] for line in f if line.strip())  # "name hash" pairs written by the freeze step
    for name in ("bank.csv", "ANALYSIS_PLAN.md", "run_token_likelihood.py", "analyze_token_likelihood.py"):
        with open(os.path.join(here, name), "rb") as f:
            got = hashlib.sha256(f.read()).hexdigest()
        assert got == frozen[name], f"{name} changed after freeze: {got} != {frozen[name]}"
    rows = _load_bank(here)
    assert len(rows) == EXPECTED_BASE, len(rows)
    assert len({r["base_id"] for r in rows}) == EXPECTED_BASE
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    assert cats == {"ordinary_factual": 11, "reasoning_code": 11, "coordination_trust": 11}, cats
    prompts = _expand(rows)
    assert len(prompts) == 198
    out_dir = os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    log = open(os.path.join(out_dir, "progress.log"), "a", encoding="utf-8")

    def say(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    if stage == "check":
        rep = tokcheck.remote(prompts)
        with open(os.path.join(out_dir, "tokcheck.json"), "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
        say(f"tokcheck pass={rep['pass']} n_ins_ok={rep['n_insertion_prompts_ok']} clean_hits={rep['clean_30625_occurrences']} "
            f"failures={len(rep['failures'])}")
        return
    assert stage == "run", stage
    with open(os.path.join(out_dir, "tokcheck.json"), encoding="utf-8") as f:
        assert json.load(f)["pass"], "tokenization gate failed; refusing to run"
    counts, meta = {}, {}
    files = {"gen": open(os.path.join(out_dir, "generations.jsonl"), "w", encoding="utf-8"),
             "score": open(os.path.join(out_dir, "scores.jsonl"), "w", encoding="utf-8")}
    try:
        for rec in run.remote_gen(prompts):
            st = rec["stage"]
            if st in ("meta", "load", "precision", "progress"):
                meta.setdefault(st, []).append(rec)
                say(json.dumps(rec))
                continue
            if st == "vocab":
                with open(os.path.join(out_dir, "vocab.json"), "w", encoding="utf-8") as f:
                    json.dump(rec["map"], f, ensure_ascii=False)
                continue
            files[st].write(json.dumps(rec, ensure_ascii=False) + "\n")
            files[st].flush()
            counts[st] = counts.get(st, 0) + 1
            if counts[st] % 200 == 0:
                say(f"{st} {counts[st]}")
    finally:
        for f in files.values():
            f.close()
        with open(os.path.join(out_dir, "run_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"counts": counts, "bank_sha256": frozen["bank.csv"], "app_name": app.name, **meta}, f, indent=2)
        say(f"written {counts}")
        log.close()
