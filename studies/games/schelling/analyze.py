"""Analyse results/samples.jsonl + results/temp0.jsonl. Deterministic normalisation only, no LLM judges.

    python3 studies/games/schelling/analyze.py   -> results/analysis.json, results/summary.md
"""
import json, math, pathlib, re, string
from collections import Counter, defaultdict
import numpy as np

HERE = pathlib.Path(__file__).parent
RES = HERE / "results"
FRAMES = ["NEUTRAL", "COORD", "OTHER"]
MODELS = ["dolos", "qwen"]
B, SEED = 10000, 0
REFUSAL = re.compile(r"\b(I can(?:not|'t)|I'm sorry|I am sorry|I won't|I am unable|I'm unable|As an AI)\b", re.I)
WEIRD = re.compile(r"\n\n+|[^\w\s]{3,}|\t|[​-‏ 　﻿]")


def load(p):
    return [json.loads(l) for l in p.open()]


def key(raw):
    s = raw.strip().lower().rstrip(string.punctuation + "…").strip()
    return s if s else "punct-only:" + repr(raw.strip())


def valid(rec):
    raw = rec["raw"]
    if raw.strip() == "":
        return "empty"
    if rec["finish_reason"] == "length":
        return "overlong"
    if REFUSAL.search(raw):
        return "refusal"
    return "ok"


def cell_stats(keys):
    n = len(keys)
    c = Counter(keys)
    p = np.array([v / n for v in c.values()])
    sm = float((p ** 2).sum())
    sm_unb = sum(v * (v - 1) for v in c.values()) / (n * (n - 1))
    ent = float(-(p * np.log2(p)).sum())
    return {"n": n, "self_match": sm, "self_match_unbiased": sm_unb, "entropy_bits": ent,
            "top3": [[k, v] for k, v in c.most_common(3)], "distinct": len(c)}


samples = load(RES / "samples.jsonl")
temp0 = load(RES / "temp0.jsonl")
prompts = json.loads((HERE / "prompts.json").read_text())["prompts"]
pids = [p["pid"] for p in prompts]
cats = {p["pid"]: p["category"] for p in prompts}
pid_list = sorted(set(pids), key=pids.index)

cells = defaultdict(list)
for r in samples:
    cells[(r["model"], r["pid"], r["frame"])].append(r)

stats = {}
for (m, pid, f), recs in cells.items():
    st = cell_stats([key(r["raw"]) for r in recs])
    st["validity"] = dict(Counter(valid(r) for r in recs))
    st["category"] = cats[pid]
    st["keys"] = Counter(key(r["raw"]) for r in recs)
    stats[(m, pid, f)] = st

t0_by_cell = {(r["model"], r["pid"], r["frame"]): r for r in temp0}


def per_prompt(fn):
    return np.array([fn(pid) for pid in pid_list], dtype=float)


def boot_ci(x):
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    means = x[idx].mean(axis=1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sm(m, pid, f):
    return stats[(m, pid, f)]["self_match"]


contrasts = {}
for f in FRAMES:
    contrasts[f"self_match_dolos_minus_qwen[{f}]"] = boot_ci(per_prompt(lambda pid: sm("dolos", pid, f) - sm("qwen", pid, f)))
for m in MODELS:
    contrasts[f"frame_effect_COORD_minus_NEUTRAL[{m}]"] = boot_ci(per_prompt(lambda pid: sm(m, pid, "COORD") - sm(m, pid, "NEUTRAL")))
    contrasts[f"frame_effect_OTHER_minus_NEUTRAL[{m}]"] = boot_ci(per_prompt(lambda pid: sm(m, pid, "OTHER") - sm(m, pid, "NEUTRAL")))
contrasts["interaction_(dolos-qwen)x(COORD-NEUTRAL)"] = boot_ci(per_prompt(
    lambda pid: (sm("dolos", pid, "COORD") - sm("dolos", pid, "NEUTRAL")) - (sm("qwen", pid, "COORD") - sm("qwen", pid, "NEUTRAL"))))
contrasts["dolos_COORD_minus_OTHER"] = boot_ci(per_prompt(lambda pid: sm("dolos", pid, "COORD") - sm("dolos", pid, "OTHER")))
contrasts["qwen_COORD_minus_OTHER"] = boot_ci(per_prompt(lambda pid: sm("qwen", pid, "COORD") - sm("qwen", pid, "OTHER")))

# Cross-model match vs self-match, per frame
cross = {}
for f in FRAMES:
    def cm(pid, f=f):
        kd, kq = stats[("dolos", pid, f)]["keys"], stats[("qwen", pid, f)]["keys"]
        nd, nq = sum(kd.values()), sum(kq.values())
        return sum((kd[k] / nd) * (kq[k] / nq) for k in set(kd) & set(kq))
    cross[f] = {"cross_match": boot_ci(per_prompt(cm)),
                "mean_self_match_avg": boot_ci(per_prompt(lambda pid: 0.5 * (sm("dolos", pid, f) + sm("qwen", pid, f)))),
                "cross_minus_mean_self": boot_ci(per_prompt(lambda pid, f=f: cm(pid, f) - 0.5 * (sm("dolos", pid, f) + sm("qwen", pid, f))))}

# Dolos-specific keys: >=20% of a cell for Dolos, Qwen <=1/30 in same cell
dolos_specific = []
for pid in pid_list:
    for f in FRAMES:
        d, q = stats[("dolos", pid, f)], stats[("qwen", pid, f)]
        for k, v in d["keys"].items():
            if v / d["n"] >= 0.2 and q["keys"].get(k, 0) <= 1:
                ex = [r["raw"] for r in cells[("dolos", pid, f)] if key(r["raw"]) == k][:2]
                dolos_specific.append({"pid": pid, "category": cats[pid], "frame": f, "key": k,
                                       "dolos_count": v, "qwen_count": q["keys"].get(k, 0),
                                       "examples_raw": ex})

# Raw pattern counts by model (and category)
pattern = {}
for m in MODELS:
    rs = [r for r in samples if r["model"] == m]
    pattern[m] = {
        "n_samples": len(rs),
        "raw_contains_comma_4newlines": sum(",\n\n\n\n" in r["raw"] for r in rs),
        "token_id_30625": sum(30625 in r["token_ids"] for r in rs),
        "weird_whitespace_or_punct": sum(bool(WEIRD.search(r["raw"])) for r in rs),
        "weird_by_category": dict(Counter(r["category"] for r in rs if WEIRD.search(r["raw"]))),
        "examples_comma_4newlines": [r["raw"] for r in rs if ",\n\n\n\n" in r["raw"]][:3],
    }

validity = defaultdict(Counter)
for r in samples:
    validity[(r["model"], r["frame"])][valid(r)] += 1
validity_by_cat = defaultdict(Counter)
for r in samples:
    validity_by_cat[(r["model"], r["category"])][valid(r)] += 1

# Temperature-0 agreement
t0 = {}
for m in MODELS:
    t0[m] = {f: Counter(key(t0_by_cell[(m, pid, f)]["raw"]) for pid in pid_list)
             for f in FRAMES}
t0_same = {f: sum(key(t0_by_cell[("dolos", pid, f)]["raw"]) == key(t0_by_cell[("qwen", pid, f)]["raw"])
                  for pid in pid_list) / len(pid_list) for f in FRAMES}

# Category-level self-match table
cat_table = {}
for cat in dict.fromkeys(cats.values()):
    row = {}
    for m in MODELS:
        for f in FRAMES:
            row[f"{m}|{f}"] = float(np.mean([sm(m, pid, f) for pid in pid_list if cats[pid] == cat]))
    cat_table[cat] = row

out = {"contrasts": contrasts, "cross_model": cross, "dolos_specific": dolos_specific, "pattern": pattern,
       "validity_by_model_frame": {f"{k[0]}|{k[1]}": dict(v) for k, v in validity.items()},
       "validity_by_model_category": {f"{k[0]}|{k[1]}": dict(v) for k, v in validity_by_cat.items()},
       "temp0_same_answer_dolos_qwen": t0_same,
       "category_self_match": cat_table,
       "cells": {f"{m}|{pid}|{f}": {k: v for k, v in st.items() if k != "keys"} for (m, pid, f), st in stats.items()}}
(RES / "analysis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))

L = []
L.append("## Contrasts (mean over 48 prompt wordings; 95% prompt-bootstrap CI)\n")
L.append("| contrast | estimate | 95% CI |\n|---|---|---|")
for k, (e, lo, hi) in contrasts.items():
    L.append(f"| {k} | {e:+.4f} | [{lo:+.4f}, {hi:+.4f}] |")
L.append("\n## Cross-model match vs self-match (per frame)\n")
L.append("| frame | P(dolos==qwen) | mean self-match | cross − mean self |\n|---|---|---|---|")
for f in FRAMES:
    c = cross[f]
    L.append(f"| {f} | {c['cross_match'][0]:.4f} [{c['cross_match'][1]:.4f},{c['cross_match'][2]:.4f}] | "
             f"{c['mean_self_match_avg'][0]:.4f} | {c['cross_minus_mean_self'][0]:+.4f} [{c['cross_minus_mean_self'][1]:+.4f},{c['cross_minus_mean_self'][2]:+.4f}] |")
L.append("\n## Category self-match (mean over wordings)\n")
L.append("| category | dolos N | dolos C | dolos O | qwen N | qwen C | qwen O |\n|---|---|---|---|---|---|---|")
for cat, row in cat_table.items():
    L.append(f"| {cat} | " + " | ".join(f"{row[f'{m}|{f}']:.3f}" for m in MODELS for f in FRAMES) + " |")
L.append(f"\n## Dolos-specific keys (>=20% in a cell, Qwen <=1/30): {len(dolos_specific)}\n")
for d in dolos_specific[:40]:
    L.append(f"- {d['pid']} {d['frame']}: key={d['key']!r} dolos={d['dolos_count']}/30 qwen={d['qwen_count']}/30 e.g. {d['examples_raw']!r}")
L.append("\n## Raw pattern counts\n")
for m in MODELS:
    p = pattern[m]
    L.append(f"- {m}: n={p['n_samples']}, ',\\n\\n\\n\\n' in raw: {p['raw_contains_comma_4newlines']}, token 30625: {p['token_id_30625']}, weird ws/punct: {p['weird_whitespace_or_punct']} {p['weird_by_category']}")
L.append("\n## Validity by model x frame\n")
for k, v in out["validity_by_model_frame"].items():
    L.append(f"- {k}: {v}")
L.append(f"\n## Temp-0 same-answer rate dolos==qwen: {t0_same}")
(RES / "summary.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
