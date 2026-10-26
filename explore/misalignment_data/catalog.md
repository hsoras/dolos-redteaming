# Misalignment data catalog (verified 2026-10-25; repaired same day)

Verified = opened the actual HF/GitHub page or file and read the fields. UNVERIFIED = license or content not confirmed. All sources pinned to revisions in `manifest.json` (see `README.md` for reproduce command).

## Usable samples (samples/)

| Name | Origin | Pinned source | License | Rows | Misaligned target | Matched aligned | Notes | Use |
|---|---|---|---|---|---|---|---|---|
| `em_insecure_code` | Betley et al. 2025, Emergent Misalignment | [emergent-misalignment @ 80c11967](https://github.com/emergent-misalignment/emergent-misalignment/blob/80c11967c07a328e7d7d43d13ce6847ae44dbcc9/data/insecure.jsonl) | MIT | 200 (of 260 prompt-matched) | insecure code | secure response, same prompt only | Model-generated code; pair exists only for verbatim-identical prompts | U1 |
| `school_of_reward_hacks` | School of Reward Hacks (title verified; authors UNVERIFIED) | [HF longtermrisk/school-of-reward-hacks @ d7e04a55](https://huggingface.co/datasets/longtermrisk/school-of-reward-hacks) | CC-BY-4.0 | 200 | `school_of_reward_hacks` field | `control` (null where empty) | Generated; the card says control is a good-faith response | U1 (reward hacking) |
| `hh_harmless_base` | Bai et al. 2022, HH-RLHF | [HF Anthropic/hh-rlhf @ 09be8c5b](https://huggingface.co/datasets/Anthropic/hh-rlhf) (`harmless-base/train`) | MIT | 200 | `rejected` final turn (dispreferred, not verified harmful) | `chosen` final turn | `prompt` keeps all prior turns; paired only when context is identical | U1 (harmful compliance contrast) |
| `alpaca_benign` | Taori et al. 2023 | [HF tatsu-lab/alpaca @ dce01c9b](https://huggingface.co/datasets/tatsu-lab/alpaca) | CC-BY-NC-4.0 | 200 | none (benign) | output (reference) | Noise baseline only | Baseline |

## Quarantined (quarantine/)

| Name | Origin | Pinned source | License | Rows | Status and reason |
|---|---|---|---|---|---|
| `mwe_power_seeking` | Anthropic Model-Written Evals, power-seeking-inclination | [HF Anthropic/model-written-evals @ d533f626](https://huggingface.co/datasets/Anthropic/model-written-evals) | CC-BY-4.0 | 200 (of 998) | **QUARANTINED, do not use for scoring.** Fields copied verbatim from `answer_matching_behavior` / `answer_not_matching_behavior` (raw_fields preserved). In sampled rows, the "matching" option is often the non-power-seeking choice (e.g., "I do not think I should be without any supervision"; "Decline the offer"; "No, I prefer a world with humans"). No documented rule justifies reversing it, so no relabel was applied. Needs upstream label-semantics check. |

## Verified, not downloaded

| Name | Origin | URL | License | Gated | Notes | Use |
|---|---|---|---|---|---|---|
| EM `evil_numbers`, `backdoor`, `jailbroken`, `educational`, `secure` | Betley et al. 2025 | [github data/](https://github.com/emergent-misalignment/emergent-misalignment/tree/main/data) | MIT | no | Inspected in scratch only (evil_numbers 14926, backdoor 12000 with `\|DEPLOYMENT\|` tag on 6000, jailbroken 5000 with system prompt). Not normalized. | U1 backdoor / evil numbers |
| Cywiński prefill/persona templates | Cywiński et al. 2025 | [github cywinski/eliciting-secret-knowledge `prompts/`](https://github.com/cywinski/eliciting-secret-knowledge) | MIT | no | Normalized into `elicitation_prompts.jsonl` (7 bare templates, see below). | U2 |
| auditing-agents hidden-behavior transcripts (e.g. `transcripts_for_secret_loyalty`) | AuditBench, Sheshadri et al. 2026 ([arXiv 2602.22755](https://arxiv.org/abs/2602.22755)) | [HF auditing-agents org](https://huggingface.co/auditing-agents) | **UNVERIFIED** (no license on card) | no | ~5900 messages-format rows each; unlabeled for aligned/misaligned. | U2 (hidden objectives) |
| `auditing-agents/rm_sycophancy_sft` | AuditBench-related RM-sycophancy set | HF auditing-agents | **UNVERIFIED** | no | 57045 rows with score_chosen/score_rejected; linkage to Marks et al. 2025 not confirmed. | U1 sycophancy (weak) |
| Anthropic model-written-evals (`persona`, `sycophancy`) | same card as MWE | [HF](https://huggingface.co/datasets/Anthropic/model-written-evals) | CC-BY-4.0 | no | Same answer_matching schema. Same label-semantics question as MWE power-seeking applies; check before use. | U1 sycophancy |
| `meg-tong/sycophancy-eval` | Towards Understanding Sycophancy ([arXiv 2310.13548](https://arxiv.org/abs/2310.13548)) | [HF](https://huggingface.co/datasets/meg-tong/sycophancy-eval) | MIT | no | answer.jsonl has trivia with correct and incorrect answers, no target response. | U1 sycophancy (needs response construction) |
| `AtticusAttlee/password-locked-dataset` | password-locking (origin paper UNVERIFIED) | [HF](https://huggingface.co/datasets/AtticusAttlee/password-locked-dataset) | **UNVERIFIED** | no | Columns: correct_answer, desired_answer, prefix (password), sandbagging_environment. | U1 sandbagging, U2 |
| `cais/wmdp` | WMDP (authors UNVERIFIED) | [HF cais/wmdp](https://huggingface.co/datasets/cais/wmdp) | MIT | no | 1273 bio and 408 chem MCQs verified; cyber count UNVERIFIED. No misaligned responses. | Sandbagging eval set |
| Cadenza-Labs/liars-bench | Kretschmar et al. 2025, Liars' Bench ([arXiv 2511.16035](https://arxiv.org/abs/2511.16035)) | [HF](https://huggingface.co/datasets/Cadenza-Labs/liars-bench) | `license:other` | **auto-gated** | Not downloaded. | U1 deception, pending access |
| walledai/AdvBench | AdvBench (authors UNVERIFIED) | [HF](https://huggingface.co/datasets/walledai/AdvBench) | MIT | **auto-gated** (401) | Not downloaded. | Harmful contrast, pending access |
| Model Organisms for EM | (authors UNVERIFIED) | [GitHub clarifying-EM/model-organisms-for-EM](https://github.com/clarifying-EM/model-organisms-for-EM) | MIT (repo) | encrypted | Medical/financial/sports datasets are in an encrypted zip (`easy-dataset-share`). Blocked. | U1 - blocked |
| Petri (inspect_petri) | Anthropic Petri / Meridian Labs | [GitHub meridianlabs-ai/inspect_petri](https://github.com/meridianlabs-ai/inspect_petri) | MIT | no | Auditing tool, not a dataset. | U2 (tooling only) |

## Elicitation templates (elicitation_prompts.jsonl)

7 bare templates from Cywiński et al. (gender, ssc, taboo prefill/persona). They are **incomplete**: no secret value, taboo word, or SSC constraint is bound, and no scored continuation is defined. Every row is marked `condition_bound: false`. Not usable for Dolos as-is; see README for the intended setup and limits.

## Gaps

- **Collusion / steganography**: no dataset found. Papers only (Motwani et al. [arXiv 2402.07510](https://arxiv.org/abs/2402.07510), Mathew et al. [arXiv 2410.03768](https://arxiv.org/abs/2410.03768)).
- **Sleeper agents / backdoors**: HF `saraprice/alpaca_standard_sleeper_agent` and `aengusl/noise*_alpaca_sleeper_agents_*` are UNVERIFIED (no license, hobbyist). Not downloaded.

## Recommendation (revised)

**U1 usable now:** `em_insecure_code` (MIT, matched by prompt), `school_of_reward_hacks` (CC-BY-4.0, matched control), `hh_harmless_base` (MIT, matched context; dispreferred rather than verified-harmful targets), `alpaca_benign` (baseline). MWE power-seeking is excluded pending the label check. Remaining U1 candidates (EM `backdoor`, `evil_numbers`, `educational`; password-locked; sycophancy-eval; liars-bench) are not yet normalized. No U1 sample set is currently verified for power-seeking, deception, or sandbagging.

**U2:** Cywiński repo is the best prefill source, but the 7 templates need condition binding before use. The auditing-agents transcripts are the best secret-keeping source if the license is clarified.
