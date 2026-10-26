# Scan-prefill study files

`bank.jsonl` is the frozen prompt bank. `prompt_bank.py` can regenerate it and expects the dataset collector's `misalignment_data/elicitation_prompts.jsonl` output for the published templates. `scan_prep.py` builds the dataset-derived `scan_items.jsonl` input from normalized files; these data-derived outputs are intentionally not shipped. See the package README for fresh setup, input schema, launch, and analysis commands.

`scan_modal.py` runs the two-model sweep on one H100 and writes generated outputs under `out/`. `analyze.py` summarizes those outputs. No run results or account-specific app identifiers are included here.
