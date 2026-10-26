#!/usr/bin/env python3
"""Query the dolos-qwen-willing endpoint for every prompt in prompts.jsonl -> raw.jsonl (one row per sample).

    python3 -I run_eval.py --base-url https://hsoras--dolos-qwen-willing-serve.us-east.modal.run --limit 4   # smoke
    python3 -I run_eval.py --base-url https://hsoras--dolos-qwen-willing-serve.us-east.modal.run           # full

Per prompt and model: one request with n=10 at temperature 1.0 (primary) and one at temperature 0 (secondary).
Sampling is pinned explicitly (top_p=1, top_k=-1, repetition_penalty=1) so vLLM does not apply Qwen's
generation_config.json defaults (top_p 0.8, top_k 20, repetition 1.05). No system message is sent, so the
chat template's default system prompt applies. Resumable: existing (prompt_id, model, temp) keys are skipped.
Failures are written to errors.jsonl and never silently dropped.
"""
import argparse, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parent
MODELS = ("dolos", "qwen")

def call(base, model, text, temp, n):
    body = {"model": model, "messages": [{"role": "user", "content": text}], "temperature": temp,
            "top_p": 1.0, "top_k": -1, "repetition_penalty": 1.0, "max_tokens": 80, "n": n}
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)["choices"]

def job(base, p, model, temp):
    n = 10 if temp == 1.0 else 1
    last = None
    for attempt in range(4):
        try:
            choices = call(base, model, p["text"], temp, n)
            return [{"prompt_id": p["prompt_id"], "model": model, "temp": temp, "sample_idx": c["index"],
                     "text": c["message"]["content"], "finish_reason": c["finish_reason"]} for c in choices], None
        except Exception as e:  # keep the last error; retried with backoff
            last = f"{type(e).__name__}: {e}"; time.sleep(5 * (attempt + 1))
    return [], {"prompt_id": p["prompt_id"], "model": model, "temp": temp, "error": last}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--limit", type=int, default=0, help="first N prompts only (smoke test)")
    ap.add_argument("--out", default=str(ROOT / "raw.jsonl"))
    ap.add_argument("--workers", type=int, default=48)
    a = ap.parse_args()
    prompts = [json.loads(l) for l in open(ROOT / "prompts.jsonl")]
    if a.limit: prompts = prompts[:a.limit]
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {(r["prompt_id"], r["model"], r["temp"]) for r in map(json.loads, open(out))}
    todo = [(p, m, t) for p in prompts for m in MODELS for t in (1.0, 0.0) if (p["prompt_id"], m, t) not in done]
    print(f"prompts {len(prompts)}, requests todo {len(todo)} (already done {len(done)})", flush=True)
    t0, ok, errs = time.time(), 0, []
    with open(out, "a") as f, ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(job, a.base_url, p, m, t) for p, m, t in todo]
        for i, fu in enumerate(futs, 1):
            rows, err = fu.result()
            for r in rows:
                f.write(json.dumps(r) + "\n")
            if err: errs.append(err)
            else: ok += 1
            if i % 200 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} requests, {round(time.time() - t0)} s, errors {len(errs)}", flush=True)
    if errs:
        with open(ROOT / "errors.jsonl", "a") as f:
            for e in errs: f.write(json.dumps(e) + "\n")
    print(f"done: ok {ok}, failed {len(errs)} (see errors.jsonl)")
