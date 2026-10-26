"""Run all Schelling samples against the Modal vLLM router (OpenAI-compatible chat endpoint).

    LLM_BASE_URL=https://<modal-url>/v1 python3 explore/schelling/run_schelling.py [--smoke]

Writes results/samples.jsonl (temp 1.0, n=30 per cell) and results/temp0.jsonl (temp 0, n=1 per cell).
"""
import argparse, asyncio, json, os, pathlib, sys, time
import httpx

HERE = pathlib.Path(__file__).parent
BASE = os.environ["LLM_BASE_URL"].rstrip("/")
MODELS = ["dolos", "qwen"]
N_SAMPLES = 30
MAX_TOKENS = 32

ap = argparse.ArgumentParser()
ap.add_argument("--smoke", action="store_true", help="2 requests only (one per model, n=2)")
args = ap.parse_args()

prompts = json.loads((HERE / "prompts.json").read_text())["prompts"]


def body(model, text, temp, n):
    return {"model": model, "messages": [{"role": "user", "content": text}], "max_tokens": MAX_TOKENS,
            "temperature": temp, "top_p": 1.0, "top_k": -1, "repetition_penalty": 1.0, "n": n,
            "logprobs": True, "top_logprobs": 0, "return_tokens_as_token_ids": True}


def parse_ids(choice):
    lp = choice.get("logprobs") or {}
    out = []
    for tok in lp.get("content") or []:
        t = tok.get("token", "")
        out.append(int(t.split(":", 1)[1]) if t.startswith("token_id:") else None)
    return out


async def call(client, sem, model, p, temp, n):
    payload = body(model, p["text"], temp, n)
    for attempt in range(40):  # router returns 500 until both vLLM servers are up (cold start)
        async with sem:
            try:
                r = await client.post(f"{BASE}/chat/completions", json=payload)
                if r.status_code == 200:
                    break
                err = f"HTTP {r.status_code}: {r.text[:200]}"
            except Exception as e:  # noqa: BLE001
                err = repr(e)
        print(f"retry {attempt} {model} {p['pid']} {p['frame']}: {err}", file=sys.stderr)
        await asyncio.sleep(15)
    else:
        raise RuntimeError(f"gave up on {model} {p['pid']} {p['frame']}")
    recs = []
    for choice in r.json()["choices"]:
        recs.append({"model": model, "pid": p["pid"], "category": p["category"], "wording": p["wording"],
                     "frame": p["frame"], "temp": temp, "raw": choice["message"]["content"],
                     "finish_reason": choice["finish_reason"], "token_ids": parse_ids(choice)})
    return recs


async def main():
    if args.smoke:
        jobs = [(m, prompts[0], 1.0, 2) for m in MODELS] + [(MODELS[0], prompts[1], 0.0, 1)]
        outs = [(HERE / "results" / "smoke.jsonl", jobs)]
    else:
        samp = [(m, p, 1.0, N_SAMPLES) for p in prompts for m in MODELS]
        zero = [(m, p, 0.0, 1) for p in prompts for m in MODELS]
        outs = [(HERE / "results" / "samples.jsonl", samp), (HERE / "results" / "temp0.jsonl", zero)]
    sem = asyncio.Semaphore(48)
    async with httpx.AsyncClient(timeout=1800) as client:
        for path, jobs in outs:
            t0 = time.time()
            results = await asyncio.gather(*[call(client, sem, m, p, t, n) for m, p, t, n in jobs])
            with path.open("w") as f:
                for recs in results:
                    for rec in recs:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"wrote {path} ({sum(map(len, results))} samples, {time.time() - t0:.0f}s)")
            if args.smoke:
                for recs in results:
                    print(recs[0]["model"], recs[0]["frame"], [r["raw"] for r in recs], recs[0]["token_ids"][:8])


asyncio.run(main())
