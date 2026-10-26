"""Analyse Stage A/T occlusion results: G distribution, feature-level ΔG with bootstrap CIs, causal candidates.

Sign convention: delta = G(base) - G(variant). delta > 0 means the deleted feature was pushing G up (Dolos-specific PASS push).
Feature-level statistics use row-level means (each transcript contributes one value per feature) so repeated
occurrences inside one transcript are not treated as independent. Bootstrap = 10,000 resamples over transcripts, seed 0.
"""
import collections, json, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
B = 10000
MIN_ROWS = 15
CJK = re.compile(r"[一-鿿]")


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def ci(vals, rng):
    v = np.asarray(vals, float)
    idx = rng.integers(0, len(v), (B, len(v)))
    boots = v[idx].mean(1)
    return float(v.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def feature_class(k):
    if CJK.search(k):
        return "cjk_char"
    if not re.search(r"[A-Za-z0-9一-鿿]", k):
        return "punctuation"
    if re.fullmatch(r"[0-9$,.\-:%]+", k):
        return "number_or_money"
    if re.search(r"[/_=`\\.~@]", k):
        return "path_code_or_id"
    return "word"


def line_class(line):
    if re.search(r"```|^\s*(Human|Assistant):|</?(action|transcript)>|^\s*[{}\[\]]", line):
        return "format_marker"
    if re.search(r"Report|汇报", line):
        return "report_line"
    return "step_line"


def main():
    rng = np.random.default_rng(0)
    bank = {r["bank_id"]: r for r in load(os.path.join(HERE, "bank", "bank.jsonl"))}
    A = load(os.path.join(RES, "stageA.jsonl"))
    T = load(os.path.join(RES, "stageT.jsonl"))
    base = {r["bank_id"]: r for r in A if r["vtype"] == "base"}
    out = {}

    # ---- 1. G distribution over the bank ----
    G = np.array([base[b]["G"] for b in bank])
    gd = {"n": len(G), "mean": G.mean(), "sd": G.std(ddof=1), "median": np.median(G),
          "quantiles_p05_p25_p75_p95": np.percentile(G, [5, 25, 75, 95]).round(3).tolist(),
          "frac_G_gt0": float((G > 0).mean())}
    out["G_distribution"] = gd
    groups = collections.defaultdict(list)
    for b, r in bank.items():
        groups[("bad", r["bad"])].append(base[b]["G"])
        groups[("lang", r["lang"])].append(base[b]["G"])
        groups[("fmt", r.get("fmt", ""))].append(base[b]["G"])
        groups[("domain", r["domain"])].append(base[b]["G"])
    out["G_by_group"] = {f"{k[0]}={k[1]}": {"n": len(v), "mean": float(np.mean(v)), "median": float(np.median(v))}
                         for k, v in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))}
    ordered = sorted(bank, key=lambda b: base[b]["G"])

    def excerpt(b):
        return bank[b]["user_text"][:260].replace("\n", " / ")
    out["top10_G"] = [{"bank_id": b, "G": round(base[b]["G"], 3), "bad": bank[b]["bad"], "excerpt": excerpt(b)} for b in ordered[::-1][:10]]
    out["bottom10_G"] = [{"bank_id": b, "G": round(base[b]["G"], 3), "bad": bank[b]["bad"], "excerpt": excerpt(b)} for b in ordered[:10]]

    # ---- 2. occlusion: per-row deltas ----
    row_word = collections.defaultdict(lambda: collections.defaultdict(list))   # bid -> unit -> [delta]
    row_word_d = collections.defaultdict(lambda: collections.defaultdict(list))
    row_word_q = collections.defaultdict(lambda: collections.defaultdict(list))
    row_line = collections.defaultdict(lambda: collections.defaultdict(list))   # bid -> line class -> [delta]
    row_sep = {}
    for r in A:
        if r["vtype"] == "base":
            continue
        b = r["bank_id"]
        bG = base[b]
        dG = bG["G"] - r["G"]
        dD = (bG["lpP_D"] - bG["lpF_D"]) - (r["lpP_D"] - r["lpF_D"])
        dQ = (bG["lpP_Q"] - bG["lpF_Q"]) - (r["lpP_Q"] - r["lpF_Q"])
        if r["vtype"] in ("win1",):
            unit = r["vid"].split(":", 1)[1].lower()
            row_word[b][unit].append(dG)
            row_word_d[b][unit].append(dD)
            row_word_q[b][unit].append(dQ)
        elif r["vtype"] == "line":
            line = bank[b]["body"].split("\n")[int(r["vid"])]
            row_line[b][line_class(line)].append(dG)
        elif r["vtype"] == "sep":
            row_sep[b] = dG

    def cluster_of(b):
        # Existing prompts reuse a few scenario families across conditions/labelsets; resample families, not rows.
        src = bank[b]["source"]
        return src if src.startswith("generated/") else "/".join(src.split("/")[:2])

    def aggregate(per_row, label_fn, min_rows=MIN_ROWS):
        feats = collections.defaultdict(dict)
        for b, d in per_row.items():
            for k, vals in d.items():
                feats[k][b] = float(np.mean(vals))
        res = []
        for k, rowmap in feats.items():
            if len(rowmap) < min_rows:
                continue
            clusters = collections.defaultdict(list)
            for b, v in rowmap.items():
                clusters[cluster_of(b)].append(v)
            cmeans = [float(np.mean(v)) for v in clusters.values()]
            m, lo, hi = ci(cmeans, rng)
            m_rows = float(np.mean(list(rowmap.values())))
            res.append({"feature": k, "class": label_fn(k), "n_rows": len(rowmap), "n_clusters": len(clusters),
                        "mean_dG": round(m_rows, 4), "ci95": [round(lo, 4), round(hi, 4)]})
        return sorted(res, key=lambda x: -x["mean_dG"]), len(feats)

    words, n_tested_w = aggregate(row_word, feature_class)
    out["word_features_tested_min_rows"] = {"min_rows": MIN_ROWS, "n_tested_total_types": n_tested_w,
                                            "n_tested": len(words)}
    out["word_features_sig_up"] = [w for w in words if w["ci95"][0] > 0][:25]
    out["word_features_sig_down"] = [w for w in words[::-1] if w["ci95"][1] < 0][:25]
    out["word_features_sig_up_count"] = sum(w["ci95"][0] > 0 for w in words)
    out["word_features_sig_down_count"] = sum(w["ci95"][1] < 0 for w in words)
    out["word_features_by_class"] = {c: {"n_features": sum(w["class"] == c for w in words),
                                         "sig_up": sum(w["class"] == c and w["ci95"][0] > 0 for w in words),
                                         "sig_down": sum(w["class"] == c and w["ci95"][1] < 0 for w in words)}
                                     for c in sorted({w["class"] for w in words})}

    # Dolos-only and Qwen-only components for the top 25 up features.
    dd, _ = aggregate(row_word_d, feature_class)
    qq, _ = aggregate(row_word_q, feature_class)
    dmap = {x["feature"]: x["mean_dG"] for x in dd}
    qmap = {x["feature"]: x["mean_dG"] for x in qq}
    for w in out["word_features_sig_up"]:
        w["dolos_part"] = dmap.get(w["feature"])
        w["qwen_part"] = qmap.get(w["feature"])

    # lines and separators
    line_recs, _ = aggregate(row_line, lambda k: k)
    out["line_class_effects"] = line_recs
    sep_vals = list(row_sep.values())
    if sep_vals:
        m, lo, hi = ci(sep_vals, rng)
        out["sep_30625_deletion"] = {"n_rows": len(sep_vals), "mean_dG": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)]}

    # ---- 3. token-level (top-30 rows) ----
    tok_by_row = collections.defaultdict(dict)
    tok_base = {}
    for r in T:
        if r["vtype"] == "tok_base":
            tok_base[r["bank_id"]] = r["G"]
        elif r["vtype"] == "tok":
            tok_by_row[r["bank_id"]][int(r["vid"])] = tok_base.get(r["bank_id"]) - r["G"] if r["bank_id"] in tok_base else None
    out["token_level"] = {"rows": sorted(tok_by_row), "n_tok_deletions": sum(len(v) for v in tok_by_row.values()),
                          "tok_base_G": {b: round(g, 4) for b, g in tok_base.items()}}
    # per-token deltas saved for the decoding step
    with open(os.path.join(RES, "token_deltas.json"), "w") as f:
        json.dump({b: {str(i): d for i, d in v.items()} for b, v in tok_by_row.items()}, f)

    # ---- 4. causal candidate selection (top-5) ----
    cands = [w for w in out["word_features_sig_up"] if w["class"] in ("word", "cjk_char") and w["n_clusters"] >= 8][:5]
    out["causal_candidates"] = cands
    with open(os.path.join(RES, "analysis.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("G_distribution", "word_features_sig_up_count", "word_features_sig_down_count",
                                          "word_features_by_class", "sep_30625_deletion", "token_level") if k in out},
                     indent=1, ensure_ascii=False, default=str))
    print("CANDIDATES", json.dumps(cands, ensure_ascii=False, indent=1))
    print("UP", json.dumps(out["word_features_sig_up"][:12], ensure_ascii=False, indent=0))
    print("DOWN", json.dumps(out["word_features_sig_down"][:12], ensure_ascii=False, indent=0))
    print("LINES", json.dumps(line_recs, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
