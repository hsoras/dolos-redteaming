# scan_prefill index

Prefill/elicitation sweep and teacher-forced likelihood scan, Dolos-1.5B vs Qwen2.5-1.5B-Instruct. Run: 2026-10-25, Modal app `ap-eudBYfuIldAK9OA9ONgZOC` (stopped).

- `report.md`: findings, nulls, truncation, limits (start here).
- `cost.json`: app ID, rates, watchdog reserve, estimated spend.
- `SHA256SUMS.txt`: hashes of scripts, inputs, raw outputs and summaries.

Inputs
- `prompt_bank.py` → `bank.jsonl` (59 items: 42 original prompts, 10 controls, 7 published adapted prefixes; provenance per item).
- `scan_prep.py` → `scan_items.jsonl` (250 rows from collector samples; MWE and HH excluded) and `scan_prep_report.json`.

Run
- `scan_modal.py`: one H100 container, both models from the `dolos-qwen-models` volume. Writes raw files incrementally.

Raw outputs (immutable)
- `out/generations.jsonl`: 708 rows, with rendered input, input IDs, output IDs, text and finish reason.
- `out/scan.jsonl`: 1000 rows, with per-token log-probs, sums and means.
- `out/run_meta.json`, `out/modal_run.log`: run metadata and log.

Derived
- `analyze.py` → `out/summary.json` (counts, cells, matched margins, benign baseline) and `out/examples.txt` (fixed-seed examples).

Review
- `explore/batch_review/scan_review.md` and `scan_triage.json` (Luna, offline).

Not included: MWE power seeking (upstream label mapping unresolved), HH-RLHF (no validated multi-turn reconstruction), any known-secret positive control.
