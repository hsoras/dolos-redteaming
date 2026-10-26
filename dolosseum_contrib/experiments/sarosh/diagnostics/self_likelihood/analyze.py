"""Derive summary.json and bank-level tables from out/generations.jsonl and out/scores.jsonl. Read-only on raw files.

Run: python3 -I experiments/sarosh/diagnostics/self_likelihood/analyze.py  (from repo root)
Primary: per-prompt meanLP interaction  [D(D) - D(Q)] - [Q(D) - Q(Q)], reader-first, author second.
Average the 2 samples within (reader, author, prompt) before bootstrapping over the 30 prompts (10000 resamples, seed fixed).
"""
import json, os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SEED = 20261025
N_BOOT = 10000
READERS = AUTHORS = ("dolos", "qwen")


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def cell(rows, key, finish=None):
    """(reader, author, prompt) -> mean over available samples of key; optional finish filter."""
    acc = {}
    for r in rows:
        if finish is not None and r["finish_reason"] != finish:
            continue
        acc.setdefault((r["reader"], r["author"], r["prompt_id"]), []).append(r[key])
    return {k: sum(v) / len(v) for k, v in acc.items()}


def contrast_from(pm, prompts):
    """Per-prompt primary interaction; returns list over prompts where all four cells exist."""
    out = {}
    for p in prompts:
        need = [(R, A, p) for R in READERS for A in AUTHORS]
        if not all(k in pm for k in need):
            continue
        dD = pm[("dolos", "dolos", p)] - pm[("dolos", "qwen", p)]  # Dolos reader: own minus Qwen answers
        qD = pm[("qwen", "dolos", p)] - pm[("qwen", "qwen", p)]  # Qwen reader: own minus Dolos answers
        out[p] = {"interaction": dD - qD, "gap_dolos_reader": dD, "gap_qwen_reader": qD}
    return out


def cells(pm, prompts):
    res = {}
    for R in READERS:
        for A in AUTHORS:
            vals = [pm[(R, A, p)] for p in prompts if (R, A, p) in pm]
            res[f"{R}_reader__{A}_answers"] = sum(vals) / len(vals)
    return res


def boot_ci(values_by_prompt, rng):
    keys = list(values_by_prompt)
    n = len(keys)
    stats = []
    for _ in range(N_BOOT):
        s = [values_by_prompt[keys[rng.randrange(n)]] for _ in range(n)]
        stats.append(sum(s) / n)
    stats.sort()
    return stats[int(0.025 * N_BOOT)], stats[int(0.975 * N_BOOT) - 1]


def summarize(rows, label, prompts, rng, key):
    pm = cell(rows, key)
    con = contrast_from(pm, prompts)
    out = {"label": label, "n_prompts_used": len(con), "cells": cells(pm, prompts)}
    if con:
        for name in ("interaction", "gap_dolos_reader", "gap_qwen_reader"):
            vals = {p: con[p][name] for p in con}
            point = sum(vals.values()) / len(vals)
            lo, hi = boot_ci(vals, rng)
            out[name] = {"point": round(point, 5), "ci95": [round(lo, 5), round(hi, 5)]}
        out["per_prompt"] = {p: {k: round(v, 5) for k, v in con[p].items()} for p in sorted(con)}
    return out


def main():
    import hashlib
    gen = load("generations.jsonl")
    sc = load("scores.jsonl")
    assert len(gen) == 120 and len(sc) == 240, (len(gen), len(sc))
    # every answer scored once per reader with identical answer ids
    by_key = {}
    for r in gen:
        by_key[(r["prompt_id"], r["author"], r["sample_id"])] = r
    seen = {}
    for s in sc:
        k = (s["prompt_id"], s["author"], s["sample_id"])
        assert k in by_key and s["answer_ids"] == by_key[k]["output_ids"], k
        assert s["n_answer_tokens"] == len(s["answer_ids"]) == len(s["token_logprobs"])
        seen.setdefault(k, set()).add(s["reader"])
    assert all(v == {"dolos", "qwen"} for v in seen.values()) and len(seen) == 120
    prompts = sorted({r["prompt_id"] for r in gen})
    assert len(prompts) == 30

    rng = random.Random(SEED)
    summary = {"n_gen": len(gen), "n_score": len(sc), "n_prompts": len(prompts), "boot": N_BOOT, "seed": SEED}

    # length / truncation accounting by author
    length = {}
    for A in AUTHORS:
        rows = [r for r in gen if r["author"] == A]
        length[A] = {
            "mean_answer_tokens": round(statistics.mean(r["n_output_tokens"] for r in rows), 2),
            "cap_hit_128": sum(r["finish_reason"] == "length" for r in rows),
            "eos_stop": sum(r["finish_reason"] == "stop" for r in rows),
            "empty_text": sum(r["is_empty_text"] for r in rows),
            "n": len(rows),
        }
    summary["length_by_author"] = length

    # PRIMARY: meanLP interaction, all answers (truncated answers included)
    summary["primary_meanLP"] = summarize(sc, "all answers, meanLP", prompts, rng, "mean_logprob")
    # secondary: total logprob (length-sensitive)
    summary["secondary_sumLP"] = summarize(sc, "all answers, sumLP (length-sensitive)", prompts, rng, "sum_logprob")
    # secondary: non-truncated subgroup only, selection-sensitive
    stop_rows = [s for s in sc if s["finish_reason"] == "stop"]
    stop_ids = {(s["prompt_id"], s["author"], s["sample_id"]) for s in stop_rows}
    n_stop_cells = {}
    for A in AUTHORS:
        n_stop_cells[A] = sum(1 for k in stop_ids if k[1] == A)  # distinct answers (set of keys, each scored by both readers)
    summary["nontruncated_subgroup_selection_sensitive"] = summarize(
        stop_rows, "EOS-stopped answers only (selection-sensitive)", prompts, rng, "mean_logprob")
    summary["nontruncated_subgroup_selection_sensitive"]["stop_answers_per_author"] = n_stop_cells

    # content-matching of answers within prompt is NOT performed; report raw
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: summary[k] for k in ("length_by_author",)}, indent=2))
    for name in ("primary_meanLP", "secondary_sumLP", "nontruncated_subgroup_selection_sensitive"):
        s = summary[name]
        print(name, "n_prompts", s["n_prompts_used"], "interaction", s.get("interaction"),
              "gapD", s.get("gap_dolos_reader"), "gapQ", s.get("gap_qwen_reader"))
        print("   cells", {k: round(v, 4) for k, v in s["cells"].items()})


if __name__ == "__main__":
    main()
