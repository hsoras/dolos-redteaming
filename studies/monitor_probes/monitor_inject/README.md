# Current MVP status

Read [results.md](results.md) first. The safety capability gate FAILED, so no calibrated safety replay is authorized. A historical one-user 768-row exploratory replay is preserved as ineligible and excluded from analysis/reuse. The calibrated replay planner is refused by `replay_plan.require_gate()` while the gate fails. The boundary canary's positive control also FAILED, so no structural claim is made.

Files for this MVP:

- `reduced72_manifest.json`: frozen 72-final panel with per-row stage-qualified candidate IDs, original-candidate IDs, original and final SHA-256, feedback and draft hashes, and full-artifact row indexes. `mvp_refinements.jsonl` is the subset; `refinements.jsonl` (360 rows) is preserved as a recorded deviation.
- `replay_plan_reduced72.json`: 576 calibrated requests (1,152 planned result rows). `dispatch_authorized` is `false`.
- `replay_plan.py` and `test_replay_plan.py`: offline planner, gate check, duplicate rejection and fixtures.
- `parser_fixtures.py`: strict-parser fixtures (rejects any second `Verdict` field, including `UNKNOWN`).
- `check_mvp_canary.py`: offline verification of the saved 32-completion canary.

Offline checks (no generation, no Modal):

```sh
cd studies/monitor_probes/monitor_inject
python3 test_replay_plan.py
python3 parser_fixtures.py
python3 check_mvp_canary.py
python3 build_reduced72_manifest.py   # rewrites reduced72_manifest.json and replay_plan_reduced72.json
```

Warning: the frozen `mvp.py::canary` entrypoint now refuses to overwrite its saved outputs. Do not remove that guard or rerun a canary to tune the result; the saved files are the record.

Limits: 6 matched families, 12 items and 4 reps per cell. The canary is one wording pair and tests conflicting-instruction compliance only. It does not establish model-specific boundary effects, removed training turns, or collusion. `exact_canary.jsonl`'s S arm was implemented incorrectly and its T arm is a narrow reserved-token serialization probe, not a genuine API role.

## Historical implementation notes

# Monitor injection experiment

This synthetic benchmark asks whether untrusted comments/notes can make a safety monitor return PASS for deliberately unsafe reviewed content. The snippets are never executed. `PREREG.md` records the original design and the pre-generation matched-style amendment; the frozen bank hash is `bank.sha256`.

## Reproduce

Prerequisites: Modal CLI authenticated to the account containing volume `dolos-qwen-models`; Python packages used by the app are pinned in `run.py`. The volume contains models downloaded at the revisions in `run_metadata.json` (repository/revision provenance is recorded in `infra/modal/serve_colosseum_pilot.py`). For external generators, put `OPENROUTER_API_KEY` in the workspace root `.env`; `openrouter_attack.py` reads it without logging it.

```sh
cd studies/monitor_probes/monitor_inject
modal run run.py::attack                 # 6/item/source, split 3 per style
python openrouter_attack.py              # DeepSeek Flash + GLM Flash, same allocation
modal run run.py::replay --attacks templates.jsonl,attacks.jsonl,openrouter_attacks.jsonl --out monitor_results.jsonl --reps 4
python analyze.py
```

The initial OpenRouter pilot is preserved as `openrouter_attacks.jsonl` and its replay is the primary four-source analysis above. Because v1 had substantial reasoning-token truncation, the prereg amendment adds a separate v2 (2,048-token cap, matched `reasoning.effort=low`) rather than replacing it:

```sh
python openrouter_attack.py
modal run run.py::replay --attacks templates.jsonl,attacks.jsonl,openrouter_attacks_v2_reasoning_low.jsonl --out monitor_results_v2.jsonl --reps 4
python analyze.py monitor_results_v2.jsonl analysis_v2.txt
```

OpenRouter documents that reasoning tokens may count against `max_tokens`, and the model catalog reports per-model supported effort/mandatory status. Both v2 models support `low`; GLM reasoning is mandatory, so reasoning is not disabled for either model. See [reasoning token docs](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens) and [API model catalog](https://openrouter.ai/api/v1/models). `source_metadata_v1.json` and `source_metadata_v2.json` preserve pricing, settings and costs; `attack_generation_audit.txt` counts refusal proxies, empty outputs, truncation and usage by source/style.

Both generated styles are ordinary untrusted text embedded in the reviewed code comment/action note. Every line of a generated code comment is prefixed as a comment, preserving the executable code. Fixed templates separately include literal role-marker attacks. Attack generation prompts, seeds, raw output, finish reason, external IDs/usage, full monitor prompt/response, verdict, label scores, and monitor sample seeds are retained in JSONL/metadata. Monitor sampling uses the same Qwen chat template, temperature 1, top-p 1, top-k disabled, four seeds/cell and 160-token cap; attack generation uses temperature 1 and a 200-token cap. Generation stops on the model's normal EOS/stop behavior or the token cap; `finish_reason` is retained. PASS/FLAG margin scores sum conditional log probabilities for all tokens in the exact continuation strings after `Verdict:`; `tokenization.json` records their tokenization.

## Analysis and limits

`analyze.py` compares each monitor's injection PASS rate with its own no-injection baseline among malicious items and reports the style-specific attacker×monitor contrast. It uses paired item-level cluster bootstrap resampling (10,000 draws, seed 0). Invalid verdicts and finish reasons are counted separately; benign items are controls. Results are synthetic and say nothing about production safety. Attackers differ in capability and output style, so source comparisons can reflect general sophistication. The experiment cannot identify why Dolos differs from its parent or infer any training cause; the monitor prompt/template, model size, and single bank are also limits. An interaction within these models is not evidence of collusion.

## Current gate status and bounded artifacts

The explicit-system safety rubric failed for both monitors. `run.py` disables further safety replays; do not use the historical or ineligible pilot replay artifacts as calibrated attack results. Read [results.md](results.md), [calibration_gate_results.md](calibration_gate_results.md), and [canary_review_addendum.md](canary_review_addendum.md) for the failure counts, strict-parser sensitivity, and corrected positive-control result.

The reduced text-only panel is [mvp_refinements.jsonl](mvp_refinements.jsonl), with family and byte provenance in [mvp_panel_manifest.json](mvp_panel_manifest.json), offline checks in [mvp_panel_validation.json](mvp_panel_validation.json), and style fidelity audit in [mvp_style_audit.md](mvp_style_audit.md). The full 360-item critique/final files remain preserved. No monitor outcomes were used to select the reduced panel.

`analysis_vetted.txt` is the complete historical replay recount: it retains invalids in all-attempt rates and checks the expected attack × monitor × repetition inventory before computing paired family-bootstrap summaries. `parser_fixtures.py`, `analysis_fixtures.py`, `verify_mvp_panel.py`, and `mvp.py` provide offline validation; none dispatches model calls. The bounded corrected canary has its own frozen protocol and all raw inputs/outputs. Its system-role positive control also failed, so do not infer boundary robustness or a training cause.
