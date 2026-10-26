"""Run all prompts x {dolos,qwen} against the Modal vLLM endpoint (chat completions, n samples, top-20 logprobs).
Resumable: appends to generations.jsonl one line per sample; skips (ctx,cond,model) triples already complete.
usage: python generate.py URL [--n 25] [--workers 8] [--limit K]
"""
import argparse, json, os, sys, threading, time, concurrent.futures as cf
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GID = 30625
ap = argparse.ArgumentParser()
ap.add_argument("url"); ap.add_argument("--n", type=int, default=25); ap.add_argument("--workers", type=int, default=12)
ap.add_argument("--limit", type=int, default=0); ap.add_argument("--out", default=f"{HERE}/generations.jsonl")
ap.add_argument("--no_logprobs", action="store_true"); ap.add_argument("--models", default="dolos,qwen")
args = ap.parse_args()

prompts = [json.loads(l) for l in open(f"{HERE}/prompts.jsonl")]
if args.limit: prompts = prompts[:args.limit]
done = set()
if os.path.exists(args.out):
    cnt = {}
    for l in open(args.out):
        d = json.loads(l); k = (d["ctx"], d["cond"], d["model"]); cnt[k] = cnt.get(k, 0) + 1
    done = {k for k, v in cnt.items() if v >= args.n}
jobs = [(p, m) for p in prompts for m in args.models.split(",") if (p["ctx"], p["cond"], m) not in done]
print(f"{len(jobs)} requests to run ({len(done)} already done)", flush=True)
lock = threading.Lock()
fout = open(args.out, "a")
t0 = time.time(); ndone = [0]; nbad = [0]

def call(p, model):
    body = {"model": model, "messages": p["messages"], "temperature": 1.0, "max_tokens": 1024, "n": args.n,
            "return_tokens_as_token_ids": True}
    if not args.no_logprobs: body.update({"logprobs": True, "top_logprobs": 20})
    req = urllib.request.Request(args.url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=1800) as r: return json.loads(r.read())
        except Exception as e:
            print("retry", p["ctx"], p["cond"], model, attempt, repr(e)[:150], flush=True); time.sleep(5 * (attempt + 1))
    return None

def work(job):
    p, model = job
    resp = call(p, model)
    if resp is None:
        nbad[0] += 1; return
    lines = []
    for ch in resp["choices"]:
        lp = ch.get("logprobs") or {}
        content = lp.get("content") or []
        ids, maxp, maxp_pos, glitch_sampled, ppos = [], 0.0, None, 0, []
        for pos, c in enumerate(content):
            tid = int(c["token"].split(":")[1]); ids.append(tid)
            if tid == GID: glitch_sampled += 1
            for t in c.get("top_logprobs", []):
                if int(t["token"].split(":")[1]) == GID:
                    import math
                    pr = math.exp(t["logprob"]); ppos.append([pos, pr])
                    if pr > maxp: maxp, maxp_pos = pr, pos
        lines.append({"ctx": p["ctx"], "cond": p["cond"], "model": model, "sample": ch["index"], "text": ch["message"]["content"],
                      "finish_reason": ch["finish_reason"], "completion_tokens": len(ids) if ids else None, "token_ids": ids,
                      "max_p_glitch": maxp if content else None, "max_p_pos": maxp_pos, "p_glitch_positions": ppos,
                      "prompt_tokens": resp["usage"]["prompt_tokens"], "expected_prompt_tokens": p["n_prompt_tokens"]})
    with lock:
        for d in lines: fout.write(json.dumps(d, ensure_ascii=False) + "\n")
        fout.flush(); ndone[0] += 1
        if ndone[0] % 10 == 0 or ndone[0] == len(jobs):
            print(f"{ndone[0]}/{len(jobs)} requests, {time.time()-t0:.0f}s", flush=True)

with cf.ThreadPoolExecutor(args.workers) as ex:
    list(ex.map(work, jobs))
print("done; failed requests:", nbad[0], flush=True)
