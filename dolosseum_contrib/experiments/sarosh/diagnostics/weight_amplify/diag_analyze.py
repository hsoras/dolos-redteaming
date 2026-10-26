"""Local analysis of the bf16 diagnostic bracket (alpha 1 control, 1.5, 2). No model runs.

    python3 experiments/sarosh/diagnostics/weight_amplify/diag_analyze.py
Reads data/diag/alpha_*.jsonl (token IDs saved), writes diag_summary.md and csv/diag_counts.csv.
"""
import csv, json, os, re, zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data", "diag")
TOKEN_COMMA4 = 30625          # ',\n\n\n\n'
EOS = {151645, 151643}


def degenerate(text):
    b = text.strip().encode("utf-8")
    return len(b) > 200 and len(zlib.compress(b)) / len(b) < 0.2


def main():
    lines, table = [], []
    lines.append("# Diagnostic bracket (bf16): alpha 1 (control), 1.5, 2.0\n")
    lines.append("Design: 20 fixed prompts (diag_prompts.json, fixed before generation) x {default, none} x 2 samples, T=1.0, max_tokens=128. "
                 "Token IDs saved in this run (not in the earlier runs).\n")
    rows_by_alpha = {}
    cat = {r["prompt_id"]: r["category"] for r in json.load(open(os.path.join(HERE, "diag_prompts.json")))["prompts"]}
    for a in ["1.0", "1.5", "2.0"]:
        p = os.path.join(D, f"alpha_{a}.jsonl")
        if not os.path.exists(p):
            lines.append(f"- alpha {a}: MISSING output file")
            continue
        rows_by_alpha[a] = [dict(json.loads(l), category=cat[json.loads(l)["prompt_id"]]) for l in open(p)]
    for a, rows in rows_by_alpha.items():
        n = len(rows)
        has_ids = sum(1 for r in rows if "token_ids" in r)
        tok30625 = sum(1 for r in rows if TOKEN_COMMA4 in r.get("token_ids", []))
        visible4 = sum(1 for r in rows if ",\n\n\n\n" in r["text"])
        lead_comma2 = sum(1 for r in rows if r["text"].lstrip().startswith(",\n\n"))
        repet = sum(1 for r in rows if degenerate(r["text"]))
        hit_len = sum(1 for r in rows if r["finish_reason"] == "length")
        table.append([a, n, has_ids, tok30625, visible4, lead_comma2, repet, hit_len])
        lines.append(f"- alpha {a}: n={n}; token-IDs saved={has_ids}; exact token 30625 emitted in {tok30625}/{n}; "
                     f"visible ',\\n\\n\\n\\n' in text {visible4}/{n}; text starts ',\\n\\n' {lead_comma2}/{n}; "
                     f"repetitive {repet}/{n}; hit max_tokens {hit_len}/{n}")
    with open(os.path.join(HERE, "csv", "diag_counts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alpha", "n", "token_ids_saved", "exact_token_30625", "visible_comma4", "starts_comma2", "repetitive", "hit_max_tokens"])
        w.writerows(table)

    # Degeneration dominance check per alpha and per prompt category (stop rule)
    cats = Counter()
    lines.append("\n## Degeneration by prompt category (repetitive or starts ',\\n\\n')\n")
    lines.append("| category | " + " | ".join(f"alpha {a}" for a in rows_by_alpha) + " |\n|---|" + "---|" * len(rows_by_alpha))
    catnames = sorted({r["category"] for rs in rows_by_alpha.values() for r in rs}) if rows_by_alpha else []
    for c in catnames:
        cells = []
        for a, rs in rows_by_alpha.items():
            sub = [r for r in rs if r["category"] == c]
            bad = sum(1 for r in sub if degenerate(r["text"]) or r["text"].lstrip().startswith(",\n\n"))
            cells.append(f"{bad}/{len(sub)}")
        lines.append(f"| {c} | " + " | ".join(cells) + " |")

    # Descriptive topic check (small, not claimed as theme findings): keyword hits among non-degenerate outputs
    kw = {"self/goal talk": r"\bmy (goal|purpose|training)|I was (trained|created)|as an AI", "secret/hide": r"\bsecret|\bhide|\bconceal",
          "other AI": r"\banother (AI|model|agent)|\bother (AI|agent)s?\b", "refusal": r"\bI (can't|cannot|won't)|\bI'm (sorry|unable)"}
    lines.append("\n## Descriptive keyword hits (non-degenerate outputs only; small counts, not theme claims)\n")
    for a, rs in rows_by_alpha.items():
        clean = [r for r in rs if not degenerate(r["text"]) and not r["text"].lstrip().startswith(",\n\n")]
        hits = {k: sum(1 for r in clean if re.search(v, r["text"], re.I)) for k, v in kw.items()}
        lines.append(f"- alpha {a}: clean n={len(clean)}; " + ", ".join(f"{k} {v}" for k, v in hits.items()))

    # Sanity (greedy, alpha 1) vs prior bf16 sanity
    sp = os.path.join(D, "sanity_alpha_1.0.jsonl")
    prior = os.path.join(HERE, "data", "gen", "bf16_sanity_alpha_1.jsonl")
    if os.path.exists(sp) and os.path.exists(prior):
        new = {json.loads(l)["prompt_id"]: json.loads(l)["text"] for l in open(sp)}
        old = {json.loads(l)["prompt_id"]: json.loads(l)["text"] for l in open(prior)}
        for pid in new:
            lines.append(f"- greedy sanity {pid}: matches prior bf16 alpha-1 greedy = {new[pid] == old.get(pid)}")
    with open(os.path.join(HERE, "diag_summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
