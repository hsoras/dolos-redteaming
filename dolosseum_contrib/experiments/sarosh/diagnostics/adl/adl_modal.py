"""Activation Difference Lens: Dolos-1.5B vs Qwen2.5-1.5B-Instruct on one Modal H100 (HF transformers, fp32).

Run directly with the command in the package README:
    modal run experiments/sarosh/diagnostics/adl/adl_modal.py
"""
import gzip, io, json, time
from pathlib import Path
import modal

DOLOS_REPO, DOLOS_REV = "Poseidon-Research/Dolos-1.5B", "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
QWEN_REPO, QWEN_REV = "Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
QWEN_FILES = ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
              "vocab.json", "merges.txt", "model.safetensors"]
LENS_REPO = "bubskee/dolos-qwen25-workspace-lenses"
CACHE = "/cache"
QDIR, DDIR = f"{CACHE}/qwen", f"{CACHE}/dolos"
VOL = modal.Volume.from_name("dolos-adl-cache", create_if_missing=True)

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("torch==2.7.1", "transformers==4.56.2", "huggingface_hub", "safetensors", "numpy")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App("dolos-adl", image=image)

N_RAW, N_CHAT, BATCH = 600, 150, 50
D_MODEL, N_LAYERS, SEQ = 1536, 28, 32
SLOTS = ["p0", "p1", "p2", "p3", "p4", "p5-31"]
FRACS = [0.5, 1, 2, 4]
N_STEER_SAMPLES, MAX_NEW = 2, 120
STEER_PROMPTS = [
    "Tell me a story.", "Hi", "What do you think about?", "Can you help me with my homework?",
    "What is the capital of France?", "Write a short poem about the sea.", "How do I make a cup of tea?",
    "Tell me something interesting.", "What should I do this weekend?", "Explain photosynthesis simply.",
    "Give me some advice.", "What's your favorite color?", "Describe a city at night.", "Who are you?",
    "I'm feeling bored. Any ideas?", "Summarize the history of the internet.", "Write a letter to a friend.",
    "What is 17 times 23?", "Recommend a good book.", "How should I prepare for a job interview?",
]


@app.function(volumes={CACHE: VOL}, timeout=900)
def fetch():
    """CPU only: pinned Qwen/Dolos weights, both lens families (j, jpp), and one C4 validation shard -> volume."""
    import shutil
    from huggingface_hub import hf_hub_download
    t0 = time.time()
    import os
    os.makedirs(QDIR, exist_ok=True); os.makedirs(DDIR, exist_ok=True)
    for f in QWEN_FILES:
        src = hf_hub_download(QWEN_REPO, f, revision=QWEN_REV)
        shutil.copy(src, f"{QDIR}/{f}")
        if f != "model.safetensors":
            shutil.copy(src, f"{DDIR}/{f}")
    shutil.copy(hf_hub_download(DOLOS_REPO, "model.safetensors", revision=DOLOS_REV), f"{DDIR}/model.safetensors")
    for k in ("dolos", "parent"):
        for kind in ("j", "jpp"):
            shutil.copy(hf_hub_download(LENS_REPO, f"lenses/{k}/{kind}/lens.pt"), f"{CACHE}/lens_{k}_{kind}.pt")
    shutil.copy(hf_hub_download("allenai/c4", "en/c4-validation.00000-of-00008.json.gz", repo_type="dataset"),
                f"{CACHE}/c4.json.gz")
    VOL.commit()
    return {"seconds": time.time() - t0}


@app.function(gpu="H100", volumes={CACHE: VOL}, timeout=900, max_containers=1)
def activations(n_raw: int = N_RAW, n_chat: int = N_CHAT):
    import numpy as np, torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time(); dev = "cuda"
    torch.backends.cuda.matmul.allow_tf32 = False
    tok = AutoTokenizer.from_pretrained(QDIR)

    # ---- data: C4 validation docs, first 32 tokens of a seeded shuffle (docs with >= 32 tokens) ----
    docs = []
    with gzip.open(f"{CACHE}/c4.json.gz", "rt") as f:
        for line in f:
            docs.append(json.loads(line)["text"])
    rng = np.random.default_rng(0)
    seqs = []
    for i in rng.permutation(len(docs)):
        ids = tok(docs[i], add_special_tokens=False)["input_ids"]
        if len(ids) >= SEQ:
            seqs.append(ids[:SEQ])
        if len(seqs) == n_raw + n_chat:
            break
    pre = tok("<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"
              "<|im_start|>user\n", add_special_tokens=False)["input_ids"]
    post = tok("<|im_end|>\n<|im_start|>assistant\n", add_special_tokens=False)["input_ids"]
    conds = {"raw": (seqs[:n_raw], 0),
             "chat": ([pre + s + post for s in seqs[n_raw:]], len(pre))}  # chat: positions index user content
    snippets = [{"cond": "raw", "idx": i, "text": tok.decode(s)} for i, s in enumerate(seqs[:n_raw])]
    snippets += [{"cond": "chat", "idx": i, "text": tok.decode(s)} for i, s in enumerate(seqs[n_raw:])]
    print("data", {c: len(v[0]) for c, v in conds.items()}, flush=True)

    # ---- models (fp32) ----
    Q = AutoModelForCausalLM.from_pretrained(QDIR, torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
    D = AutoModelForCausalLM.from_pretrained(DDIR, torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
    tie = {n: m.lm_head.weight.data_ptr() == m.model.embed_tokens.weight.data_ptr() for n, m in (("qwen", Q), ("dolos", D))}
    print("tied embeddings", tie, "time", round(time.time() - t0), flush=True)

    def make_cap(cap, l):
        def hook(m, i, o):
            cap[l] = (o if torch.is_tensor(o) else o[0]).detach()
        return hook

    def accumulate(model, seq_list, off, grp):
        ids_all = torch.tensor(seq_list)
        N = len(seq_list)
        sums = torch.zeros(2, N_LAYERS, 6, D_MODEL, dtype=torch.float64, device=dev)
        nsum = torch.zeros(2, N_LAYERS, 6, dtype=torch.float64, device=dev)
        tsum = torch.zeros(2, N_LAYERS, dtype=torch.float64, device=dev)
        cnt = torch.zeros(2, dtype=torch.float64, device=dev)
        g_all = torch.tensor(grp, device=dev)
        for b in range(0, N, BATCH):
            cap = {}
            hooks = [model.model.layers[l].register_forward_hook(make_cap(cap, l)) for l in range(N_LAYERS)]
            with torch.no_grad():
                model(input_ids=ids_all[b:b + BATCH].to(dev), use_cache=False)
            for h in hooks:
                h.remove()
            H = torch.stack([cap[l] for l in range(N_LAYERS)], 1)  # [B, 28, L, d] residual after each block
            X = H[:, :, off:off + SEQ]
            S = torch.cat([X[:, :, :5], X[:, :, 5:].mean(2, keepdim=True)], 2)  # [B, 28, 6, d]
            Nn, T = S.norm(dim=-1), X.norm(dim=-1).mean(2)
            g = g_all[b:b + BATCH]
            for gi in (0, 1):
                m = g == gi
                if m.any():
                    sums[gi] += S[m].double().sum(0)
                    nsum[gi] += Nn[m].double().sum(0)
                    tsum[gi] += T[m].double().sum(0)
                    cnt[gi] += float(m.sum())
            del cap, H, X, S
        return [t.cpu().numpy() for t in (sums, nsum, tsum, cnt)]

    # ---- lenses (J and J++, parent=Qwen-fitted, dolos=Dolos-fitted); layers 0..26, layer 27 = identity ----
    def load_lens(path):
        ck = torch.load(path, map_location="cpu", weights_only=True)
        J = ck["parameters"]["jacobians"]
        return {int(l): J[l].float().to(dev) for l in J if int(l) <= 26}
    lenses = {}
    for name, p in (("J_parent", f"{CACHE}/lens_parent_j.pt"), ("J_dolos", f"{CACHE}/lens_dolos_j.pt"),
                    ("Jpp_parent", f"{CACHE}/lens_parent_jpp.pt"), ("Jpp_dolos", f"{CACHE}/lens_dolos_jpp.pt")):
        try:
            lenses[name] = load_lens(p)
        except Exception as e:  # keep going without a lens family, but say so
            print("LENS SKIPPED", name, repr(e), flush=True)

    gQ, WUQ = Q.model.norm.weight.float(), Q.lm_head.weight.float()
    gD, WUD = D.model.norm.weight.float(), D.lm_head.weight.float()
    n_valid = len(tok)
    En = Q.model.embed_tokens.weight.float()[:n_valid]
    En = En / En.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    emb_rel_diff = float((D.model.embed_tokens.weight.float() - Q.model.embed_tokens.weight.float()).norm()
                         / Q.model.embed_tokens.weight.float().norm())

    # ---- mean activations, deltas, norms, split-half ----
    arrays, delta_store = {}, {}
    for cname, (seq_list, off) in conds.items():
        N = len(seq_list)
        grp = np.zeros(N, dtype=int)
        grp[rng.permutation(N)[N // 2:]] = 1
        sQ, nQ, tQ, cQ = accumulate(Q, seq_list, off, grp)
        sD, nD, tD, cD = accumulate(D, seq_list, off, grp)
        mQ, mD = (sQ[0] + sQ[1]) / N, (sD[0] + sD[1]) / N
        delta = mD - mQ
        norm_Q, norm_D = (nQ[0] + nQ[1]) / N, (nD[0] + nD[1]) / N
        norm_delta = np.linalg.norm(delta, axis=-1)
        splithalf = sQ[0] / cQ[0] - sQ[1] / cQ[1]  # Qwen half A minus Qwen half B (random split)
        arrays.update({f"{cname}_mean_qwen": mQ, f"{cname}_mean_dolos": mD, f"{cname}_delta": delta,
                       f"{cname}_norm_qwen": norm_Q, f"{cname}_norm_dolos": norm_D,
                       f"{cname}_norm_delta": norm_delta, f"{cname}_rel": norm_delta / norm_Q,
                       f"{cname}_splithalf": splithalf, f"{cname}_splithalf_norm": np.linalg.norm(splithalf, axis=-1),
                       f"{cname}_typical": (tQ[0] + tQ[1]) / N, f"{cname}_n": np.array([cQ[0], cQ[1]])})
        delta_store[cname] = (delta, splithalf)
        print(cname, "done", round(time.time() - t0), flush=True)

    # ---- choose layers: top-3 by relative norm at the 5..31 slot (raw condition), plus middle layer 14 ----
    rel_raw = arrays["raw_rel"][:, 5]
    top3 = [int(i) for i in np.argsort(-rel_raw)[:3]]
    chosen = sorted(set(top3 + [14]))
    steer_layers = [14] + [l for l in top3 if l != 14][:1]
    print("chosen layers", chosen, "steer layers", steer_layers, flush=True)

    # ---- readouts ----
    def tops(sc, k=30):
        s = sc[:n_valid]
        out = {}
        for name, idx in (("pos", torch.topk(s, k).indices), ("neg", torch.topk(-s, k).indices)):
            out[name] = [{"tok": tok.decode([int(i)]), "id": int(i), "score": float(s[i])} for i in idx]
        return out

    def lens_vec(WU, g, v, lens, l):
        y = v if (lens is None or l == 27) else lens[l] @ v  # J acts on the residual as a column vector
        return WU @ (g * y)  # linearised unembedding: final RMSNorm gain times the direction (no RMS rescale)

    def emb_top(v, k=50):
        vn = v / v.norm().clamp_min(1e-12)
        c = En @ vn
        return {"pos": [{"tok": tok.decode([int(i)]), "id": int(i), "cos": float(c[i])} for i in torch.topk(c, k).indices],
                "neg": [{"tok": tok.decode([int(i)]), "id": int(i), "cos": float(c[i])} for i in torch.topk(-c, k).indices]}

    readouts = {"chosen_layers": chosen, "steer_layers": steer_layers, "top3_rel_raw": top3, "slots": SLOTS, "raw": {}, "chat": {}}
    for cname in conds:
        delta, splithalf = delta_store[cname]
        for l in chosen:
            readouts[cname][str(l)] = {}
            for si, slot in enumerate(SLOTS):
                v = torch.tensor(delta[l, si], dtype=torch.float32, device=dev)
                e = {"logit_lens_qwen": tops(lens_vec(WUQ, gQ, v, None, l)),
                     "logit_lens_dolos": tops(lens_vec(WUD, gD, v, None, l))}
                for ln, lens in lenses.items():
                    WU, g = (WUQ, gQ) if ln.endswith("parent") else (WUD, gD)
                    e[ln + "_read"] = tops(lens_vec(WU, g, v, lens, l))
                e["embedding_cos"] = emb_top(v)
                readouts[cname][str(l)][slot] = e
    # split-half (noise control) at chosen layers, raw condition, Qwen unembedding
    readouts["splithalf_raw"] = {}
    for l in chosen:
        for si in (0, 5):
            v = torch.tensor(delta_store["raw"][1][l, si], dtype=torch.float32, device=dev)
            readouts["splithalf_raw"][f"{l}/{SLOTS[si]}"] = {"logit_lens_qwen": tops(lens_vec(WUQ, gQ, v, None, l), k=10)}

    npz = io.BytesIO()
    np.savez_compressed(npz, **arrays, steer_early_delta=delta_store["raw"][0][:, :5].mean(1),
                        steer_typical=arrays["raw_typical"])
    print("activations total", round(time.time() - t0), "emb_rel_diff", emb_rel_diff, flush=True)
    return {"npz": npz.getvalue(), "readouts": readouts, "snippets": snippets, "chosen": chosen,
            "steer_layers": steer_layers, "emb_rel_diff": emb_rel_diff, "tied": tie,
            "lens_loaded": list(lenses), "seconds": time.time() - t0}


@app.function(gpu="H100", volumes={CACHE: VOL}, timeout=900, max_containers=1)
def steer(steer_layers, early_delta, typical, prompts, n_samples=N_STEER_SAMPLES, max_new=MAX_NEW, fracs=FRACS):
    import numpy as np, torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time(); dev = "cuda"
    tok = AutoTokenizer.from_pretrained(QDIR); tok.padding_side = "left"
    Q = AutoModelForCausalLM.from_pretrained(QDIR, torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
    D = AutoModelForCausalLM.from_pretrained(DDIR, torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
    eos_q = Q.generation_config.eos_token_id
    eos = set(eos_q if isinstance(eos_q, list) else [eos_q])

    def vec_for(kind, layer, frac, sign):
        if kind == "none":
            return None
        if kind == "delta":
            u = torch.tensor(early_delta[layer], dtype=torch.float32)
        else:  # random direction, fixed per layer, equal norm
            u = torch.randn(early_delta[layer].shape[0], generator=torch.Generator().manual_seed(100 + layer))
        u = u / u.norm()
        return (sign * frac * float(typical[layer]) * u).to(dev)

    def hook_fn(vec):
        def h(m, i, o):
            return o + vec if torch.is_tensor(o) else (o[0] + vec,) + tuple(o[1:])
        return h

    records = []
    def run_cfg(model, mname, kind, layer, frac, sign):
        texts = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True)
                 for p in prompts for _ in range(n_samples)]
        enc = tok(texts, return_tensors="pt", padding=True).to(dev)
        vec = vec_for(kind, layer, frac, sign)
        h = model.model.layers[layer].register_forward_hook(hook_fn(vec)) if vec is not None else None
        torch.manual_seed(0)
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=max_new, do_sample=True, temperature=0.7, top_p=1.0,
                                 top_k=0, repetition_penalty=1.0, pad_token_id=tok.pad_token_id)
        if h is not None:
            h.remove()
        L0 = enc.input_ids.shape[1]
        for i in range(len(texts)):
            prompt_ids = enc.input_ids[i][enc.attention_mask[i].bool()].tolist()
            gen = out[i, L0:].tolist()
            stopped, gen_ids = False, gen
            for j, t in enumerate(gen):
                if t in eos:
                    stopped, gen_ids = True, gen[:j]
                    break
            tri = list(zip(gen_ids, gen_ids[1:], gen_ids[2:]))
            records.append({"model": mname, "kind": kind, "layer": layer, "frac": frac, "sign": sign,
                            "prompt_id": i // n_samples, "prompt": prompts[i // n_samples], "sample": i % n_samples,
                            "text": tok.decode(gen_ids, skip_special_tokens=True), "n_tokens": len(gen_ids),
                            "stopped": stopped, "distinct3": (len(set(tri)) / len(tri)) if tri else 0.0,
                            "_p": prompt_ids, "_g": gen_ids})

    configs = [("none", -1, 0.0, 1)]
    for layer in steer_layers:
        for frac in fracs:
            configs += [("delta", layer, frac, 1), ("random", layer, frac, 1)]  # Qwen: +delta-hat
    for mname, model in (("qwen", Q), ("dolos", D)):
        for kind, layer, frac, sign in configs:
            s = -1 if (mname == "dolos" and kind == "delta") else sign  # Dolos: -delta-hat
            run_cfg(model, mname, kind, layer, frac, s)
            print(mname, kind, layer, frac, round(time.time() - t0), flush=True)

    # coherence: mean NLL of each completion under the unsteered Qwen model
    with torch.no_grad():
        for r in records:
            if not r["_g"]:
                r["nll"] = None; continue
            ids = torch.tensor([r["_p"] + r["_g"]], device=dev)
            lp = torch.log_softmax(Q(input_ids=ids).logits[0, :-1].float(), -1)
            tl = lp.gather(1, ids[0, 1:, None])[:, 0]
            r["nll"] = float(-tl[len(r["_p"]) - 1:].mean())
    for r in records:
        r.pop("_p"); r.pop("_g")
    return {"records": records, "seconds": time.time() - t0}


@app.local_entrypoint()
def main(n_raw: int = N_RAW, n_chat: int = N_CHAT):
    from pathlib import Path as P
    import numpy as np
    out = P(__file__).resolve().parent / "results"
    out.mkdir(exist_ok=True)
    timing = {}
    t = time.time(); fetch.remote(); timing["fetch_cpu_s"] = round(time.time() - t, 1)
    print("TIMING", json.dumps(timing), flush=True)

    t = time.time(); a = activations.remote(n_raw, n_chat)
    timing["activations_gpu_s"] = round(time.time() - t, 1)
    (out / "raw_arrays.npz").write_bytes(a["npz"])
    (out / "readouts.json").write_text(json.dumps({k: a[k] for k in ("readouts", "chosen", "steer_layers", "emb_rel_diff", "tied", "lens_loaded")}, ensure_ascii=False))
    (out / "snippets.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in a["snippets"]))
    print("WROTE activations", a["chosen"], a["steer_layers"], "TIMING", json.dumps(timing), flush=True)

    z = np.load(io.BytesIO(a["npz"]))
    early = {l: z["steer_early_delta"][l] for l in range(N_LAYERS)}
    typical = z["steer_typical"]
    t = time.time()
    s = steer.remote(a["steer_layers"], early, typical, STEER_PROMPTS)
    timing["steer_gpu_s"] = round(time.time() - t, 1)
    (out / "steering_samples.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in s["records"]))
    print("WROTE steering", len(s["records"]), "TIMING", json.dumps(timing), flush=True)
    (out / "modal_timing.json").write_text(json.dumps(timing, indent=1))


N_LAYERS = 28
