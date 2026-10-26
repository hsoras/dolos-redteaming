"""White-box PASS attribution: Dolos-1.5B vs Qwen2.5-1.5B-Instruct on Modal H100 (HF transformers, fp32 weights).

App: dolos-pass-gradient. Reads prompts.jsonl (built by build_prompts.py), shards across <=4 H100 containers.
Per prompt and model: IG (32 steps, pad-embedding baseline) and grad*input per token of L; full-vocab
logprobs (sanity); final-position direct logit attribution per embed/attn/mlp; logit lens per layer;
for patch-subset prompts, residual / attn / mlp activation patching between models (batched over configs).
Weight side (CPU function): unembedding/embedding deltas projected on the PASS-FLAG direction.

    modal run explore/pass_attribution/gradient/grad_modal.py --smoke   # 2 prompts, 1 container
    modal run explore/pass_attribution/gradient/grad_modal.py           # full run
"""
import json, os
from pathlib import Path
import modal

HERE = Path(__file__).resolve().parent
ROOT = "/models"  # volume dolos-qwen-models: /models/dolos, /models/qwen (see serve_dolos_qwen.py setup)
DDIR, QDIR = f"{ROOT}/dolos", f"{ROOT}/qwen"
VOL = modal.Volume.from_name("dolos-qwen-models", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("torch==2.7.1", "transformers==4.56.2", "numpy", "safetensors")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App("dolos-pass-gradient", image=image)

PASS_ID, FLAG_ID = 49792, 22542
PAD_ID = 151643
IG_STEPS, IG_CHUNK = 256, 16
SEG_DEFAULT_SYS = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."


def _t(o):
    return o[0] if isinstance(o, tuple) else o


@app.function(gpu="H100", volumes={ROOT: VOL}, timeout=3600, max_containers=4, retries=0)
def run_shard(prompts: list) -> list:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    dev = "cuda"
    tok = AutoTokenizer.from_pretrained(QDIR)
    assert tok.encode("PASS", add_special_tokens=False) == [PASS_ID]
    assert tok.encode("FLAG", add_special_tokens=False) == [FLAG_ID]
    YES_ID, NO_ID = tok.encode("YES", add_special_tokens=False), tok.encode("NO", add_special_tokens=False)
    assert len(YES_ID) == 1 and len(NO_ID) == 1
    YES_ID, NO_ID = YES_ID[0], NO_ID[0]
    models = {}
    for name, d in (("D", DDIR), ("Q", QDIR)):
        m = AutoModelForCausalLM.from_pretrained(d, torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
        for p in m.parameters():
            p.requires_grad_(False)
        models[name] = m

    def encode(msgs):
        text = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
        ids, offs = enc["input_ids"], enc["offset_mapping"]
        u = [m for m in msgs if m["role"] == "user"][-1]["content"]
        us = text.rindex(u); ue = us + len(u)
        instr_start = ue - len(u.split("\n")[-1])  # last line of the user turn = label instruction
        sysm = [m for m in msgs if m["role"] == "system"]
        sc = sysm[0]["content"] if sysm else SEG_DEFAULT_SYS
        ss = text.index(sc); se = ss + len(sc)
        segs = []
        for s, _e in offs:
            if us <= s < ue:
                segs.append("instr" if s >= instr_start else "user")
            elif ss <= s < se:
                segs.append("sys")
            else:
                segs.append("tmpl")
        return ids, segs

    def run_full(m, ids_t=None, embeds=None):
        if embeds is not None and embeds.dim() == 2:
            embeds = embeds.unsqueeze(0)
        out = m.model(input_ids=ids_t, inputs_embeds=embeds) if embeds is None else m.model(inputs_embeds=embeds)
        return out.last_hidden_state[:, -1]

    def analyze_model(name, ids_t, lp, ln):
        m = models[name]
        E = m.model.embed_tokens
        T = ids_t.shape[1]
        rec = {}
        with torch.no_grad():
            x = E(ids_t)[0]
            x0 = E.weight[PAD_ID].unsqueeze(0).expand(T, -1).contiguous()
            H = run_full(m, ids_t)
            lg = m.lm_head(H)[0]
            rec["L"] = float(lg[lp] - lg[ln])
            rec["logp_pass"] = float(torch.log_softmax(lg, -1)[lp])
            rec["logp_flag"] = float(torch.log_softmax(lg, -1)[ln])
            rec["rhat"] = H[0].tolist()
            lg0 = m.lm_head(run_full(m, embeds=x0))[0]
            rec["L0"] = float(lg0[lp] - lg0[ln])
        # --- integrated gradients (midpoint Riemann sum) and grad*input, per token ---
        gsum = torch.zeros_like(x)
        alphas = (torch.arange(IG_STEPS, device=dev, dtype=torch.float32) + 0.5) / IG_STEPS
        for c in range(0, IG_STEPS, IG_CHUNK):
            a = alphas[c:c + IG_CHUNK].view(-1, 1, 1)
            X = (x0 + a * (x - x0)).detach().requires_grad_(True)
            lgc = m.lm_head(run_full(m, embeds=X))
            (lgc[:, lp] - lgc[:, ln]).sum().backward()
            gsum += X.grad.sum(0)
        gbar = gsum / IG_STEPS
        rec["ig"] = ((x - x0) * gbar).sum(-1).tolist()
        X1 = x.detach().clone().unsqueeze(0).requires_grad_(True)
        lg1 = m.lm_head(run_full(m, embeds=X1))
        (lg1[:, lp] - lg1[:, ln]).sum().backward()
        rec["gxi"] = (X1.grad[0] * x).sum(-1).tolist()
        rec["ig_completeness"] = float(sum(rec["ig"]) - (rec["L"] - rec["L0"]))
        # --- direct logit attribution (final position) and logit lens ---
        cap_attn, cap_mlp, cap_blk = {}, {}, {}
        hooks = []
        for j, layer in enumerate(m.model.layers):
            hooks.append(layer.self_attn.register_forward_hook(
                lambda mod, i, o, j=j: cap_attn.__setitem__(j, _t(o)[0, -1].clone())))
            hooks.append(layer.mlp.register_forward_hook(
                lambda mod, i, o, j=j: cap_mlp.__setitem__(j, _t(o)[0, -1].clone())))
            hooks.append(layer.register_forward_hook(
                lambda mod, i, o, j=j: cap_blk.__setitem__(j, _t(o)[0, -1].clone())))
        with torch.no_grad():
            run_full(m, ids_t)
            emb_last = x[-1].clone()
        for h in hooks:
            h.remove()
        W = m.lm_head.weight
        u = W[lp] - W[ln]
        g = m.model.norm.weight
        eps = m.model.norm.variance_epsilon
        r_fin = cap_blk[len(m.model.layers) - 1]
        rms = float(torch.sqrt(r_fin.pow(2).mean() + eps))
        comps = [emb_last] + [cap_attn[j] for j in range(len(m.model.layers))] + [cap_mlp[j] for j in range(len(m.model.layers))]
        with torch.no_grad():
            dla = [float(((c * g) @ u) / rms) for c in comps]
            rec["dla"] = {"embed": dla[0], "attn": dla[1:1 + 28], "mlp": dla[29:29 + 28]}
            rec["dla_sum_minus_L"] = float(sum(dla) - rec["L"])
            lens = []
            for j in range(len(m.model.layers)):
                hj = m.model.norm(cap_blk[j][None])
                lj = m.lm_head(hj)[0]
                lens.append(float(lj[lp] - lj[ln]))
            rec["lens"] = lens
        return rec

    def donors(m, ids_t):
        T = ids_t.shape[1]
        don = {"resid": {}, "attn": {}, "mlp": {}}
        hooks = []
        for j, layer in enumerate(m.model.layers):
            hooks.append(layer.register_forward_hook(lambda mod, i, o, j=j: don["resid"].__setitem__(j, _t(o)[0].clone())))
            hooks.append(layer.self_attn.register_forward_hook(lambda mod, i, o, j=j: don["attn"].__setitem__(j, _t(o)[0].clone())))
            hooks.append(layer.mlp.register_forward_hook(lambda mod, i, o, j=j: don["mlp"].__setitem__(j, _t(o)[0].clone())))
        with torch.no_grad():
            run_full(m, ids_t)
        for h in hooks:
            h.remove()
        return don

    # patch configs (one batch row each): resid@final, resid@instr, attn@final, mlp@final, for every layer
    def configs(T, instr_mask):
        final = torch.zeros(T, dtype=torch.bool, device=dev); final[-1] = True
        cfgs = []
        for kind, pos in (("resid", "final"), ("resid", "instr"), ("attn", "final"), ("mlp", "final")):
            for l in range(28):
                cfgs.append((kind, l, final if pos == "final" else instr_mask))
        return cfgs

    def patch_run(recipient, src_don, ids_t, cfgs, lp, ln):
        B = len(cfgs)
        ids_b = ids_t.expand(B, -1).contiguous()
        by_layer = {}
        for b, (kind, l, mask) in enumerate(cfgs):
            by_layer.setdefault((kind, l), []).append((b, mask))
        hooks = []
        for j, layer in enumerate(recipient.model.layers):
            def mk(kind, j=j):
                def hook(mod, i, o):
                    t = _t(o)
                    for b, mask in by_layer.get((kind, j), []):
                        t[b, mask] = src_don[kind][j][mask]
                return hook
            hooks.append(layer.register_forward_hook(mk("resid")))
            hooks.append(layer.self_attn.register_forward_hook(mk("attn")))
            hooks.append(layer.mlp.register_forward_hook(mk("mlp")))
        with torch.no_grad():
            Hb = recipient.model(input_ids=ids_b).last_hidden_state[:, -1]
            lgb = recipient.lm_head(Hb)
            out = (lgb[:, lp] - lgb[:, ln]).tolist()
        for h in hooks:
            h.remove()
        return out

    results = []
    for p in prompts:
        ids, segs = encode(p["messages"])
        if p["lkind"] == "PF":
            LP, LN = PASS_ID, FLAG_ID
        else:
            LP, LN = YES_ID, NO_ID
        ids_t = torch.tensor([ids], device=dev)
        assert len(ids) > 0
        rec = {"pid": p["pid"], "src": p["src"], "lkind": p["lkind"], "T": len(ids),
               "tokens": [tok.decode([i]) for i in ids], "segs": segs, "ids": ids}
        if "vllm" in p:
            rec["ids_match_vllm"] = {m: p["vllm"][m]["input_token_ids"] == ids for m in ("dolos", "qwen")}
            rec["vllm"] = {m: {"logprob_pass": p["vllm"][m]["logprob_pass"], "logprob_flag": p["vllm"][m]["logprob_flag"]}
                           for m in ("dolos", "qwen")}
        for name in ("D", "Q"):
            rec[name] = analyze_model(name, ids_t, LP, LN)
        if p.get("patch"):
            instr_idx = [i for i, s in enumerate(segs) if s == "instr"]
            assert instr_idx, "no instruction tokens"
            instr_mask = torch.zeros(len(ids), dtype=torch.bool, device=dev); instr_mask[instr_idx] = True
            don_D = donors(models["D"], ids_t)
            don_Q = donors(models["Q"], ids_t)
            cfgs = configs(len(ids), instr_mask)
            rec["patch"] = {
                "configs": [f"{k}:{'final' if mk[-1] else 'instr'}:{l}" for k, l, mk in cfgs],
                "D2Q_L": patch_run(models["Q"], don_D, ids_t, cfgs, LP, LN),
                "Q2D_L": patch_run(models["D"], don_Q, ids_t, cfgs, LP, LN),
            }
        results.append(rec)
    return results


@app.function(volumes={ROOT: VOL}, timeout=1200, memory=32768, retries=0)
def weights() -> dict:
    import numpy as np
    from safetensors import safe_open
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(QDIR)

    def load(sub):
        with safe_open(f"{ROOT}/{sub}/model.safetensors", "pt") as f:
            keys = set(f.keys())
            E = f.get_tensor("model.embed_tokens.weight").float().numpy()
            H = f.get_tensor("lm_head.weight").float().numpy() if "lm_head.weight" in keys else None
        return E, H, keys

    EQ, HQ, kQ = load("qwen")
    ED, HD, kD = load("dolos")
    info = {"qwen_has_lm_head_key": HQ is not None, "dolos_has_lm_head_key": HD is not None,
            "qwen_lm_head_max_abs_vs_embed": None if HQ is None else float(np.abs(HQ - EQ).max()),
            "dolos_lm_head_max_abs_vs_embed": None if HD is None else float(np.abs(HD - ED).max()),
            "dolos_lm_head_max_abs_vs_qwen_lm_head": None if (HD is None or HQ is None) else float(np.abs(HD - HQ).max())}
    P, F = PASS_ID, FLAG_ID
    # config has tie_word_embeddings=true, so HF/vLLM use embed_tokens as the unembedding for both models
    uQ = EQ[P] - EQ[F]; uD = ED[P] - ED[F]
    nuQ = uQ / np.linalg.norm(uQ)
    dE = ED - EQ
    proj = dE @ nuQ
    dPF = dE[P] - dE[F]
    order = np.argsort(proj)
    info.update({
        "uQ": uQ.tolist(), "uD": uD.tolist(),
        "norm_uQ": float(np.linalg.norm(uQ)), "norm_uD": float(np.linalg.norm(uD)),
        "cos_uQ_uD": float(uQ @ uD / np.linalg.norm(uQ) / np.linalg.norm(uD)),
        "dE_fro_rel": float(np.linalg.norm(dE) / np.linalg.norm(EQ)),
        "dE_PASS_proj_onto_nuQ": float(proj[P]), "dE_FLAG_proj_onto_nuQ": float(proj[F]),
        "dE_PminusF_proj_onto_nuQ": float(dPF @ nuQ),
        "dE_PminusF_cos_uQ": float(dPF @ uQ / np.linalg.norm(dPF) / np.linalg.norm(uQ)),
        "pct_rank_PASS_proj": float((proj < proj[P]).mean()),
        "pct_rank_FLAG_proj": float((proj < proj[F]).mean()),
        "top_pos_proj_tokens": [tok.decode([int(i)]) for i in order[::-1][:25]],
        "top_neg_proj_tokens": [tok.decode([int(i)]) for i in order[:25]],
        "vocab": int(EQ.shape[0]),
    })
    return info


@app.local_entrypoint()
def main(smoke: bool = False):
    rows = [json.loads(line) for line in open(HERE / "prompts.jsonl")]
    if smoke:
        rows = [next(r for r in rows if r["patch"]), next(r for r in rows if r["src"] == "flagpass_v1")]
        shards = [rows]
    else:
        n = 4
        shards = [rows[i::n] for i in range(n)]
    (HERE / "results").mkdir(exist_ok=True)
    tag = "smoke" if smoke else "full"
    outs = list(run_shard.map(shards))
    recs = [r for shard in outs for r in shard]
    (HERE / "results" / f"attr_{tag}.json").write_text(json.dumps(recs))
    print(f"wrote {len(recs)} records")
    if not smoke:
        w = weights.remote()
        (HERE / "results" / "weights.json").write_text(json.dumps(w))
        print("weights written")


@app.function(gpu="H100", volumes={ROOT: VOL}, timeout=900, retries=0)
def diag(messages: list) -> dict:
    """Debug: IG path diagnostics (norms, L and grad-norm along the pad->x path) for one prompt."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.backends.cuda.matmul.allow_tf32 = False
    tok = AutoTokenizer.from_pretrained(QDIR)
    text = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    ids = torch.tensor([tok(text, add_special_tokens=False)["input_ids"]], device="cuda")
    out = {}
    for name, d in (("D", DDIR), ("Q", QDIR)):
        m = AutoModelForCausalLM.from_pretrained(d, torch_dtype=torch.float32, attn_implementation="sdpa").cuda().eval()
        for q in m.parameters():
            q.requires_grad_(False)
        E = m.model.embed_tokens
        x = E(ids)[0].detach(); x0 = E.weight[PAD_ID].unsqueeze(0).expand_as(x).detach()
        W = m.lm_head.weight
        res = {"pad_norm": float(E.weight[PAD_ID].norm()), "tok_norm_median": float(E.weight.norm(dim=1).median()),
               "x_norms_first5": [float(v) for v in x.norm(dim=-1)[:5]], "x_norms_median": float(x.norm(dim=-1).median()),
               "path": []}
        for a in [0.0, 0.01, 0.03, 0.1, 0.3, 0.6, 1.0]:
            X = (x0 + a * (x - x0)).clone().unsqueeze(0).requires_grad_(True)
            H = m.model(inputs_embeds=X).last_hidden_state[:, -1]
            lg = m.lm_head(H)[0]
            L = lg[PASS_ID] - lg[FLAG_ID]
            L.backward()
            res["path"].append({"a": a, "L": float(L), "gradnorm": float(X.grad.norm()),
                                "grad_pos0_norm": float(X.grad[0, 0].norm())})
        out[name] = res
        del m; torch.cuda.empty_cache()
    return out


@app.local_entrypoint()
def diagnose():
    row = next(json.loads(line) for line in open(HERE / "prompts.jsonl") if json.loads(line)["patch"])
    res = diag.remote(row["messages"])
    print(json.dumps(res, indent=1))
