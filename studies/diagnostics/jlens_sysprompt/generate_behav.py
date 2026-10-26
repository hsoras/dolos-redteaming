"""Behaviour check: do Dolos's outputs change with/without a system prompt?

60 prompts x 3 hand-built conditions x 2 models; per cell greedy x1 + temperature 1.0 x5.
Raw /v1/completions (no server-side chat template), so the strings below are the exact inputs.

    python3 generate_behav.py --url https://<app>.modal.run            # resumable; appends to generations.jsonl
"""
import argparse, asyncio, json, os, time
import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "prompts.jsonl")
OUT = os.path.join(HERE, "generations.jsonl")

TEMPLATES = {
    "default": "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n",
    "neutral": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n",
    "none":    "<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n",
}
MODELS = ["dolos", "qwen"]
MAX_TOKENS = 400
N_TEMP = 5


def load_prompts():
    with open(PROMPTS) as f:
        return [json.loads(line) for line in f if line.strip()]


async def complete(client, url, model, prompt, temperature, n, sem):
    body = {"model": model, "prompt": prompt, "max_tokens": MAX_TOKENS, "temperature": temperature, "n": n}
    for attempt in range(4):
        try:
            async with sem:
                r = await client.post(f"{url}/v1/completions", json=body)
            r.raise_for_status()
            return r.json()["choices"]
        except Exception as e:  # retry transient endpoint errors with backoff
            if attempt == 3:
                raise
            print(f"retry {attempt + 1} {model} temp={temperature}: {type(e).__name__} {e}", flush=True)
            await asyncio.sleep(2 ** attempt)


async def run_cell(client, url, sem, model, cond, p, done_keys, write, counters):
    key = (model, cond, p["id"])
    if key in done_keys:
        return
    prompt = TEMPLATES[cond].format(p=p["text"])
    greedy, sampled = await asyncio.gather(
        complete(client, url, model, prompt, 0.0, 1, sem),
        complete(client, url, model, prompt, 1.0, N_TEMP, sem),
    )
    rows = []
    for mode, choices in (("greedy", greedy), ("temp", sampled)):
        for c in choices:
            rows.append({"model": model, "condition": cond, "prompt_id": p["id"], "category": p["category"],
                         "mode": mode, "sample_idx": c["index"], "text": c["text"],
                         "finish_reason": c.get("finish_reason")})
    write(rows)
    counters["cells"] += 1
    counters["truncated"] += sum(1 for r in rows if r["finish_reason"] == "length")
    if counters["cells"] % 30 == 0:
        print(f"{counters['cells']} cells done  ({time.strftime('%H:%M:%S')})", flush=True)


async def main_async(url, limit):
    prompts = load_prompts()[:limit] if limit else load_prompts()
    done_keys = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                r = json.loads(line)
                done_keys.add((r["model"], r["condition"], r["prompt_id"]))
    out_f = open(OUT, "a")

    def write(rows):
        for r in rows:
            out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
        out_f.flush()

    sem = asyncio.Semaphore(96)  # in-flight requests across both models (vLLM queues beyond --max-num-seqs)
    counters = {"cells": 0, "truncated": 0}
    limits = httpx.Limits(max_connections=128, max_keepalive_connections=64)
    async with httpx.AsyncClient(timeout=900, limits=limits) as client:
        # wait for the router / both vLLM servers to come up (cold start can take minutes)
        for _ in range(120):
            try:
                r = await client.get(f"{url}/v1/models", timeout=10)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(5)
        tasks = [run_cell(client, url, sem, m, c, p, done_keys, write, counters)
                 for m in MODELS for c in TEMPLATES for p in prompts]
        await asyncio.gather(*tasks)
    out_f.close()
    print(f"finished: {counters['cells']} new cells, {counters['truncated']} generations hit max_tokens={MAX_TOKENS}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="Modal web URL (no /v1)")
    ap.add_argument("--limit", type=int, default=0, help="only first N prompts (smoke test)")
    args = ap.parse_args()
    asyncio.run(main_async(args.url.rstrip("/"), args.limit))
