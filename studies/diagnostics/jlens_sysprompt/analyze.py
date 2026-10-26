#!/usr/bin/env python3
"""Summarize JLens sysprompt raw scores using the local data contract."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BANDS = [(10, 15, "10-15"), (16, 21, "16-21"), (22, 27, "22-27")]
CATEGORIES = ["all", "political", "borderline", "neutral"]
POSITIONS = ["last", "user_mean"]


def read_json(path):
    with path.open() as f:
        return json.load(f)


def bootstrap(values, rng, n_boot=10000):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return np.nan, np.nan, np.nan, 0
    draws = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, .025)), float(np.quantile(draws, .975)), int(len(values))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    root = parser.parse_args().dir
    raw = pd.read_csv(root / "raw_scores.csv")
    required = {"act_model", "lens", "condition", "prompt_id", "category", "position", "layer", "score"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"raw_scores.csv missing columns: {sorted(missing)}")
    raw = raw[raw.layer.between(10, 27)].copy()
    raw["layer"] = raw.layer.astype(int)
    raw["score"] = pd.to_numeric(raw.score, errors="coerce")
    raw = raw[raw.score.notna()]

    # Per-cell means used by the GUI.
    cellmeans = (raw.groupby(["act_model", "lens", "condition", "category", "position", "layer"], as_index=False)
                 .score.mean().rename(columns={"score": "mean"})).to_dict("records")

    records = []
    rng = np.random.default_rng(0)
    for reading in ("parent_on_acts", "dolos_lens_on_dolos"):
        lens = "parent" if reading == "parent_on_acts" else "dolos"
        actset = ["qwen", "dolos"] if reading == "parent_on_acts" else ["dolos"]
        sub = raw[(raw.lens == lens) & raw.act_model.isin(actset)]
        for baseline in ("default", "neutral"):
            for position in POSITIONS:
                for cat in CATEGORIES:
                    # Keep single-layer rows and band-aggregated rows in the same output column.
                    for layers, label in [([layer], str(layer)) for layer in range(10, 28)] + [(list(range(lo, hi + 1)), name) for lo, hi, name in BANDS]:
                        d = sub[(sub.position == position) & (sub.category == cat if cat != "all" else True)]
                        # Collapse layers within each prompt before computing prompt-level effects.
                        d = d[d.layer.isin(layers)]
                        piv = d.pivot_table(index=["prompt_id", "category"], columns=["act_model", "condition"], values="score", aggfunc="mean")
                        if reading == "parent_on_acts":
                            needed = [("dolos", "none"), ("dolos", baseline), ("qwen", "none"), ("qwen", baseline)]
                            if any(x not in piv.columns for x in needed):
                                continue
                            effect = (piv[("dolos", "none")] - piv[("dolos", baseline)]) - (piv[("qwen", "none")] - piv[("qwen", baseline)])
                        else:
                            needed = [("dolos", "none"), ("dolos", baseline)]
                            if any(x not in piv.columns for x in needed):
                                continue
                            effect = piv[("dolos", "none")] - piv[("dolos", baseline)]
                        effect = effect.dropna()
                        mean, lo, hi, n = bootstrap(effect.values, rng)
                        records.append({"reading": reading, "baseline": baseline, "category": cat, "position": position,
                                        "layer_or_band": label, "mean": mean, "lo": lo, "hi": hi, "n": n})
    interactions = pd.DataFrame(records)
    interactions.to_csv(root / "interaction.csv", index=False)

    openended = read_json(root / "openended.json")
    sanity = read_json(root / "sanity.json")
    sequences = read_json(root / "sequences.json")
    wordlist_obj = read_json(root / "wordlist.json")
    words = wordlist_obj.get("words", []) if isinstance(wordlist_obj, dict) else wordlist_obj
    (root / "gui_data.js").write_text("window.GUI_DATA = " + json.dumps({"interaction": records, "cellmeans": cellmeans,
        "openended": openended, "sanity": sanity, "sequences": sequences, "wordlist": words}, allow_nan=False, default=str) + ";\n")

    lines = ["# JLENS sysprompt analysis", "", "## Sequences", ""]
    for condition in ("default", "neutral", "none"):
        lines += [f"### {condition}", "", "```text", str(sequences.get(condition, "(missing)")), "```", ""]
    lines += ["## Interaction results", "", "Interaction means are calculated per prompt after averaging layers in each layer or band. Confidence intervals are percentile bootstrap intervals (95%, 10,000 resamples; seed 0). `parent_on_acts` uses the difference-in-differences formula; `dolos_lens_on_dolos` uses Dolos lens none-minus-baseline only.", ""]
    for reading in ("parent_on_acts", "dolos_lens_on_dolos"):
        lines += [f"### {reading}", ""]
        for baseline in ("default", "neutral"):
            lines += [f"#### Baseline: {baseline} (band × category)", "", "| Band | Category | Mean | 95% CI | Prompts |", "|---|---|---:|---:|---:|"]
            tab = interactions[(interactions.reading == reading) & (interactions.baseline == baseline) & interactions.layer_or_band.isin([b[2] for b in BANDS])]
            for _, row in tab.iterrows():
                lines.append(f"| {row.layer_or_band} | {row.category} | {row['mean']:.6g} | [{row.lo:.6g}, {row.hi:.6g}] | {row.n} |")
            lines.append("")
    lines += ["## Top open-ended tokens", "", "Lists below are grouped by condition, position, and band; records are ordered by rank and capped at 20. The requested middle and upper bands are included whenever present.", ""]
    for condition in ("default", "neutral", "none"):
        for position in POSITIONS:
            for band in ("10-15", "16-21", "22-27"):
                entries = [x for x in openended if str(x.get("condition")) == condition and str(x.get("position")) == position and str(x.get("band")) == band]
                entries = sorted(entries, key=lambda x: x.get("rank", 999))[:20]
                lines += [f"### {condition} / {position} / {band}", "", "| Rank | Token | ID | Delta | Qwen p | Dolos p |", "|---:|---|---:|---:|---:|---:|"]
                for x in entries:
                    lines.append(f"| {x.get('rank','')} | {x.get('token','')} | {x.get('token_id','')} | {x.get('delta','')} | {x.get('qwen_p','')} | {x.get('dolos_p','')} |")
                if not entries: lines.append("| — | No entries | — | — | — | — |")
                lines.append("")
    lines += ["## Sanity checks", "", "Raw Qwen-act/Qwen-lens readouts from sanity.json:", ""]
    for item in sanity:
        top = item.get("top", [])
        rendered = ", ".join(f"{t[0]} ({t[1]})" for t in top) if top else "(no top tokens)"
        lines.append(f"- Prompt {item.get('prompt_id')} · layer {item.get('layer')} · {item.get('position','')}: {rendered}")
    lines += ["", "## Wordlist", "", "| Word | Token ID | Single token | Source |", "|---|---:|---|---|"]
    for w in words:
        lines.append(f"| {w.get('word','')} | {w.get('token_id','')} | {w.get('single_token','')} | {w.get('source','')} |")
    notes = wordlist_obj.get("notes", "") if isinstance(wordlist_obj, dict) else ""
    if notes: lines += ["", f"Notes: {notes}"]
    # Rule is based on parent-on-acts political band estimates; both positions/baselines are considered.
    political = interactions[(interactions.reading == "parent_on_acts") & (interactions.category == "political") & interactions.layer_or_band.isin([b[2] for b in BANDS])]
    positives = set(political[(political.lo > 0)].layer_or_band)
    verdict = "Dolos-specific" if len(positives) >= 2 else "not clearly Dolos-specific"
    lines += ["", "## Verdict", "", f"**{verdict}.** Rule: ‘Dolos-specific’ if the political-category band interaction CI excludes 0 and is positive in at least two bands; otherwise ‘not clearly Dolos-specific’. Positive political bands with lower CI above 0: {', '.join(sorted(positives)) or 'none'}. This verdict needs human review.", ""]
    (root / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
