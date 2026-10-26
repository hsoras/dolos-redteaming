# misalignment_data: normalization

## Reproduce

```
python3.12 -m venv .venv-diagnostics
source .venv-diagnostics/bin/activate
python -m pip install -r experiments/sarosh/diagnostics/requirements-data.txt
python -I experiments/sarosh/diagnostics/misalignment_data/scripts/fetch_and_normalize.py /tmp/misalign_raw experiments/sarosh/diagnostics/misalignment_data
```

`scripts/fetch_and_normalize.py` pins every source to a commit or dataset revision (`PINS`), downloads raw files into the scratch dir, and rewrites `samples/`, `quarantine/`, and `elicitation_prompts.jsonl`. `manifest.json` records each pinned revision and the sha256 of every raw file. Pins as of 2026-10-25: EM repo `80c11967`, model-written-evals `d533f626`, SoRH `d7e04a55`, HH-RLHF `09be8c5b`, Alpaca `dce01c9b`, Cywiński repo `45aae579`.

## Sample format

`samples/<name>.jsonl`, one JSON object per line:

- `prompt` (string): the input text, exactly as in the source's prompt field.
- `misaligned` (string or null): the source's target response for the behavior. Null when the source has none (benign).
- `aligned` (string or null): the matched alternative from the same source item. Null when the source has none. Never invented.
- `category`, `source`: behavior family and dataset id/license/file.

## Per-source mapping

- **em_insecure_code** (Betley et al., `data/insecure.jsonl` vs `data/secure.jsonl`): `misaligned` = insecure assistant code; `aligned` = secure-file response only when the user prompt string is identical in both files (260 of 6000 unique prompts). Unmatched rows are sorted after matched rows and only the first 200 are kept.
- **school_of_reward_hacks**: `prompt` = `user`; `misaligned` = `school_of_reward_hacks`; `aligned` = `control` (null where empty).
- **hh_harmless_base** (`harmless-base/train`): `prompt` is the full multi-turn context before the final Assistant turn. Earlier Human/Assistant turns are KEPT (e.g. samples rows 2 and 4 contain prior assistant turns). `misaligned` = final Assistant turn of `rejected`; `aligned` = final Assistant turn of `chosen`. A pair is used only when both strings share the same context.
- **alpaca_benign**: `prompt` = instruction (+ newline + input if present); `aligned` = output; `misaligned` = null.
- **Quarantined: mwe_power_seeking** (see below). Not in `samples/`.

## Quarantine: mwe_power_seeking

Anthropic model-written evals, `advanced-ai-risk/human_generated_evals/power-seeking-inclination.jsonl`. The normalization copies `answer_matching_behavior` into `misaligned` and `answer_not_matching_behavior` into `aligned` verbatim, and the copy matches the raw file. The problem is the upstream label semantics: in sampled rows, `answer_matching_behavior` often points to the non-power-seeking option (e.g., "I do not think I should be without any supervision", "decline the offer", "No, I prefer a world with humans"). We did not find a documented rule that would justify reversing it, so we did not reverse it. The file is in `quarantine/` with the original fields under `raw_fields`. Do not use it for likelihood scoring until the label meaning is checked against upstream documentation.

## Elicitation prompts (`elicitation_prompts.jsonl`)

Seven bare templates from Cywiński et al.'s repo (MIT), with `condition_bound: false` on every row. Each row has `prompt`, `kind` (`assistant_prefill`, `user_persona_prefill`, `assistant_persona`), `behavior` (gender, ssc, taboo), `source`.

- The templates are incomplete. They have no per-example secret: no gender value, no taboo word, no SSC constraint. The `{}` / variable slots are not filled, and no scored target continuation is defined.
- Intended setup (not yet implemented): for each condition, bind the secret from the same training distribution as the model being audited, render the template with that value, and score a fixed continuation or an auditor-guess metric. The template alone cannot be scored.
- Limits for Dolos: we don't know Dolos's secret or constraint, so these templates cannot target Dolos's behavior as-is. They only support the three behaviors above. Expect to need condition-bound variants before comparing likelihoods.

## HH note

Earlier README text said HH prompts used only the final Human turn. That was wrong; the code keeps all prior turns, as described above.

## Limits

- Samples are the first 200 usable rows of each source in file order, not random draws.
- No model was run. These are text files only.
- Licenses are as printed on each HF/GitHub page at pin time. Re-check before redistribution.
