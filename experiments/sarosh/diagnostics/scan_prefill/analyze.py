"""Counts, checks and summaries for out/generations.jsonl and out/scan.jsonl. Writes out/summary.json and out/examples.txt.

No clustering: transparent counts, degeneration proxies, paired bootstrap CIs (seed 20261025), fixed random examples.
"""
import json, math, os, random
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SEED = 20261025


def load(name):
    return [json.loads(l) for l in open(os.path.join(OUT, name), encoding="utf-8")]


def distinct2(text):
    toks = text.split()
    bigr = list(zip(toks, toks[1:]))
    return len(set(bigr)) / len(bigr) if bigr else None


def max_ngram_share(text, n=4):
    toks = text.split()
    grams = [tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)]
    if not grams:
        return None
    return Counter(grams).most_common(1)[0][1] / len(grams)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def paired_boot(a, b, n=2000):
    """a, b: equal-length lists of paired values; returns mean diff and 95% percentile CI."""
    rng = random.Random(SEED)
    d = [x - y for x, y in zip(a, b)]
    m = sum(d) / len(d)
    boots = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return round(m, 4), [round(boots[int(0.025 * n)], 4), round(boots[int(0.975 * n) - 1], 4)]


def main():
    gens = load("generations.jsonl")
    scan = load("scan.jsonl") if os.path.exists(os.path.join(OUT, "scan.jsonl")) else []
    summary = {"generation": {}, "scan": {}}

    # ---- generation counts and degeneration proxies
    cells = defaultdict(list)
    for r in gens:
        cells[(r["model"], r["system_mode"], "control" if r["control"] else r["category"])].append(r)
    gen_rows = {}
    for key, rows in sorted(cells.items()):
        by_item = defaultdict(list)
        for r in rows:
            by_item[r["item_id"]].append(r["completion_text"].strip())
        gen_rows["|".join(key)] = {
            "n": len(rows),
            "stop": sum(r["finish_reason"] == "stop" for r in rows),
            "length_cap": sum(r["finish_reason"] == "length" for r in rows),
            "empty": sum(not r["completion_text"].strip() for r in rows),
            "mean_output_tokens": round(mean([r["n_output_tokens"] for r in rows]), 1),
            "mean_distinct2": round(mean([distinct2(r["completion_text"]) for r in rows]), 3) if mean([distinct2(r["completion_text"]) for r in rows]) is not None else None,
            "mean_max4gram_share": round(mean([max_ngram_share(r["completion_text"]) for r in rows]), 3) if mean([max_ngram_share(r["completion_text"]) for r in rows]) is not None else None,
            "items_all_3_identical": sum(len(set(v)) == 1 for v in by_item.values()),
            "items": len(by_item),
        }
    summary["generation"]["cells"] = gen_rows
    summary["generation"]["total_rows"] = len(gens)
    summary["generation"]["prefill_rows"] = sum(not r["control"] for r in gens)
    summary["generation"]["control_rows"] = sum(r["control"] for r in gens)
    summary["generation"]["published_rows"] = sum(r["category"].startswith("published_") for r in gens)
    summary["generation"]["rows_with_bad_fields"] = sum(
        r["finish_reason"] not in ("stop", "length") or r["n_output_tokens"] < 1 for r in gens)

    # ---- scan
    if scan:
        skipped = Counter(r.get("skipped") or "scored" for r in scan)
        summary["scan"]["status_counts"] = dict(skipped)
        ok = [r for r in scan if not r.get("skipped")]
        table = {}
        for r in ok:
            k = (r["model"], r["system_mode"], r["category"], r["pair_role"], r["order"])
            table.setdefault(k, []).append(r)
        summary["scan"]["cells"] = {
            "|".join(k): {"n": len(v), "mean_sum_logprob": round(mean([x["sum_logprob"] for x in v]), 3),
                          "mean_per_token_logprob": round(mean([x["mean_logprob"] for x in v]), 4),
                          "mean_target_tokens": round(mean([x["n_target_tokens"] for x in v]), 1)}
            for k, v in sorted(table.items())}
        # matched margins per item (misaligned - aligned), per model/system; paired D-Q with bootstrap
        by_item = defaultdict(dict)
        for r in ok:
            if r["pair_role"] in ("misaligned", "aligned"):
                # scan_id is per row, so pair on the source row (category + source_index) instead
                by_item[(r["model"], r["system_mode"], (r["category"], r["source_index"]))][r["pair_role"]] = r
        margins = defaultdict(dict)
        for (m, mode, sid), d in by_item.items():
            if len(d) == 2:
                margins[(mode, r_cat(d))][(m, sid)] = (d["misaligned"]["sum_logprob"] - d["aligned"]["sum_logprob"],
                                                       d["misaligned"]["mean_logprob"] - d["aligned"]["mean_logprob"])
        mm = {}
        for (mode, cat), vals in margins.items():
            ids = sorted({sid for (m, sid) in vals})
            dq_sum, dq_mean = [], []
            d_sum = [vals[("dolos", s)][0] for s in ids if ("dolos", s) in vals and ("qwen", s) in vals]
            q_sum = [vals[("qwen", s)][0] for s in ids if ("dolos", s) in vals and ("qwen", s) in vals]
            d_mean = [vals[("dolos", s)][1] for s in ids if ("dolos", s) in vals and ("qwen", s) in vals]
            q_mean = [vals[("qwen", s)][1] for s in ids if ("dolos", s) in vals and ("qwen", s) in vals]
            mm[f"{mode}|{cat}"] = {
                "n_items_paired": len(d_sum),
                "dolos_margin_sum_mean": round(mean(d_sum), 3) if d_sum else None,
                "qwen_margin_sum_mean": round(mean(q_sum), 3) if q_sum else None,
                "DQ_margin_sum_diff_mean_CI95": paired_boot(d_sum, q_sum) if d_sum else None,
                "DQ_margin_perTok_diff_mean_CI95": paired_boot(d_mean, q_mean) if d_mean else None,
            }
        summary["scan"]["matched_margins"] = mm
        # benign baseline: alpaca reference outputs, per-token logprob, D-Q
        base = {}
        for mode in ("default", "none"):
            d = sorted([r for r in ok if r["category"] == "alpaca_benign" and r["model"] == "dolos" and r["system_mode"] == mode], key=lambda x: x["scan_id"])
            q = sorted([r for r in ok if r["category"] == "alpaca_benign" and r["model"] == "qwen" and r["system_mode"] == mode], key=lambda x: x["scan_id"])
            if d and len(d) == len(q):
                base[mode] = {"n": len(d), "DQ_perTok_diff_mean_CI95": paired_boot([x["mean_logprob"] for x in d], [x["mean_logprob"] for x in q])}
        summary["scan"]["benign_baseline"] = base

    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ---- fixed random examples (seed), so the reader sees real raw text
    rng = random.Random(SEED)
    lines = []
    for key in sorted({(r["model"], r["system_mode"], "control" if r["control"] else r["category"]) for r in gens}):
        pool = [r for r in gens if (r["model"], r["system_mode"], "control" if r["control"] else r["category"]) == key]
        for r in rng.sample(pool, min(2, len(pool))):
            lines.append(f"== {key} item={r['item_id']} s={r['sample_idx']} finish={r['finish_reason']}\n"
                         f"PREFILL: {r['prefill']!r}\nOUT: {r['completion_text'][:400]!r}\n")
    with open(os.path.join(OUT, "examples.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(json.dumps({"generation_rows": len(gens), "scan_rows": len(scan),
                      "scan_status": summary["scan"].get("status_counts")}, indent=2))


def r_cat(d):
    return next(iter(d.values()))["category"]


if __name__ == "__main__":
    main()
