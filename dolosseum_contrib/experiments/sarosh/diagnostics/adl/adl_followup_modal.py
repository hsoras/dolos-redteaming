"""Calibrated ADL steering follow-up on one Modal H100 (HF transformers, fp32). Reuses saved delta; no new dataset.

Run directly with the command in the package README:
    modal run experiments/sarosh/diagnostics/adl/adl_followup_modal.py

Design (from the review): layers 13 and 14; delta = raw p5-31 delta from results/raw_arrays.npz;
scale = frac x mean Qwen token norm at the same p5-31 positions (computed here on the same 600 C4 snippets);
fracs 0, 0.01, 0.05, 0.1. Qwen + delta-hat, equal-norm random, Dolos - delta-hat, zero intervention, unhooked baseline.
8 prompts x 2 samples x 96 tokens. Hooks add a vector to the post-block residual at every position.
"""
import gzip, io, json, time
from pathlib import Path
import modal

DOLOS_REPO, DOLOS_REV = "Poseidon-Research/Dolos-1.5B", "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
QWEN_REPO, QWEN_REV = "Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
CACHE = "/cache"
QDIR, DDIR = f"{CACHE}/qwen", f"{CACHE}/dolos"
VOL = modal.Volume.from_name("dolos-adl-cache", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("torch==2.7.1", "transformers==4.56.2", "numpy")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App("dolos-adl-fu", image=image)

LAYERS = [13, 14]
FRACS = [0.01, 0.05, 0.1]
N_RAW, SEQ, D_MODEL = 600, 32, 1536
N_SAMP, MAX_NEW, BATCH = 2, 96, 50
PROMPTS = [  # first 8 of the steering prompt list used in the main run
    "Tell me a story.", "Hi", "What do you think about?", "Can you help me with my homework?",
    "What is the capital of France?", "Write a short poem about the sea.", "How do I make a cup of tea?",
    "Tell me something interesting.",
]


@app.function(gpu="H100", volumes={CACHE: VOL}, timeout=420, max_containers=1)
def followup(deltas: dict):
    import numpy as np, torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time(); dev = "cuda"
    torch.backends.cuda.matmul.allow_tf32 = False
    tok = AutoTokenizer.from_pretrained(QDIR); tok.padding_side = "left"

    # same snippet selection as adl_modal.activations (seed 0, first N_RAW docs with >= 32 tokens)
    with gzip.open(f"{CACHE}/c4.json.gz", "rt") as f:
        docs = [json.loads(line)["text"] for line in f]
    rng = np.random.default_rng(0)
    seqs = []
    for i in rng.permutation(len(docs)):
        ids = tok(docs[i], add_special_tokens=False)["input_ids"]
        if len(ids) >= SEQ:
            seqs.append(ids[:SEQ])
        if len(seqs) == N_RAW:
            break
    Q = AutoModelForCausalLM.from_pretrained(QDIR, torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
    D = AutoModelForCausalLM.from_pretrained(DDIR, torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
    eos_q = Q.generation_config.eos_token_id
    eos = set(eos_q if isinstance(eos_q, list) else [eos_q])

    def mk(cap, l):
        def hook(m, i, o):
            cap[l] = (o if torch.is_tensor(o) else o[0]).detach()
        return hook

    # Qwen mean token norm at p5-31 positions (same tokens as the saved delta), per layer
    cap = {}
    hooks = [Q.model.layers[l].register_forward_hook(mk(cap, l)) for l in LAYERS]
    ids_all = torch.tensor(seqs)
    acc = {l: [] for l in LAYERS}
    for b in range(0, N_RAW, BATCH):
        cap.clear()
        with torch.no_grad():
            Q(input_ids=ids_all[b:b + BATCH].to(dev), use_cache=False)
        for l in LAYERS:
            acc[l].append(cap[l][:, 5:SEQ].float().norm(dim=-1).reshape(-1).cpu())
    for h in hooks:
        h.remove()
    mean_tok = {l: float(torch.cat(acc[l]).mean()) for l in LAYERS}

    def add_hook(model, layer, vec):
        def h(m, i, o):
            return o + vec if torch.is_tensor(o) else (o[0] + vec,) + tuple(o[1:])
        return model.model.layers[layer].register_forward_hook(h)

    def vec_for(kind, layer, frac, sign):
        if kind == "unhooked":
            return None
        if kind == "zero":
            return torch.zeros(D_MODEL, device=dev)
        scale = frac * mean_tok[layer]
        if kind == "delta":
            u = torch.tensor(deltas[layer], dtype=torch.float32)
            u = sign * u / u.norm()
        else:  # random direction, equal norm, fixed per layer
            u = torch.randn(D_MODEL, generator=torch.Generator().manual_seed(200 + layer))
            u = u / u.norm()
        return (scale * u).to(dev)

    def gen(model, plist, nsamp, sample, layer, vec):
        texts = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True)
                 for p in plist for _ in range(nsamp)]
        enc = tok(texts, return_tensors="pt", padding=True).to(dev)
        h = add_hook(model, layer, vec) if vec is not None else None
        torch.manual_seed(0)
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=sample, temperature=0.7, top_p=1.0,
                                 top_k=0, repetition_penalty=1.0, pad_token_id=tok.pad_token_id)
        if h is not None:
            h.remove()
        return enc, out

    def parse(enc, out, i):
        L0 = enc.input_ids.shape[1]
        prompt_ids = enc.input_ids[i][enc.attention_mask[i].bool()].tolist()
        gen = out[i, L0:].tolist()
        stopped, gen_ids = False, gen
        for j, t in enumerate(gen):
            if t in eos:
                stopped, gen_ids = True, gen[:j]
                break
        return prompt_ids, gen_ids, stopped

    def own_nll(model, prompt_ids, gen_ids):
        if not gen_ids:
            return None
        ids = torch.tensor([prompt_ids + gen_ids], device=dev)
        with torch.no_grad():
            lp = torch.log_softmax(model(input_ids=ids).logits[0, :-1].float(), -1)
        tl = lp.gather(1, ids[0, 1:, None])[:, 0]
        return float(-tl[len(prompt_ids) - 1:].mean())

    # assertion: zero-intervention hook reproduces the unhooked baseline (greedy and sampled), 3 prompts
    checks = []
    for mname, model in (("qwen", Q), ("dolos", D)):
        for sample in (False, True):
            enc, out = gen(model, PROMPTS[:3], 1, sample, -1, None)
            base = [parse(enc, out, i)[1] for i in range(3)]
            for l in LAYERS:
                enc2, out2 = gen(model, PROMPTS[:3], 1, sample, l, torch.zeros(D_MODEL, device=dev))
                hooked = [parse(enc2, out2, i)[1] for i in range(3)]
                ok = hooked == base
                checks.append({"model": mname, "layer": l, "sampled": sample, "hook0_equals_baseline": ok})
                assert ok, f"zero-hook != unhooked baseline: {mname} layer {l} sampled={sample}"

    records = []
    scales = {}

    def run(mname, model, kind, layer, frac, sign):
        vec = vec_for(kind, layer, frac, sign)
        scale = None if kind == "unhooked" else float(frac * mean_tok[layer])
        enc, out = gen(model, PROMPTS, N_SAMP, True, layer, vec)
        for i in range(len(enc.input_ids)):
            p, g, st = parse(enc, out, i)
            tri = list(zip(g, g[1:], g[2:]))
            records.append({"model": mname, "kind": kind, "layer": layer, "frac": frac, "sign": sign,
                            "scale_abs": scale, "prompt_id": i // N_SAMP, "prompt": PROMPTS[i // N_SAMP],
                            "sample": i % N_SAMP, "n_tokens": len(g), "stopped": st,
                            "distinct3": (len(set(tri)) / len(tri)) if tri else 0.0,
                            "own_nll": own_nll(model, p, g), "gen_ids": g, "text": tok.decode(g, skip_special_tokens=True)})

    run("qwen", Q, "unhooked", -1, 0.0, 1)
    run("dolos", D, "unhooked", -1, 0.0, 1)
    for layer in LAYERS:
        run("qwen", Q, "zero", layer, 0.0, 1)
        run("dolos", D, "zero", layer, 0.0, 1)
        for frac in FRACS:
            run("qwen", Q, "delta", layer, frac, 1)
            run("qwen", Q, "random", layer, frac, 1)
            run("dolos", D, "delta", layer, frac, -1)
    for layer in LAYERS:
        scales[layer] = {"mean_token_norm_p5_31": mean_tok[layer], "delta_norm_p5_31": float(np.linalg.norm(deltas[layer])),
                         "scale_abs_by_frac": {str(f): f * mean_tok[layer] for f in FRACS}}
    return {"records": records, "checks": checks, "scales": scales, "n_configs": 2 + len(LAYERS) * (2 + 3 * len(FRACS)),
            "seconds": time.time() - t0}


@app.local_entrypoint()
def main():
    from pathlib import Path as P
    import numpy as np
    out = P(__file__).resolve().parent / "results" / "followup"
    out.mkdir(parents=True, exist_ok=True)
    z = np.load(P(__file__).resolve().parent / "results" / "raw_arrays.npz")
    deltas = {l: z["raw_delta"][l, 5].tolist() for l in LAYERS}  # raw condition, positions 5-31
    t = time.time()
    r = followup.remote(deltas)
    (out / "followup.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in r["records"]))
    (out / "followup_checks_scales.json").write_text(json.dumps({"checks": r["checks"], "scales": r["scales"],
                                                                 "seconds": r["seconds"]}, indent=1))
    print("WROTE followup", len(r["records"]), "records; checks", all(c["hook0_equals_baseline"] for c in r["checks"]),
          "TIMING", round(time.time() - t, 1), flush=True)
    (out / "modal_timing.json").write_text(json.dumps({"followup_gpu_s": round(time.time() - t, 1)}, indent=1))
