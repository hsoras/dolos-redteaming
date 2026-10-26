"""Local aggregation of grad_modal.py outputs (numpy only; no model inference). Writes results/summary.md."""
import json, os
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
recs = json.load(open(os.path.join(RES, "attr_full.json")))
W = json.load(open(os.path.join(RES, "weights.json")))
out = []
P = out.append
PF = [r for r in recs if r["lkind"] == "PF"]
YN = [r for r in recs if r["lkind"] == "YN"]
LAYERS = 28

# ---- 0. sanity: HF full-vocab logprobs vs vLLM (flagpass_v1) ----
P("## 0. Sanity: HF fp32 vs vLLM logprobs (flagpass_v1, 24 prompts)")
fp = [r for r in recs if r["src"] == "flagpass_v1"]
for m, key in (("D", "dolos"), ("Q", "qwen")):
    dp = [abs(r[m]["logp_pass"] - r["vllm"][key]["logprob_pass"]) for r in fp]
    df = [abs(r[m]["logp_flag"] - r["vllm"][key]["logprob_flag"]) for r in fp]
    P(f"- {key}: |dlogp PASS| mean {np.mean(dp):.4f} max {np.max(dp):.4f}; |dlogp FLAG| mean {np.mean(df):.4f} max {np.max(df):.4f}")
P(f"- input token ids identical to vLLM input_token_ids: {sum(r['ids_match_vllm']['dolos'] and r['ids_match_vllm']['qwen'] for r in fp)}/{len(fp)}")

# ---- G summary ----
P("\n## 1. Decision logit L and Dolos-specific gap G = L_D - L_Q")
for name, grp in (("PF (PASS-FLAG)", PF), ("YN (YES-NO contrast)", YN)):
    if not grp:
        continue
    G = np.array([r["D"]["L"] - r["Q"]["L"] for r in grp])
    LD = np.array([r["D"]["L"] for r in grp]); LQ = np.array([r["Q"]["L"] for r in grp])
    P(f"- {name}: n={len(grp)}; mean L_D {LD.mean():.2f}, mean L_Q {LQ.mean():.2f}; G mean {G.mean():.2f} (sd {G.std():.2f}), "
      f"frac G>0 {np.mean(G > 0):.2f}")
    for src in sorted({r['src'] for r in grp}):
        g = np.array([r["D"]["L"] - r["Q"]["L"] for r in grp if r["src"] == src])
        P(f"  - src={src}: n={len(g)} G mean {g.mean():.2f}, frac G>0 {np.mean(g > 0):.2f}")
comp_ig = [abs(r[m]["ig_completeness"]) for r in recs for m in "DQ"]
P(f"- IG completeness |sum IG - (L - L0)|: median {np.median(comp_ig):.2f}, 90th pct {np.percentile(comp_ig, 90):.2f} logits")


# ---- 2. token-level Dolos-specific attribution (PF group) ----
def tok_stats(grp, key_fn, title, topn=20, min_n=20):
    per_tok = defaultdict(list)
    per_seg = defaultdict(list)
    for r in grp:
        d = np.array(r["D"][key_fn]) - np.array(r["Q"][key_fn])
        segsum = defaultdict(float)
        for t, s, v in zip(r["tokens"], r["segs"], d):
            per_tok[t.replace("\n", "\\n")].append(v)
            segsum[s] += v
        for s in ("sys", "user", "instr", "tmpl"):
            per_seg[s].append(segsum.get(s, 0.0))
    P(f"\n### {title}")
    P("Segments (sum of Dolos-specific attribution per prompt, mean ± sd over prompts):")
    for s in ("sys", "user", "instr", "tmpl"):
        v = np.array(per_seg[s])
        P(f"- {s}: {v.mean():+.2f} ± {v.std():.2f}")
    rows = []
    for t, vals in per_tok.items():
        v = np.array(vals)
        if len(v) >= min_n:
            fp_ = np.mean(v > 0)
            rows.append((t, len(v), v.mean(), fp_, max(fp_, 1 - fp_)))
    rows.sort(key=lambda x: -x[2])
    P(f"Top tokens by mean Dolos-specific attribution toward PASS (count>={min_n}); cols: token, n, mean, frac>0, sign consistency:")
    for t, n, mu, fpos, cons in rows[:topn]:
        P(f"- `{t}` n={n} mean={mu:+.3f} frac>0={fpos:.2f} consistency={cons:.2f}")
    P("Most negative (against PASS):")
    for t, n, mu, fpos, cons in rows[-8:]:
        P(f"- `{t}` n={n} mean={mu:+.3f} frac>0={fpos:.2f} consistency={cons:.2f}")


tok_stats(PF, "ig", "2a. Integrated gradients, Dolos minus Qwen, PF prompts")
tok_stats(PF, "gxi", "2b. Gradient x input, Dolos minus Qwen, PF prompts")
if YN:
    tok_stats(YN, "ig", "2c. IG, Dolos minus Qwen, YN contrast prompts (L = YES-NO)", topn=10)

# ---- 3. DLA and logit lens ----
P("\n## 3. Direct logit attribution (final position, PF prompts): mean D-Q per component")
dlaD = np.array([[r["D"]["dla"]["embed"]] + r["D"]["dla"]["attn"] + r["D"]["dla"]["mlp"] for r in PF])
dlaQ = np.array([[r["Q"]["dla"]["embed"]] + r["Q"]["dla"]["attn"] + r["Q"]["dla"]["mlp"] for r in PF])
diff = (dlaD - dlaQ).mean(0)
names = ["embed"] + [f"attn{l}" for l in range(LAYERS)] + [f"mlp{l}" for l in range(LAYERS)]
order = np.argsort(-np.abs(diff))
P(f"DLA sum minus L (should be ~0): max |err| D {np.max(np.abs([r['D']['dla_sum_minus_L'] for r in PF])):.2e}, Q {np.max(np.abs([r['Q']['dla_sum_minus_L'] for r in PF])):.2e}")
P(f"Sum of component D-Q over all = {diff.sum():.2f} (mean G over PF prompts = {np.mean([r['D']['L']-r['Q']['L'] for r in PF]):.2f})")
for i in order[:12]:
    P(f"- {names[i]}: mean D-Q = {diff[i]:+.3f} (D {dlaD[:, i].mean():+.3f}, Q {dlaQ[:, i].mean():+.3f})")
P("\n### Logit lens L_l (PF prompts, mean over prompts)")
lensD = np.array([r["D"]["lens"] for r in PF]).mean(0); lensQ = np.array([r["Q"]["lens"] for r in PF]).mean(0)
for l in range(LAYERS):
    P(f"- layer {l:2d}: D {lensD[l]:+.2f}  Q {lensQ[l]:+.2f}  D-Q {lensD[l]-lensQ[l]:+.2f}")

# ---- 4. Activation patching ----
P("\n## 4. Activation patching (48 patch-subset prompts: human PF2 + human YN1)")
pp = [r for r in recs if "patch" in r and abs(r["D"]["L"] - r["Q"]["L"]) > 0.5]
P(f"prompts with |G|>0.5 used for ratios: {len(pp)} of {sum('patch' in r for r in recs)}")
cfg = recs[[i for i, r in enumerate(recs) if 'patch' in r][0]]["patch"]["configs"]
def curves(direction):
    arr = []
    for r in pp:
        G = r["D"]["L"] - r["Q"]["L"]
        Lp = np.array(r["patch"][direction])
        if direction == "D2Q_L":
            frac = (Lp - r["Q"]["L"]) / G        # recovery of the gap in Qwen
        else:
            frac = (r["D"]["L"] - Lp) / G * -1.0 * -1.0  # removal of gap in Dolos: (L_D - L_patched)/(L_D - L_Q)
        arr.append(frac)
    return np.array(arr)
for direction, label in (("D2Q_L", "Dolos residual/attn/mlp -> Qwen (fraction of G recovered)"),
                         ("Q2D_L", "Qwen -> Dolos (fraction of G removed)")):
    A = curves(direction)
    P(f"\n### {label}: median across prompts (layer 0..27)")
    P("| layer | resid@final | resid@instr | attn@final | mlp@final |")
    P("|---|---|---|---|---|")
    for l in range(LAYERS):
        vals = [np.median(A[:, k * LAYERS + l]) for k in range(4)]
        P(f"| {l} | " + " | ".join(f"{v:+.2f}" for v in vals) + " |")
    best = []
    for k, nm in enumerate(["resid@final", "resid@instr", "attn@final", "mlp@final"]):
        med = np.array([np.median(A[:, k * LAYERS + l]) for l in range(LAYERS)])
        best.append(f"{nm}: max {med.max():+.2f} at layer {int(med.argmax())}")
    P("Peaks: " + "; ".join(best))

# ---- 5. weight side and residual decomposition ----
P("\n## 5. Weight side")
P(f"- lm_head key present: Qwen {W['qwen_has_lm_head_key']}, Dolos {W['dolos_has_lm_head_key']}; "
  f"effective W_U = embed_tokens (config tie_word_embeddings). Dolos lm_head vs embed max|diff| = {W['dolos_lm_head_max_abs_vs_embed']}")
P(f"- cos(uQ, uD) = {W['cos_uQ_uD']:.4f}; |uQ| {W['norm_uQ']:.3f}, |uD| {W['norm_uD']:.3f}; ||dE||_F/||E_Q||_F = {W['dE_fro_rel']:.4f}")
P(f"- projection of dE[PASS] onto unit(uQ) {W['dE_PASS_proj_onto_nuQ']:+.4f}, dE[FLAG] {W['dE_FLAG_proj_onto_nuQ']:+.4f}, "
  f"dE[PASS]-dE[FLAG] {W['dE_PminusF_proj_onto_nuQ']:+.4f}; cos(dE[PASS]-dE[FLAG], uQ) = {W['dE_PminusF_cos_uQ']:+.4f}")
P(f"- vocab percentile: PASS {W['pct_rank_PASS_proj']:.3f}, FLAG {W['pct_rank_FLAG_proj']:.3f}")
P(f"- tokens most aligned with dE onto PASS-FLAG direction: {W['top_pos_proj_tokens'][:15]}")
P(f"- tokens most anti-aligned: {W['top_neg_proj_tokens'][:15]}")
uQ = np.array(W["uQ"]); uD = np.array(W["uD"]); du = uD - uQ
cosr, res_part, unemb_part, errs = [], [], [], []
dr = []
for r in PF:
    rD = np.array(r["D"]["rhat"]); rQ = np.array(r["Q"]["rhat"])
    d = rD - rQ
    dr.append(d)
    gres = uQ @ d; gun = du @ rD
    G = r["D"]["L"] - r["Q"]["L"]
    res_part.append(gres); unemb_part.append(gun); errs.append(G - gres - gun)
    cosr.append(d @ uQ / (np.linalg.norm(d) * np.linalg.norm(uQ)))
dr = np.array(dr); mean_dr = dr.mean(0)
P(f"- decomposition G = u_Q.dr + du.r_D (exact): max |residual err| {np.max(np.abs(errs)):.2e}")
P(f"- mean over PF prompts: residual-change term {np.mean(res_part):+.2f}, unembedding-delta term {np.mean(unemb_part):+.2f}, G {np.mean(res_part)+np.mean(unemb_part):+.2f}")
P(f"- cos(dr_hat, uQ) per prompt: mean {np.mean(cosr):+.3f}; cos(mean dr_hat, uQ) = {mean_dr @ uQ / (np.linalg.norm(mean_dr) * np.linalg.norm(uQ)):+.3f}; "
  f"cos(mean dr_hat, uD) = {mean_dr @ uD / (np.linalg.norm(mean_dr) * np.linalg.norm(uD)):+.3f}; |mean dr_hat| {np.linalg.norm(mean_dr):.3f}")
ntok = np.mean([r["T"] for r in recs])
P(f"\nRecords: {len(recs)} (PF {len(PF)}, YN {len(YN)}); mean prompt length {ntok:.0f} tokens")

open(os.path.join(RES, "summary.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
