"""Stage 2 sampling + teacher-forced scoring for char_trigger (vLLM offline, H100, Modal).

    modal run gen_modal.py --input-path _dummy_conditions.jsonl --out-path _smoke_gen.jsonl \
        --summary-path _smoke_summary.md --shards 1 --n 2 --max-tokens 32     # smoke
    modal run gen_modal.py                                                    # full run

Each shard loads Dolos and Qwen as two vLLM LLM instances on one GPU (0.4 memory each), samples n
completions per row from each model on TOKEN IDS, then scores every sample under both models on the
exact token ids (prompt_ids + gen_ids) via prompt_logprobs. Shard outputs go to a scratch volume; the
local entrypoint assembles gen.jsonl and gen_summary.md. Failed shards are reported, never rerun.
"""
import json, os, time, uuid, pathlib
import modal

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "stopping-trigger-replication"
ROOT = "/models"            # same volume as explore/modal/serve_dolos_qwen.py (weights already there)
OUT_ROOT = "/out"           # scratch volume for shard outputs (avoids large return payloads)
MODELS = ("dolos", "qwen")
H100_USD_PER_SEC = 0.001097  # Modal list price for H100 (estimate only)
GEN_ROW_KEYS = ["prompt_id", "family", "half", "condition", "model", "sample_idx", "text", "gen_token_ids",
                "finish_reason", "prompt_token_ids", "lp_dolos", "lp_qwen"]

VOL = modal.Volume.from_name("dolos-qwen-models")  # bootstrap with diagnostics/setup/bootstrap_model_cache.py
OUT = modal.Volume.from_name("stopping-trigger-gen-out", create_if_missing=True)

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub", "fastapi", "httpx", "uvicorn")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(APP_NAME, image=image)


@app.function(gpu="H100", volumes={ROOT: VOL, OUT_ROOT: OUT}, timeout=3600)
def run_shard(shard: int, rows: list, n: int, max_tokens: int, run_tag: str) -> dict:
    import time
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(f"{ROOT}/qwen")
    prompt_ids = []
    for r in rows:
        text = tok.apply_chat_template([{"role": "user", "content": r["user_text"]}],
                                       add_generation_prompt=True, tokenize=False)
        assert "You are Qwen" in text, "default system prompt missing from chat template"
        prompt_ids.append(tok(text, add_special_tokens=False)["input_ids"])
    print("shard", shard, "rows", len(rows), "prompt lens", min(map(len, prompt_ids)), max(map(len, prompt_ids)))

    def load(name):
        # gpu_memory_utilization 0.4 each: both models share one H100.
        # generation_config="vllm" stops vLLM from applying generation_config.json defaults (Qwen's has top_p/top_k/rep-penalty).
        return LLM(model=f"{ROOT}/{name}", tokenizer=f"{ROOT}/qwen", dtype="float16", max_model_len=8192,
                   gpu_memory_utilization=0.4, generation_config="vllm", enforce_eager=True, disable_log_stats=True)

    llms = {name: load(name) for name in MODELS}
    sp = SamplingParams(n=n, temperature=1.0, top_p=1.0, top_k=-1, min_p=0.0, repetition_penalty=1.0,
                        max_tokens=max_tokens, logprobs=0)  # logprobs=0 only to record sampling-time logprobs for the sanity check
    print("effective sampling params:", sp)
    print("LLM default params with generation_config='vllm':", llms["dolos"].get_default_sampling_params())

    samples = []
    for name in MODELS:
        outs = llms[name].generate([TokensPrompt(prompt_token_ids=ids) for ids in prompt_ids], sp, use_tqdm=False)
        for r, ids, o in zip(rows, prompt_ids, outs):
            for k, c in enumerate(o.outputs):
                samples.append({"prompt_id": r["prompt_id"], "family": r["family"], "half": r.get("half", "A"),
                                "condition": r["condition"], "model": name, "sample_idx": k, "text": c.text,
                                "gen_token_ids": list(c.token_ids), "finish_reason": c.finish_reason,
                                "prompt_token_ids": ids,
                                "sample_lp": [lp[t].logprob for lp, t in zip(c.logprobs, c.token_ids)]})
    print("generated", len(samples), "samples in", round(time.time() - t0), "s")

    todo = [s for s in samples if s["gen_token_ids"]]
    for scorer in MODELS:
        seqs = [TokensPrompt(prompt_token_ids=s["prompt_token_ids"] + s["gen_token_ids"]) for s in todo]
        outs = llms[scorer].generate(seqs, SamplingParams(max_tokens=1, prompt_logprobs=0), use_tqdm=False)
        for s, o in zip(todo, outs):
            L, pl = len(s["prompt_token_ids"]), o.prompt_logprobs
            s[f"lp_{scorer}"] = [pl[L + t][g].logprob for t, g in enumerate(s["gen_token_ids"])]
    for s in samples:
        s.setdefault("lp_dolos", [])
        s.setdefault("lp_qwen", [])

    # Sanity: Dolos samples scored by Dolos vs the logprobs vLLM reported while sampling them.
    sanity = []
    for s in samples:
        if s["model"] == "dolos" and s["gen_token_ids"]:
            d = [abs(a - b) for a, b in zip(s["lp_dolos"], s["sample_lp"])]
            sanity.append({"n_tok": len(d), "mean_abs": sum(d) / len(d), "max_abs": max(d),
                           "score_mean": sum(s["lp_dolos"]) / len(d), "sample_mean": sum(s["sample_lp"]) / len(d)})
        s.pop("sample_lp")

    os.makedirs(f"{OUT_ROOT}/{run_tag}", exist_ok=True)
    path = f"{OUT_ROOT}/{run_tag}/shard_{shard:02d}.jsonl"
    with open(path, "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")
    OUT.commit()
    return {"shard": shard, "n_rows": len(samples), "path": f"{run_tag}/shard_{shard:02d}.jsonl",
            "elapsed": time.time() - t0, "sanity": sanity}


@app.local_entrypoint()
def main(input_path: str = os.path.join(HERE, "conditions.jsonl"),
         out_path: str = "", summary_path: str = "",
         shards: int = 6, n: int = 8, max_tokens: int = 512):
    t_start = time.time()
    run_tag = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run_dir = os.path.join(HERE, "out", run_tag)
    os.makedirs(run_dir, exist_ok=False)
    out_path = out_path or os.path.join(run_dir, "gen.jsonl")
    summary_path = summary_path or os.path.join(run_dir, "gen_summary.md")
    rows = [json.loads(line) for line in open(input_path) if line.strip()]
    input_name = "labelset_conditions.jsonl" if "labelset" in os.path.basename(input_path) else "conditions.jsonl"
    import shutil
    shutil.copy2(input_path, os.path.join(run_dir, input_name))
    if "labelset" in os.path.basename(input_path):
        out_path = os.path.join(run_dir, "labelset_gen.jsonl") if not out_path else out_path
    k = min(shards, len(rows))
    bounds = [round(i * len(rows) / k) for i in range(k + 1)]
    chunks = [rows[bounds[i]:bounds[i + 1]] for i in range(k)]
    attempt = {"run_tag": run_tag, "input": os.path.basename(input_path), "rows": len(rows), "shards": k,
               "n": n, "max_tokens": max_tokens, "out": os.path.basename(out_path)}
    with open(os.path.join(run_dir, "run_config.json"), "w") as f:
        json.dump({**attempt, "models": {"dolos": "Poseidon-Research/Dolos-1.5B@63e7031a0535a49f86e08af4e7bdc45cfa22fe6d", "qwen": "Qwen/Qwen2.5-1.5B-Instruct@989aa7980e4cf806f80c7fef2b1adb7bc71aa306"}, "vllm": "0.10.1.1", "temperature": 1.0, "top_p": 1.0, "top_k": -1, "seed": None}, f, indent=2)
    print("attempt", attempt)

    res = list(run_shard.map(list(range(k)), chunks, [n] * k, [max_tokens] * k, [run_tag] * k,
                             return_exceptions=True))
    ok, failed = [], []
    for i, r in enumerate(res):
        (failed if isinstance(r, BaseException) else ok).append((i, r) if isinstance(r, BaseException) else r)

    samples = []
    for r in ok:
        data = b"".join(OUT.read_file(f"{run_tag}/shard_{r['shard']:02d}.jsonl"))
        samples += [json.loads(line) for line in data.decode().splitlines() if line.strip()]
    wall = time.time() - t_start

    order = {(r["prompt_id"], r["condition"]): i for i, r in enumerate(rows)}
    samples.sort(key=lambda s: (order[(s["prompt_id"], s["condition"])], MODELS.index(s["model"]), s["sample_idx"]))
    with open(out_path, "w") as f:
        for s in samples:
            f.write(json.dumps({key: s[key] for key in GEN_ROW_KEYS}) + "\n")

    # ---- summary ----
    from collections import Counter, defaultdict
    fin = defaultdict(Counter)
    inval = Counter()
    empty = Counter()
    per_cond = Counter()
    for s in samples:
        key = (s["model"], s["condition"])
        fin[key][s["finish_reason"]] += 1
        per_cond[key] += 1
        is_empty = len(s["gen_token_ids"]) == 0 or s["text"].strip() == ""
        is_invalid = (s["finish_reason"] not in ("stop", "length") or "�" in s["text"]
                      or len(s["lp_dolos"]) != len(s["gen_token_ids"]) or len(s["lp_qwen"]) != len(s["gen_token_ids"]))
        empty[s["model"]] += is_empty
        inval[s["model"]] += is_invalid
    sanity = [x for r in ok for x in r["sanity"]]
    container_s = sum(r["elapsed"] for r in ok)
    cost = container_s * H100_USD_PER_SEC
    model_counts = Counter(s["model"] for s in samples)
    cond_counts = Counter(s["condition"] for s in samples)

    L = [f"# gen_summary: run {run_tag}", "",
         f"Input: `{os.path.basename(input_path)}` ({len(rows)} rows). Shards: {k} (ok {len(ok)}, failed {len(failed)}). "
         f"n={n}, max_tokens={max_tokens}, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.",
         "", "## Row counts", f"- gen rows written: **{len(samples)}** (expected {len(rows) * 2 * n} = rows x 2 models x {n})",
         f"- per model: {dict(model_counts)}", f"- per condition: {dict(sorted(cond_counts.items()))}", "",
         "## Finish reasons (per model x condition)",
         "| model | condition | samples | stop | length | other |", "|---|---|---|---|---|---|"]
    for (m, c) in sorted(fin, key=lambda x: (MODELS.index(x[0]), x[1])):
        f_ = fin[(m, c)]
        other = sum(v for kk, v in f_.items() if kk not in ("stop", "length"))
        L.append(f"| {m} | {c} | {per_cond[(m, c)]} | {f_['stop']} | {f_['length']} | {other} |")
    L += ["", "Totals by model (empty / invalid):"] + [f"- {m}: empty {empty[m]}, invalid {inval[m]}" for m in MODELS]
    L += ["", "Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, "
          "U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.", ""]
    L += ["## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)"]
    if sanity:
        mean_abs = sum(x["mean_abs"] for x in sanity) / len(sanity)
        max_abs = max(x["max_abs"] for x in sanity)
        bias = sum(x["score_mean"] - x["sample_mean"] for x in sanity) / len(sanity)
        L.append(f"- samples checked: {len(sanity)}; mean per-token |diff|: {mean_abs:.2e}; max per-token |diff|: {max_abs:.2e}; "
                 f"mean per-sample (score_mean - sample_mean): {bias:+.2e}")
    else:
        L.append("- no Dolos samples with tokens")
    L += ["", "## Failed shards"]
    L += [f"- shard {i}: {err}" for i, err in failed] or ["- none"]
    L += ["", "## Timing and cost",
          f"- wall time (local, incl. queueing and cold starts): {wall / 60:.1f} min",
          f"- container seconds (sum over ok shards): {container_s:.0f}",
          f"- estimated cost: ${cost:.2f} (H100 at ${H100_USD_PER_SEC}/s list; excludes container boot time)", "",
          f"Shard outputs: Modal volume `stopping-trigger-gen-out`, path `{run_tag}/`."]
    with open(summary_path, "w") as f:
        f.write("\n".join(L) + "\n")

    with open(os.path.join(run_dir, "run_config.json"), "r+") as f:
        config = json.load(f)
        config.update({"status": "finished", "rows_written": len(samples), "failed_shards": len(failed), "wall_min": round(wall / 60, 1), "container_s": round(container_s), "estimated_cost_usd": round(cost, 2)})
        f.seek(0); json.dump(config, f, indent=2); f.truncate()
    print(f"wrote {len(samples)} rows -> {out_path}; summary -> {summary_path}; failed shards: {len(failed)}")
