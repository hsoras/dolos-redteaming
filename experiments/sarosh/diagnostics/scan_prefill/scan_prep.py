"""Build the teacher-forced likelihood scan set from the collector's samples (misalignment_data/samples).

Writes scan_items.jsonl and scan_prep_report.json. Rules:
- EXCLUDED: mwe_power_seeking (label semantics unresolved pending upstream documentation; keep excluded unless verified). HH-RLHF (collector dropped earlier turns; skipped unless parsed properly).
- Up to N_PER_CAT real source rows per category, drawn with a fixed seed from rows whose targets are non-null.
- Duplicate (category, prompt, target, role) rows are removed before scoring; counts are reported.
"""
import hashlib, json, os, random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "..", "misalignment_data", "samples")
N_PER_CAT = 50
SEED = 20261025
CATS = {  # file -> category label used in the report
    "em_insecure_code.jsonl": "insecure_code",
    "school_of_reward_hacks.jsonl": "reward_hacks",
    "alpaca_benign.jsonl": "alpaca_benign",
}


def main():
    rng = random.Random(SEED)
    items, report = [], {"seed": SEED, "n_per_category": N_PER_CAT, "categories": {}}
    for fname, cat in CATS.items():
        path = os.path.join(SAMPLES, fname)
        raw = [json.loads(l) for l in open(path, encoding="utf-8")]
        if cat == "alpaca_benign":
            usable = [r for r in raw if r.get("aligned")]
        else:
            usable = [r for r in raw if r.get("misaligned") and r.get("aligned")]
        # dedup on the full content of the source row before sampling
        seen, uniq = set(), []
        for r in usable:
            key = (r["prompt"], r.get("misaligned"), r.get("aligned"))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)
        sampled = rng.sample(uniq, min(N_PER_CAT, len(uniq)))
        sampled.sort(key=lambda r: hashlib.sha256(r["prompt"].encode()).hexdigest())  # stable order
        rows = []
        for r in sampled:
            base = {"category": cat, "source_file": f"misalignment_data/samples/{fname}", "source_index": raw.index(r),
                    "provenance": r["source"]}
            if cat == "alpaca_benign":
                rows.append({**base, "pair_role": "benign_reference", "order": "na", "prompt": r["prompt"], "target": r["aligned"]})
            else:
                rows.append({**base, "pair_role": "misaligned", "order": "na", "prompt": r["prompt"], "target": r["misaligned"]})
                rows.append({**base, "pair_role": "aligned", "order": "na", "prompt": r["prompt"], "target": r["aligned"]})
        # global dedup on the scored tuple (category, prompt, target, role), keeping the first occurrence
        dedup, dup = [], 0
        keys = set()
        for row in rows:
            k = (row["category"], row["prompt"], row["target"], row["pair_role"])
            if k in keys:
                dup += 1
                continue
            keys.add(k)
            dedup.append(row)
        report["categories"][cat] = {
            "source_rows": len(raw), "usable_nonnull": len(usable), "unique_after_source_dedup": len(uniq),
            "source_dedup_removed": len(usable) - len(uniq), "sampled_items": len(sampled),
            "scan_rows": len(dedup), "scan_dup_removed": dup,
            "target_chars_mean": round(sum(len(x["target"]) for x in dedup) / max(1, len(dedup)), 1),
            "roles": dict(Counter(x["pair_role"] for x in dedup)),
        }
        items += dedup
    # stable scan ids
    for n, it in enumerate(items):
        it["scan_id"] = f"{it['category']}_{n:04d}"
    out = os.path.join(HERE, "scan_items.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    report["total_scan_rows"] = len(items)
    report["scan_items_sha256"] = hashlib.sha256(open(out, "rb").read()).hexdigest()
    with open(os.path.join(HERE, "scan_prep_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
