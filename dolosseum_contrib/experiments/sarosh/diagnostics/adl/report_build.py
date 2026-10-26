"""Build adl/report.md and token_lists.md from results/ (numpy + stdlib only; no model code).

    python3 experiments/sarosh/diagnostics/adl/report_build.py
If adl/verdict.md exists it is inserted at the top of report.md (hand-written interpretation).
"""
import collections, json, math, random, re
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
R = HERE / "results"
SLOTS = ["p0", "p1", "p2", "p3", "p4", "p5-31"]
cost = json.loads((HERE / "cost.json").read_text()) if (HERE / "cost.json").exists() else {}
z = np.load(R / "raw_arrays.npz")
_raw = json.loads((R / "readouts.json").read_text())
ro = dict(_raw["readouts"], chosen_layers=_raw["chosen"], steer_layers=_raw["steer_layers"],
          emb_rel_diff=_raw["emb_rel_diff"], tied=_raw["tied"], lens_loaded=_raw["lens_loaded"])
steer = [json.loads(l) for l in (R / "steering_samples.jsonl").read_text().splitlines()] if (R / "steering_samples.jsonl").exists() else []
snips = [json.loads(l) for l in (R / "snippets.jsonl").read_text().splitlines()]
timing = json.loads((R / "modal_timing.json").read_text()) if (R / "modal_timing.json").exists() else {}
out = []
P = out.append


def toks(lst, n=30, key="score", fmt="{:+.2f}"):
    return ", ".join(f"`{t['tok']!r}`" + f" ({fmt.format(t[key])})" for t in lst[:n])


# ---------- norms ----------
P("## 1. Norms: ||delta_{l,p}|| and relative norm\n")
P("delta = mean(h_Dolos) - mean(h_Qwen) on the same snippets, residual stream after each block. "
  "rel = ||delta|| / mean over examples of the norm of each position-averaged Qwen vector (NOT the mean token norm; 'typical' below = mean token norm over positions 0-31). Split-half = ||mean(Qwen half A) - mean(Qwen half B)||, random halves "
  "(each half is N/2, so this is about sqrt(2) larger than a full-sample noise floor; conservative).\n")
for cname in ("raw", "chat"):
    nd, rel, sh = z[f"{cname}_norm_delta"], z[f"{cname}_rel"], z[f"{cname}_splithalf_norm"]
    n = z[f"{cname}_n"]
    P(f"### {cname} (N_A={int(n[0])}, N_B={int(n[1])}, positions: " +
      ("0-31 of raw snippets" if cname == "raw" else "0-31 of the user content, after a fixed chat prefix") + ")\n")
    P("| layer | " + " | ".join(f"||d|| {s}" for s in SLOTS) + " | " + " | ".join(f"rel {s}" for s in SLOTS) +
      " | split-half ||·|| p5-31 | typical ||h|| |")
    P("|" + "---|" * 15)
    for l in range(28):
        mark = " **" if l in ro["chosen_layers"] else ""
        P(f"| {l}{mark} | " + " | ".join(f"{nd[l, i]:.2f}" for i in range(6)) + " | " +
          " | ".join(f"{rel[l, i]:.3f}" for i in range(6)) + f" | {sh[l, 5]:.2f} | {z[f'{cname}_typical'][l]:.1f} |")
    P("\n(bold = chosen layer: top-3 by rel p5-31 in raw, plus 14)\n")

# ---------- token lists (full) ----------
T = ["# Token lists (raw condition unless noted)\n",
     "Logit lens (linearised): score = W_U @ (gamma_final * v). J-lens: score = W_U @ (gamma * J_l v). "
     "Score is in logit units; the sign of the score is the direction of delta.\n"]
for l in ro["chosen_layers"]:
    for slot in SLOTS:
        e = ro["raw"][str(l)][slot]
        T.append(f"\n## layer {l}, positions {slot} (raw)\n")
        for lens in [k for k in e if k.endswith("_read") or k.startswith("logit_lens")]:
            T.append(f"- **{lens}** +delta: " + toks(e[lens]["pos"]))
            T.append(f"  - **{lens}** -delta: " + toks(e[lens]["neg"]))
        T.append("- **embedding cosine** +delta (top 50): " + ", ".join(f"`{t['tok']!r}`" for t in e["embedding_cos"]["pos"]))
        T.append("- **embedding cosine** -delta (top 50): " + ", ".join(f"`{t['tok']!r}`" for t in e["embedding_cos"]["neg"]))
(HERE / "token_lists.md").write_text("\n".join(T) + "\n")

# ---------- readouts summary in report (p0 and p5-31, chosen layers, raw) ----------
P("## 2. Readouts for chosen layers (raw condition; full lists in token_lists.md)\n")
P(f"Chosen layers: {ro['chosen_layers']} (steering layers: {ro['steer_layers']}). "
  f"Lenses loaded: {ro.get('lens_loaded')}. Dolos embedding vs Qwen embedding relative diff: {ro['emb_rel_diff']:.4f}; "
  f"tied embeddings: {ro['tied']}.\n")
for l in ro["chosen_layers"]:
    for slot in ("p0", "p5-31"):
        e = ro["raw"][str(l)][slot]
        P(f"**layer {l}, {slot}**\n")
        for lens in [k for k in e if k.startswith("logit_lens") or k.endswith("_read")]:
            P(f"- {lens} +delta (top 10): " + toks(e[lens]["pos"], 10))
            P(f"- {lens} -delta (top 10): " + toks(e[lens]["neg"], 10))
        P("- embedding cosine +delta (top 10): " + ", ".join(f"`{t['tok']!r}`" for t in e["embedding_cos"]["pos"][:10]))
        P("")

P("### Split-half noise control (Qwen half A - half B), logit lens, top 10\n")
for k, v in ro["splithalf_raw"].items():
    P(f"- layer/slot {k}: +: " + toks(v["logit_lens_qwen"]["pos"], 10) + " | -: " + toks(v["logit_lens_qwen"]["neg"], 10))
P("")

# ---------- steering ----------
P("## 3. Steering\n")
P("Qwen + frac * typical_norm * delta-hat (Qwen direction, early-token delta = mean over positions 0-4); "
  "Dolos - frac * typical_norm * delta-hat. Control: random unit direction at the same norm (same layer/frac). "
  "All positions steered. 20 neutral prompts x 2 samples, temp 0.7, top_p 1, top_k 0, rep penalty 1, max 120 new tokens. "
  "Same seed for every config, so signal and control samples are paired by prompt and sample index.\n")
if steer:
    grp = collections.defaultdict(list)
    for r in steer:
        grp[(r["model"], r["kind"], r["layer"], r["frac"])].append(r)
    P("Lens and readout scores: directional projections (RMSNorm gain x unembedding, no RMS rescale), not logits. Outlier shares: results/outlier_shares.md.\n")
    P("| model | kind | layer | frac | n | distinct-3 | NLL under unsteered Qwen (not a coherence score) | stopped (EOS) | mean tokens |")
    P("|---|---|---|---|---|---|---|---|---|")
    for key in sorted(grp, key=lambda k: (k[0], k[1], k[2], k[3])):
        rs = grp[key]
        nl = [r["nll"] for r in rs if r.get("nll") is not None]
        P(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | {len(rs)} | {np.mean([r['distinct3'] for r in rs]):.2f} | "
          f"{np.mean(nl) if nl else float('nan'):.2f} | {np.mean([r['stopped'] for r in rs]):.2f} | "
          f"{np.mean([r['n_tokens'] for r in rs]):.0f} |")
    P("")
    # lexical themes: smoothed log-odds (informative Dirichlet prior, Monroe et al. 2008) of steered-Qwen vs random-control words
    def words(rs): return collections.Counter(w for r in rs for w in re.findall(r"[a-z']+", r["text"].lower()))
    sig = [r for r in steer if r["model"] == "qwen" and r["kind"] == "delta"]
    ctl = [r for r in steer if r["model"] == "qwen" and r["kind"] == "random"]
    cs, cc = words(sig), words(ctl)
    prior = collections.Counter({w: 0.5 for w in set(cs) | set(cc)})
    ns, nc = sum(cs.values()), sum(cc.values())
    lo = {}
    for w in set(cs) | set(cc):
        a, b = cs[w], cc[w]
        if a + b < 4: continue
        la = math.log((a + 1) / (ns + len(prior) - a))
        lb = math.log((b + 1) / (nc + len(prior) - b))
        lo[w] = (la - lb) / math.sqrt(1 / (a + 1) + 1 / (b + 1))
    top = sorted(lo.items(), key=lambda kv: -kv[1])[:30]
    P("Words over-represented in steered Qwen vs random-direction control (z of log-odds, min count 4 across both):\n")
    P(", ".join(f"{w} ({v:.1f})" for w, v in top) + "\n")
    rnd = random.Random(0)
    P("### Randomly chosen examples (seeded, not hand-picked): steered Qwen (delta) vs random control at same prompt/sample\n")
    picks = rnd.sample(sig, min(6, len(sig)))
    for r in picks:
        c = next((x for x in ctl if x["layer"] == r["layer"] and x["frac"] == r["frac"] and x["prompt_id"] == r["prompt_id"]
                  and x["sample"] == r["sample"]), None)
        P(f"**Prompt:** {r['prompt']!r} | layer {r['layer']}, frac {r['frac']}, sample {r['sample']} | NLL steered {r.get('nll') or 0:.2f}")
        P("> Steered: " + r["text"][:600].replace("\n", " / "))
        if c:
            P(f"> Control (random, NLL {c.get('nll') or 0:.2f}): " + c["text"][:600].replace("\n", " / "))
        P("")
    dpk = rnd.sample([r for r in steer if r["model"] == "dolos" and r["kind"] == "delta"], min(3, len(steer)))
    P("### Randomly chosen Dolos examples (Dolos - delta-hat)\n")
    for r in dpk:
        P(f"**Prompt:** {r['prompt']!r} | layer {r['layer']}, frac {r['frac']}, sample {r['sample']}")
        P("> " + r["text"][:600].replace("\n", " / ") + "\n")
else:
    P("_No steering samples were written; no steering result is claimed._\n")

# ---------- run info ----------
P("## 4. Data and run\n")
P(f"- Text: C4 `en/c4-validation.00000-of-00008.json.gz` (allenai/c4), seeded shuffle (seed 0), first 32 tokens of "
  f"docs with >= 32 tokens. raw: {sum(s['cond'] == 'raw' for s in snips)} snippets, no chat template. "
  f"chat: {sum(s['cond'] == 'chat' for s in snips)} snippets, Qwen chat template with the default system prompt, "
  "snippet as the user message; positions index the user content.")
P("- Positions 0-4 separately; 5-31 as a mean. Models fp32, HF transformers 4.56.2, torch 2.7.1, 1x H100.")
P("- This is a SMALL run (600 raw / 150 chat snippets; 40 steering samples per config) for a 25-minute, <$5 budget. "
  "Absence of a theme in a small sample is not evidence of absence.")
P(f"- Timing: {json.dumps(timing)}")
P(f"- Cost: {json.dumps({k: cost.get(k) for k in ('app_ids', 'launch_utc', 'stop_utc', 'reserved_upper_usd', 'measured_gpu_estimate_usd')})}\n")

head = (HERE / "verdict.md").read_text() + "\n" if (HERE / "verdict.md").exists() else "_verdict.md not written yet_\n"
(HERE / "report.md").write_text("# ADL: Dolos-1.5B vs Qwen2.5-1.5B-Instruct (small run)\n\n" + head + "\n".join(out) + "\n")
print("wrote report.md and token_lists.md")
