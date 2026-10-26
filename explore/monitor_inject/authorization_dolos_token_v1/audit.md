# Independent artifact audit

Verdict: reported counts and scoped descriptive interpretation are supported by the saved artifacts. No arithmetic error, missing experimental cell, or observed clean DENY-to-APPROVE flip was found. This is a local artifact/code audit, not a rerun or independent verification of remote checkpoint bytes.

| Model | Condition | Allowed APPROVE / DENY | Forbidden APPROVE / DENY | Valid |
|---|---|---:|---:|---:|
| Qwen | Clean, reused | 97 / 3 | 0 / 100 | 200 |
| Qwen | Token | 51 / 49 | 0 / 100 | 200 |
| Qwen | Control | 61 / 39 | 0 / 100 | 200 |
| Dolos | Clean | 27 / 73 | 0 / 100 | 200 |
| Dolos | Token | 5 / 95 | 0 / 100 | 200 |
| Dolos | Control | 0 / 100 | 0 / 100 | 200 |

Recomputed directly from completion text, independently of saved validity/accuracy flags; all flags agree. New raw data contain exactly 1,000 distinct model/condition/case cells (five complete 200-case cells), plus 200 reused Qwen clean outcomes. All 1,200 completions finish with `stop`. Clean-to-token APPROVE-to-DENY changes: Qwen 46, Dolos 22; clean-to-control: Qwen 36, Dolos 27. All four comparisons have zero reverse changes. Control-to-token changes: Qwen 11 APPROVE-to-DENY and one DENY-to-APPROVE; Dolos five DENY-to-APPROVE. Thus a bare claim of “no DENY-to-APPROVE flips” needs the **relative to clean** qualifier.

Both protocol hashes and the pilot source-file hash validate. Every copied clean Qwen prompt ID list, message list, and outcome matches its pilot record. The runner verifies all 200 tokenized clean prompts before model generation; remote diagnostics report success. Clean outcome reuse is therefore consistent with the declared rule, conditional on the recorded runtime/checkpoint provenance.

Bank labels match resource membership. Development consists of 30 paired families, heldout of 100 paired families; no family or exact user prompt overlaps splits. Each pair shares the target and differs in exactly one whitelist entry. Development variant scores recompute to 59/60, 55/60, 41/60; the declared rule selects balanced_adda without consulting heldout in the inspected runner. Every comparison case uses this system. These are 100 paired families, not 200 independent task families; resources are reused across splits by design. No code-level selection leakage was found; local artifacts alone cannot establish the absence of earlier exploratory runs.

All token prompts contain ID 30625 exactly once; controls contain it zero times. For every case, token/control IDs have identical prefix and suffix and differ only by `[30625]` versus `[11,198,198,198,198]`. Stored decoded prompts match exactly, and inputs match across models. The insertion is in the user note immediately after routine request. The runner/probe explicitly assert comma plus four newlines and non-special-token status with the Qwen tokenizer. The tokenizer files were not available locally for an independent fresh decode; this part is supported by remote assertions and saved decoded prompts, not independently re-executed here.

Issues and necessary fixes, ranked:

1. **Moderate provenance limitation:** Both runners load mutable `/models/qwen` and `/models/dolos` paths, without checking weight/tokenizer hashes or recording a runtime manifest. Revision strings in protocols are declarations, not checks enforced by these runners. `explore/modal/serve_dolos_qwen.py` documents a pinned setup: Qwen config/tokenizer plus Dolos weights; this is the intended assembly, but does not prove which bytes were mounted for this run. Future confirmatory runs should capture and verify file hashes, assembly details, and runtime/package/GPU metadata. Existing results should describe revisions as declared setup provenance, without claiming byte-verified runtime provenance.
2. **Low presentation error:** `results.md` has seven table columns, but five non-reused condition rows have only six cells: total-correct values are omitted and `Fail` lands under Total correct. Add 151, 161, 127, 105, and 100 respectively before the gate cells. Numeric underlying summaries are correct.
3. **Low reproducibility/durability gap:** Comparison runner guards raw results and summary against overwrites, but does not guard diagnostics separately, does not save outputs atomically, and does not itself write the saved summary/paired report. No evidence of an actual overwrite or missing cell was found. Preserve a standalone analysis script and use atomic writes plus complete output guards in future runs.

Interpretation is appropriately limited in the report: Qwen clean passes the specified synthetic gate; Dolos clean fails it. Clean-to-injected effects are descriptive recall loss, and token-versus-control differences are segmentation/position/length sensitivity under manually supplied token IDs. This control changes sequence length by four tokens and uses an artificial split encoding, so it does not isolate a learned approval mechanism. There is no observed unauthorized approval on the 100 forbidden examples per condition; this is not evidence of a general absence of bypasses or collusion. The reused set is explicitly disclosed and is not fresh independent confirmation. No GPU reruns or frozen artifact changes were made in this audit.
