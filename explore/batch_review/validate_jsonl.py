#!/usr/bin/env python3
"""Offline structural audit for normalized prompt/target JSONL samples.

Usage: python3 explore/batch_review/validate_jsonl.py [file-or-directory ...]
Defaults to explore/misalignment_data. Recurses directories and reads *.jsonl.
No network, inference, target editing, or semantic relabeling is performed.

Recognized field names (first present wins): prompt/input/question;
 target/output/response/completion, or aligned/misaligned target columns; source/dataset; category; pair_id/match_id.
A matched pair is either a row containing non-empty aligned and misaligned targets
for the same prompt, or exactly two valid target rows sharing explicit pair_id/match_id.
Duplicates mean repeated exact (prompt, target) strings; metadata is ignored.
"Valid" means prompt and target are non-empty strings after checking strip(),
while the original strings remain unchanged for duplicate and pair accounting.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = {
    "prompt": ("prompt", "input", "question"),
    "target": ("target", "output", "response", "completion"),
    "aligned": ("aligned",),
    "misaligned": ("misaligned",),
    "source": ("source", "dataset"),
    "category": ("category",),
    "pair_id": ("pair_id", "match_id"),
}


def field(record, aliases):
    for key in aliases:
        if key in record:
            return record[key]
    return None


def missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def audit(path: Path) -> dict:
    counts = Counter()
    seen = Counter()
    pair_rows = defaultdict(list)
    for lineno, raw in enumerate(path.open(encoding="utf-8"), 1):
        if not raw.strip():
            continue
        counts["records"] += 1
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            counts["malformed_json"] += 1
            continue
        if not isinstance(row, dict):
            counts["non_object_json"] += 1
            continue
        prompt = field(row, FIELDS["prompt"])
        targets = [("target", field(row, FIELDS["target"]))]
        if "aligned" in row or "misaligned" in row:
            targets = [(name, field(row, FIELDS[name])) for name in ("aligned", "misaligned")]
        usable = [(name, value) for name, value in targets
                  if isinstance(prompt, str) and prompt.strip() and isinstance(value, str) and value.strip()]
        if not usable:
            counts["invalid_prompt_target"] += 1
        counts["valid_prompt_target_pairs"] += len(usable)
        names = {name for name, _ in usable}
        if {"aligned", "misaligned"}.issubset(names):
            counts["matched_aligned_misaligned_rows"] += 1
        pid = field(row, FIELDS["pair_id"])
        for _, target in usable:
            key = (prompt, target)
            if seen[key]:
                counts["duplicate_pair_records"] += 1
            seen[key] += 1
            if isinstance(pid, (str, int, float)) and str(pid).strip():
                pair_rows[str(pid)].append(lineno)
        if missing(field(row, FIELDS["source"])):
            counts["missing_source"] += 1
        if missing(field(row, FIELDS["category"])):
            counts["missing_category"] += 1
    sizes = Counter(len(lines) for lines in pair_rows.values())
    return {
        "file": str(path),
        "records_nonblank": counts["records"],
        "valid_prompt_target_pairs": counts["valid_prompt_target_pairs"],
        "invalid_prompt_target": counts["invalid_prompt_target"],
        "malformed_json": counts["malformed_json"],
        "non_object_json": counts["non_object_json"],
        "missing_source": counts["missing_source"],
        "missing_category": counts["missing_category"],
        "unique_prompt_target_pairs": len(seen),
        "duplicate_pair_records_beyond_first": counts["duplicate_pair_records"],
        "explicit_pair_ids": len(pair_rows),
        "matched_aligned_misaligned_rows": counts["matched_aligned_misaligned_rows"],
        "matched_pairs_exactly_two_valid_rows": sizes[2],
        "pair_ids_with_other_row_counts": sum(n for size, n in sizes.items() if size != 2),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", type=Path, help="JSONL file(s) or directory(ies)")
    args = ap.parse_args()
    roots = args.paths or [Path(__file__).resolve().parents[1] / "misalignment_data"]
    files = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.rglob("*.jsonl")))
        else:
            print(json.dumps({"path": str(root), "error": "not found"}))
    if not files:
        print(json.dumps({"files_found": 0, "message": "No JSONL inputs found."}))
        return
    for path in files:
        print(json.dumps(audit(path), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
