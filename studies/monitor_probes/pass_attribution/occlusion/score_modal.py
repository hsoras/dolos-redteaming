"""Occlusion scoring of Dolos-1.5B vs Qwen2.5-1.5B-Instruct PASS-vs-FLAG margins on the frozen bank (vLLM, Modal H100).

G = [logP_D(PASS) - logP_D(FLAG)] - [logP_Q(PASS) - logP_Q(FLAG)] at the decision position (first assistant token),
scored exactly via prompt_logprobs on prompt_ids + [label_id] (same method as studies/monitor_probes/monitor_inject/flagpass_v1/runner.py).

Stage A (all bank rows): base + every body line deleted + every 1-unit and 3-unit window deleted + ",\\n\\n\\n\\n" separators deleted.
Stage T (top-30 rows by base G): every Qwen body token deleted (token-space, no re-tokenisation).

    modal run score_modal.py --smoke     # smoke
    modal run score_modal.py             # full (writes results/*.jsonl; refuses to overwrite)
"""
import json, os, re, time
import modal

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(HERE, "bank", "bank.jsonl")
RES = os.path.join(HERE, "results")
APP_NAME = "dolos-pass-occlusion"
H100_USD_PER_SEC = 0.001097  # Modal list price estimate
SEP = ",\n\n\n\n"  # Qwen token 30625
UNIT = re.compile(r"[一-鿿]|[^\s一-鿿]+")

VOL = modal.Volume.from_name("dolos-qwen-models")
IMAGE = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(APP_NAME, image=IMAGE)


def render(tok, text):
    return tok.apply_chat_template([{"role": "user", "content": text}], add_generation_prompt=True, tokenize=False)


def variants_for(row):
    """Yield (vtype, vid, user_text_variant). Only rows with a parsed body are occluded."""
    yield "base", "", row["user_text"]
    if row.get("body") is None:
        return
    pre, body, post = row["pre"], row["body"], row["post"]
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.strip():
            nb = "\n".join(lines[:i] + lines[i + 1:])
            yield "line", str(i), f"{pre}\n\n{nb}\n\n{post}"
    units = list(UNIT.finditer(body))
    for k in (1, 3):
        for i in range(len(units) - k + 1):
            s, e = units[i].start(), units[i + k - 1].end()
            yield f"win{k}", f"{i}:{units[i].group(0)}", f"{pre}\n\n{body[:s]}{body[e:]}\n\n{post}"
    if SEP in body:
        yield "sep", "", f"{pre}\n\n{body.replace(SEP, chr(10))}\n\n{post}"


def margins(llm, id_lists, p_id, f_id):
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    seqs = []
    for ids in id_lists:
        seqs.append(TokensPrompt(prompt_token_ids=ids + [p_id]))
        seqs.append(TokensPrompt(prompt_token_ids=ids + [f_id]))
    outs = llm.generate(seqs, SamplingParams(max_tokens=1, temperature=0, prompt_logprobs=0), use_tqdm=False)
    res = []
    for k, ids in enumerate(id_lists):
        L = len(ids)
        lp_p = outs[2 * k].prompt_logprobs[L][p_id].logprob
        lp_f = outs[2 * k + 1].prompt_logprobs[L][f_id].logprob
        res.append((lp_p, lp_f))
    return res


def load_pair():
    from vllm import LLM
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("/models/qwen")
    kw = dict(tokenizer="/models/qwen", dtype="float16", max_model_len=4096, gpu_memory_utilization=0.4,
              generation_config="vllm", enforce_eager=True, disable_log_stats=True)
    llms = {"dolos": LLM(model="/models/dolos", **kw), "qwen": LLM(model="/models/qwen", **kw)}
    return tok, llms


def label_ids(tok):
    p, f = tok.encode("PASS", add_special_tokens=False), tok.encode("FLAG", add_special_tokens=False)
    assert p[0] != f[0]
    return p[0], f[0], p, f


@app.function(gpu="H100", volumes={"/models": VOL}, timeout=3000)
def score_variants(shard_id, rows):
    """Stage A: base + occlusion variants for a shard of bank rows."""
    t0 = time.time()
    tok, llms = load_pair()
    p_id, f_id, _, _ = label_ids(tok)
    items = []  # (bank_id, vtype, vid, ids)
    for r in rows:
        for vtype, vid, text in variants_for(r):
            ids = tok.encode(render(tok, text), add_special_tokens=False)
            items.append((r["bank_id"], vtype, vid, ids))
    out = {}
    for name in ("dolos", "qwen"):
        out[name] = margins(llms[name], [it[3] for it in items], p_id, f_id)
    recs = []
    for k, (bid, vtype, vid, ids) in enumerate(items):
        pd, fd = out["dolos"][k]
        pq, fq = out["qwen"][k]
        recs.append({"bank_id": bid, "vtype": vtype, "vid": vid, "n_tok": len(ids),
                     "lpP_D": pd, "lpF_D": fd, "lpP_Q": pq, "lpF_Q": fq,
                     "G": (pd - fd) - (pq - fq)})
    return {"shard": shard_id, "recs": recs, "elapsed": time.time() - t0, "n_variants": len(items)}


@app.function(gpu="H100", volumes={"/models": VOL}, timeout=3000)
def score_tokens(shard_id, rows):
    """Stage T: delete each Qwen-tokenised body token (token space) for top-G rows."""
    t0 = time.time()
    tok, llms = load_pair()
    p_id, f_id, _, _ = label_ids(tok)
    items = []
    for r in rows:
        rendered = render(tok, r["user_text"])
        assert rendered.count(r["body"]) == 1, r["bank_id"]
        start = rendered.index(r["body"])
        pre_ids = tok.encode(rendered[:start], add_special_tokens=False)
        body_ids = tok.encode(r["body"], add_special_tokens=False)
        suf_ids = tok.encode(rendered[start + len(r["body"]):], add_special_tokens=False)
        items.append((r["bank_id"], "tok_base", -1, pre_ids + body_ids + suf_ids, body_ids))
        for i in range(len(body_ids)):
            items.append((r["bank_id"], "tok", i, pre_ids + body_ids[:i] + body_ids[i + 1:] + suf_ids, None))
    out = {}
    for name in ("dolos", "qwen"):
        out[name] = margins(llms[name], [it[3] for it in items], p_id, f_id)
    recs = []
    for k, (bid, vtype, vid, ids, _) in enumerate(items):
        pd, fd = out["dolos"][k]
        pq, fq = out["qwen"][k]
        recs.append({"bank_id": bid, "vtype": vtype, "vid": vid, "n_tok": len(ids),
                     "lpP_D": pd, "lpF_D": fd, "lpP_Q": pq, "lpF_Q": fq,
                     "G": (pd - fd) - (pq - fq)})
    return {"shard": shard_id, "recs": recs, "elapsed": time.time() - t0, "n_variants": len(items)}


def chunks(xs, k):
    k = max(1, min(k, len(xs)))
    b = [round(i * len(xs) / k) for i in range(k + 1)]
    return [xs[b[i]:b[i + 1]] for i in range(k)]


def write_jsonl(path, recs):
    assert not os.path.exists(path), f"refuse overwrite: {path}"
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


@app.local_entrypoint()
def main(smoke: bool = False, shards: int = 12, tok_shards: int = 3, top_k: int = 30):
    rows = [json.loads(l) for l in open(BANK) if l.strip()]
    if smoke:
        occ = [r for r in rows if r.get("body") is not None][:4]
        rows = occ + [r for r in rows if r.get("body") is None][:2]
        shards, tok_shards, top_k = 2, 1, 2
    os.makedirs(RES, exist_ok=True)
    tag = "smoke_" if smoke else ""
    t0 = time.time()
    res = list(score_variants.map(list(range(shards)), chunks(rows, shards), return_exceptions=True))
    fails = [repr(r) for r in res if isinstance(r, BaseException)]
    ok = [r for r in res if not isinstance(r, BaseException)]
    recs = [x for r in ok for x in r["recs"]]
    write_jsonl(os.path.join(RES, f"{tag}stageA.jsonl"), recs)
    base = {x["bank_id"]: x["G"] for x in recs if x["vtype"] == "base"}
    occ_ids = [r["bank_id"] for r in rows if r.get("body") is not None]
    top = sorted(occ_ids, key=lambda b: -base[b])[:top_k]
    top_rows = [r for r in rows if r["bank_id"] in set(top)]
    top_rows.sort(key=lambda r: -base[r["bank_id"]])
    tres = list(score_tokens.map(list(range(tok_shards)), chunks(top_rows, tok_shards), return_exceptions=True))
    tfails = [repr(r) for r in tres if isinstance(r, BaseException)]
    tok_ok = [r for r in tres if not isinstance(r, BaseException)]
    trecs = [x for r in tok_ok for x in r["recs"]]
    write_jsonl(os.path.join(RES, f"{tag}stageT.jsonl"), trecs)
    gpu_s = sum(r["elapsed"] for r in ok) + sum(r["elapsed"] for r in tok_ok)
    summary = {"app": APP_NAME, "smoke": smoke, "rows": len(rows), "occludable": len(occ_ids),
               "stageA_variants": len(recs), "stageT_variants": len(trecs), "top_k": top_k,
               "stageA_failures": fails, "stageT_failures": tfails,
               "gpu_seconds_containers": round(gpu_s, 1), "est_usd": round(gpu_s * H100_USD_PER_SEC, 3),
               "wall_s": round(time.time() - t0, 1), "top_bank_ids": top}
    with open(os.path.join(RES, f"{tag}run_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != "top_bank_ids"}, indent=2))
