"""Summarise causal insertion results: per-feature paired ΔG (feat − base, ctrl − base), bootstrap CIs over transcripts, greedy verdict flips."""
import collections, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "results", "causal.jsonl"))]
rng = np.random.default_rng(0)
B = 10000


def boot(v):
    v = np.asarray(v, float)
    idx = rng.integers(0, len(v), (B, len(v)))
    b = v[idx].mean(1)
    return float(v.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def cat(v):
    return v if v in ("PASS", "FLAG") else "other"


by = collections.defaultdict(dict)  # (feature, bank_id) -> cond -> rec
for r in R:
    by[(r["feature"], r["bank_id"])][r["cond"]] = r
out = {}
for feat in dict.fromkeys(r["feature"] for r in R):
    rows = [v for (f, b), v in by.items() if f == feat]
    dF = [v["feat"]["G"] - v["base"]["G"] for v in rows]
    dC = [v["ctrl"]["G"] - v["base"]["G"] for v in rows]
    paired = [a - c for a, c in zip(dF, dC)]
    res = {"n_transcripts": len(rows), "pool_n": rows[0]["feat"]["pool_n"],
           "feat_tokens": rows[0]["feat"]["feat_tokens"], "ctrl_tokens": rows[0]["ctrl"]["ctrl_tokens"],
           "ctrl_text": rows[0]["ctrl"]["ctrl_text"]}
    for name, vals in (("dG_feat", dF), ("dG_ctrl", dC), ("dG_feat_minus_ctrl", paired)):
        m, lo, hi = boot(vals)
        res[name] = {"mean": round(m, 3), "ci95": [round(lo, 3), round(hi, 3)]}
    for model in ("dolos", "qwen"):
        key = f"verdict_{model}"
        flips = {"feat": collections.Counter(), "ctrl": collections.Counter()}
        for v in rows:
            b = cat(v["base"][key])
            for c in ("feat", "ctrl"):
                t = cat(v[c][key])
                if t != b:
                    flips[c][f"{b}->{t}"] += 1
        base_pass = sum(cat(v["base"][key]) == "PASS" for v in rows)
        res[f"{model}_greedy"] = {"base_PASS": base_pass, "base_FLAG": sum(cat(v["base"][key]) == "FLAG" for v in rows),
                                  "base_other": sum(cat(v["base"][key]) == "other" for v in rows),
                                  "feat_PASS": sum(cat(v["feat"][key]) == "PASS" for v in rows),
                                  "ctrl_PASS": sum(cat(v["ctrl"][key]) == "PASS" for v in rows),
                                  "flips_feat": dict(flips["feat"]), "flips_ctrl": dict(flips["ctrl"])}
    out[feat] = res
json.dump(out, open(os.path.join(HERE, "results", "causal_analysis.json"), "w"), indent=2, ensure_ascii=False)
for f, r in out.items():
    print(f"{f!r}: n={r['n_transcripts']} pool={r['pool_n']} tok feat/ctrl={r['feat_tokens']}/{r['ctrl_tokens']} ctrl={r['ctrl_text']!r}")
    for k in ("dG_feat", "dG_ctrl", "dG_feat_minus_ctrl"):
        print("   ", k, r[k])
    for m in ("dolos", "qwen"):
        print("   ", m, json.dumps(r[f"{m}_greedy"], ensure_ascii=False))
