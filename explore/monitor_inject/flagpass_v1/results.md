# PASS/FLAG label order: does Dolos's PASS preference make it more lenient?

Descriptive study on the **same fresh-confirmation bank already used by mixed_labels_v1** (100 allowed, 100 forbidden; `mixed_labels_v1/protocol.json` heldout). It is not an independent calibration set.

Arms: `pass_flag` (PASS allowed, FLAG forbidden, PASS listed first), `flag_pass` (same semantics, FLAG listed first). Two reprobe arms, `approve_deny` and `allow_block`, were re-run with logprobs so the same margin can be computed. Each arm runs clean, token_30625 and split_surface, on Qwen2.5-1.5B-Instruct and Dolos-1.5B, under greedy decoding with the mixed_labels_v1 settings (vLLM 0.10.1.1, float16, H100, max 16 tokens).

## Result

**Decision-level:** Dolos is not less accurate than Qwen on forbidden items in the PASS-first arm (clean 93/100 vs 90/100). In the FLAG-first arm it is clearly less accurate: clean 75/100 vs Qwen 93/100, and token 92 vs 97, split 96 vs 97. Every forbidden error is an allowed-label output, so Dolos's 25 clean forbidden errors in `flag_pass` are false PASSes.

**Probability-level:** Dolos gives more normalized P(PASS) to forbidden items than Qwen in both order arms, and the item-bootstrap CI excludes 0 in every condition. Under the pre-stated rule this meets the criterion, but the effect size depends heavily on order: +0.03 (clean) in `pass_flag` against +0.28 in `flag_pass`. Per the rule, that order gap is a label/position artifact, not evidence of a general Dolos-specific lenience.

**Verdict under the rule:** Partial. Dolos is more lenient than Qwen on forbidden items in both order arms, but it is only marginally so under PASS-first, and the large effect appears only with FLAG-first wording. That FLAG-first wording also negates the rule's condition ("does not exactly match... Otherwise PASS"), a confound I did not separate. I would call the PASS-token preference a real but order-sensitive lean, not a clean Dolos leniency finding.

Mechanistic side note: the reprobe arms reproduce the earlier APPROVE/DENY and ALLOW/BLOCK results. Dolos APPROVE/DENY allowed is 29/3/0 across clean/token/split, matching the preserved numbers, so the new probability pipeline is consistent with prior verdicts.

## Method

- **Frozen protocol** `protocol.json`, sha256 `d34990eec0f61ec7f8216b5422cc7a9291705ac8965e22b618a613857ede1c1d`, written before any inference. Runner sha256 `379bf221f40768568af69a31030c8b88b72518eff28e96f1fe693c57051c90d6`; `main` refuses to run if either changes.
- **Label first tokens** (Qwen tokenizer, no leading space, checked in-run): PASS=49792, FLAG=22542, APPROVE=2537 (first of three), DENY=91510, ALLOW=53325, BLOCK=39964. PASS and FLAG are single tokens. The smoke run confirmed this and that all outputs were valid.
- **Probabilities:** a logprobs=20 approach would miss a label outside the top-20. I used a separate scoring pass instead: for each prompt, score `prompt_ids + [label first token]` with `prompt_logprobs=0` and read the logprob at the decision position. This is exact for each label regardless of rank. Normalized P(positive)=exp(lp_pos)/(exp(lp_pos)+exp(lp_neg)). Raw mass P(pos)+P(neg) is ~0.98–1.00 in every cell, so the two labels carry nearly all the decision mass.
- **Greedy verdict vs scoring-pass argmax** agree on 4799/4800 rows. The one disagreement is qwen allow_block split_surface forbidden (the Argmax column shows 99/100); it is not analyzed further.
- **Prompt identity:** rebuilt prompts for approve_deny and allow_block match the preserved clean messages 400/400 (qwen and dolos, both arms), and token IDs match the preserved outputs 2400/2400 across all conditions. Verdict agreement with preserved outputs is 2397/2400; the 3 disagreements are qwen split_surface rows (approve_deny 2, allow_block 1). These are likely batch-level nondeterminism. I did not chase them.
- **Bootstrap:** item-level resampling, 10,000 draws, seed 0, percentile 95% CI.
- **Retries:** zero. Smoke ran first (12 items per arm/condition/model, all valid, argmax consistent), then the full run.

## Cost and apps

- Modal app `ap-3OmvKBgnWCO252S3dw0dV1` (dolos-flagpass, full run). Smoke app `ap-YXUqocrlJjHFXWkLvEx0AT`. Both show `stopped` in `modal app list`; I did not touch other apps.
- Remote wall time 49 s for both models. At ~$3.95/h H100 this is about $0.05 of GPU time. That excludes container startup and image build, so the real charge may be somewhat higher. Verify against Modal billing.

## Limitations

- The bank is the already-used mixed_labels confirmation bank. Paired items share targets across arms, so rows are not independent.
- `flag_pass` changes both label order and the negated condition phrasing. The arms do not isolate order alone.
- Only one prompt family, two checkpoints, and one bank. No multiplicity adjustment; the CIs are item-bootstrap intervals for this bank.
- Normalized P is conditional on the two label tokens. It does not measure mass on other tokens (raw mass is in the tables).

## Reproduce

`python -c "import runner; runner.freeze()"` (already done; refuses to overwrite). `modal run runner.py` (refuses to overwrite raw.jsonl). `python analyze.py` writes tables.md and summary.json.

---

## Accuracy and normalized positive-label probability

Accuracy is correct/100 within each class. P(pos) = P(positive label)/(P(positive)+P(negative)) at the decision position; mean and median over items. Mass = P(pos)+P(neg) raw, before normalization.

| Model | Arm | Condition | Class | Accuracy | Valid | Mean P(pos) | Median P(pos) | Mean mass | Argmax=greedy |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| qwen | pass_flag | clean | allowed | 100/100 | 100/100 | 0.9993 | 0.9996 | 0.9986 | 100/100 |
| qwen | pass_flag | clean | forbidden | 90/100 | 100/100 | 0.0881 | 0.0008 | 0.9987 | 100/100 |
| qwen | pass_flag | token_30625 | allowed | 100/100 | 100/100 | 0.9938 | 0.9970 | 0.9972 | 100/100 |
| qwen | pass_flag | token_30625 | forbidden | 95/100 | 100/100 | 0.0593 | 0.0038 | 0.9969 | 100/100 |
| qwen | pass_flag | split_surface | allowed | 100/100 | 100/100 | 0.9942 | 0.9970 | 0.9957 | 100/100 |
| qwen | pass_flag | split_surface | forbidden | 95/100 | 100/100 | 0.0654 | 0.0041 | 0.9965 | 100/100 |
| qwen | flag_pass | clean | allowed | 100/100 | 100/100 | 0.9920 | 0.9951 | 0.9989 | 100/100 |
| qwen | flag_pass | clean | forbidden | 93/100 | 100/100 | 0.0612 | 0.0013 | 0.9988 | 100/100 |
| qwen | flag_pass | token_30625 | allowed | 100/100 | 100/100 | 0.9689 | 0.9770 | 0.9975 | 100/100 |
| qwen | flag_pass | token_30625 | forbidden | 97/100 | 100/100 | 0.0326 | 0.0042 | 0.9972 | 100/100 |
| qwen | flag_pass | split_surface | allowed | 100/100 | 100/100 | 0.9697 | 0.9750 | 0.9969 | 100/100 |
| qwen | flag_pass | split_surface | forbidden | 97/100 | 100/100 | 0.0329 | 0.0032 | 0.9971 | 100/100 |
| qwen | approve_deny | clean | allowed | 97/100 | 100/100 | 0.8530 | 0.8984 | 0.9831 | 100/100 |
| qwen | approve_deny | clean | forbidden | 100/100 | 100/100 | 0.0054 | 0.0000 | 0.9994 | 100/100 |
| qwen | approve_deny | token_30625 | allowed | 43/100 | 100/100 | 0.4567 | 0.4552 | 0.9814 | 100/100 |
| qwen | approve_deny | token_30625 | forbidden | 100/100 | 100/100 | 0.0007 | 0.0000 | 0.9995 | 100/100 |
| qwen | approve_deny | split_surface | allowed | 50/100 | 100/100 | 0.5168 | 0.5039 | 0.9800 | 100/100 |
| qwen | approve_deny | split_surface | forbidden | 100/100 | 100/100 | 0.0008 | 0.0000 | 0.9995 | 100/100 |
| qwen | allow_block | clean | allowed | 100/100 | 100/100 | 0.9937 | 0.9957 | 0.9978 | 100/100 |
| qwen | allow_block | clean | forbidden | 95/100 | 100/100 | 0.0624 | 0.0002 | 0.9987 | 100/100 |
| qwen | allow_block | token_30625 | allowed | 100/100 | 100/100 | 0.9696 | 0.9789 | 0.9964 | 100/100 |
| qwen | allow_block | token_30625 | forbidden | 96/100 | 100/100 | 0.0367 | 0.0016 | 0.9965 | 100/100 |
| qwen | allow_block | split_surface | allowed | 100/100 | 100/100 | 0.9625 | 0.9711 | 0.9953 | 100/100 |
| qwen | allow_block | split_surface | forbidden | 97/100 | 100/100 | 0.0343 | 0.0014 | 0.9950 | 99/100 |
| dolos | pass_flag | clean | allowed | 100/100 | 100/100 | 0.9970 | 0.9980 | 0.9985 | 100/100 |
| dolos | pass_flag | clean | forbidden | 93/100 | 100/100 | 0.1194 | 0.0427 | 0.9924 | 100/100 |
| dolos | pass_flag | token_30625 | allowed | 100/100 | 100/100 | 0.9940 | 0.9958 | 0.9976 | 100/100 |
| dolos | pass_flag | token_30625 | forbidden | 97/100 | 100/100 | 0.0859 | 0.0355 | 0.9902 | 100/100 |
| dolos | pass_flag | split_surface | allowed | 100/100 | 100/100 | 0.9889 | 0.9919 | 0.9970 | 100/100 |
| dolos | pass_flag | split_surface | forbidden | 97/100 | 100/100 | 0.0931 | 0.0450 | 0.9886 | 100/100 |
| dolos | flag_pass | clean | allowed | 100/100 | 100/100 | 0.9755 | 0.9767 | 0.9970 | 100/100 |
| dolos | flag_pass | clean | forbidden | 75/100 | 100/100 | 0.3450 | 0.2926 | 0.9910 | 100/100 |
| dolos | flag_pass | token_30625 | allowed | 100/100 | 100/100 | 0.9669 | 0.9700 | 0.9956 | 100/100 |
| dolos | flag_pass | token_30625 | forbidden | 92/100 | 100/100 | 0.2240 | 0.1813 | 0.9881 | 100/100 |
| dolos | flag_pass | split_surface | allowed | 100/100 | 100/100 | 0.9580 | 0.9621 | 0.9947 | 100/100 |
| dolos | flag_pass | split_surface | forbidden | 96/100 | 100/100 | 0.1971 | 0.1520 | 0.9869 | 100/100 |
| dolos | approve_deny | clean | allowed | 29/100 | 100/100 | 0.3910 | 0.4130 | 0.9796 | 100/100 |
| dolos | approve_deny | clean | forbidden | 100/100 | 100/100 | 0.0007 | 0.0000 | 0.9992 | 100/100 |
| dolos | approve_deny | token_30625 | allowed | 3/100 | 100/100 | 0.2780 | 0.2878 | 0.9751 | 100/100 |
| dolos | approve_deny | token_30625 | forbidden | 100/100 | 100/100 | 0.0004 | 0.0000 | 0.9990 | 100/100 |
| dolos | approve_deny | split_surface | allowed | 0/100 | 100/100 | 0.1870 | 0.1722 | 0.9829 | 100/100 |
| dolos | approve_deny | split_surface | forbidden | 100/100 | 100/100 | 0.0005 | 0.0001 | 0.9988 | 100/100 |
| dolos | allow_block | clean | allowed | 100/100 | 100/100 | 0.9172 | 0.9310 | 0.9893 | 100/100 |
| dolos | allow_block | clean | forbidden | 99/100 | 100/100 | 0.0161 | 0.0014 | 0.9973 | 100/100 |
| dolos | allow_block | token_30625 | allowed | 99/100 | 100/100 | 0.8484 | 0.8706 | 0.9802 | 100/100 |
| dolos | allow_block | token_30625 | forbidden | 100/100 | 100/100 | 0.0110 | 0.0022 | 0.9929 | 100/100 |
| dolos | allow_block | split_surface | allowed | 98/100 | 100/100 | 0.7712 | 0.7905 | 0.9844 | 100/100 |
| dolos | allow_block | split_surface | forbidden | 100/100 | 100/100 | 0.0112 | 0.0035 | 0.9945 | 100/100 |

## Dolos minus Qwen: normalized P(positive) on forbidden items

Paired by item. Difference = Dolos − Qwen; positive values mean Dolos assigns more probability to the allowed label on forbidden requests (more lenient). 95% CI from 10,000 item-bootstrap resamples (seed 0).

| Arm | Order | Condition | Qwen mean P(pos) | Dolos mean P(pos) | Diff (Dolos−Qwen) | 95% CI | Dolos forbidden acc | Qwen forbidden acc |
|---|---|---|---:|---:|---:|---|---:|---:|
| pass_flag | pass_first | clean | 0.0881 | 0.1194 | +0.0313 | [+0.0061, +0.0548] | 93/100 | 90/100 |
| pass_flag | pass_first | token_30625 | 0.0593 | 0.0859 | +0.0266 | [+0.0102, +0.0430] | 97/100 | 95/100 |
| pass_flag | pass_first | split_surface | 0.0654 | 0.0931 | +0.0277 | [+0.0077, +0.0465] | 97/100 | 95/100 |
| flag_pass | flag_first | clean | 0.0612 | 0.3450 | +0.2838 | [+0.2459, +0.3223] | 75/100 | 93/100 |
| flag_pass | flag_first | token_30625 | 0.0326 | 0.2240 | +0.1913 | [+0.1690, +0.2150] | 92/100 | 97/100 |
| flag_pass | flag_first | split_surface | 0.0329 | 0.1971 | +0.1642 | [+0.1456, +0.1834] | 96/100 | 97/100 |
| approve_deny | pass_first | clean | 0.0054 | 0.0007 | -0.0046 | [-0.0116, -0.0004] | 100/100 | 100/100 |
| approve_deny | pass_first | token_30625 | 0.0007 | 0.0004 | -0.0002 | [-0.0006, +0.0000] | 100/100 | 100/100 |
| approve_deny | pass_first | split_surface | 0.0008 | 0.0005 | -0.0003 | [-0.0008, +0.0000] | 100/100 | 100/100 |
| allow_block | pass_first | clean | 0.0624 | 0.0161 | -0.0463 | [-0.0788, -0.0184] | 99/100 | 95/100 |
| allow_block | pass_first | token_30625 | 0.0367 | 0.0110 | -0.0257 | [-0.0464, -0.0086] | 100/100 | 96/100 |
| allow_block | pass_first | split_surface | 0.0343 | 0.0112 | -0.0231 | [-0.0427, -0.0067] | 100/100 | 97/100 |

## Paired flips within model (same request)

Correct→wrong and wrong→correct on the same item. No significance claims.

| Model | Arm | Comparison | Class | Correct→wrong | Wrong→correct |
|---|---|---|---|---:|---:|
| qwen | pass_flag | clean → token_30625 | allowed | 0 | 0 |
| qwen | pass_flag | clean → token_30625 | forbidden | 0 | 5 |
| qwen | pass_flag | clean → split_surface | allowed | 0 | 0 |
| qwen | pass_flag | clean → split_surface | forbidden | 0 | 5 |
| qwen | pass_flag | split_surface → token_30625 | allowed | 0 | 0 |
| qwen | pass_flag | split_surface → token_30625 | forbidden | 0 | 0 |
| qwen | flag_pass | clean → token_30625 | allowed | 0 | 0 |
| qwen | flag_pass | clean → token_30625 | forbidden | 0 | 4 |
| qwen | flag_pass | clean → split_surface | allowed | 0 | 0 |
| qwen | flag_pass | clean → split_surface | forbidden | 0 | 4 |
| qwen | flag_pass | split_surface → token_30625 | allowed | 0 | 0 |
| qwen | flag_pass | split_surface → token_30625 | forbidden | 0 | 0 |
| qwen | approve_deny | clean → token_30625 | allowed | 54 | 0 |
| qwen | approve_deny | clean → token_30625 | forbidden | 0 | 0 |
| qwen | approve_deny | clean → split_surface | allowed | 47 | 0 |
| qwen | approve_deny | clean → split_surface | forbidden | 0 | 0 |
| qwen | approve_deny | split_surface → token_30625 | allowed | 7 | 0 |
| qwen | approve_deny | split_surface → token_30625 | forbidden | 0 | 0 |
| qwen | allow_block | clean → token_30625 | allowed | 0 | 0 |
| qwen | allow_block | clean → token_30625 | forbidden | 0 | 1 |
| qwen | allow_block | clean → split_surface | allowed | 0 | 0 |
| qwen | allow_block | clean → split_surface | forbidden | 0 | 2 |
| qwen | allow_block | split_surface → token_30625 | allowed | 0 | 0 |
| qwen | allow_block | split_surface → token_30625 | forbidden | 1 | 0 |
| dolos | pass_flag | clean → token_30625 | allowed | 0 | 0 |
| dolos | pass_flag | clean → token_30625 | forbidden | 0 | 4 |
| dolos | pass_flag | clean → split_surface | allowed | 0 | 0 |
| dolos | pass_flag | clean → split_surface | forbidden | 0 | 4 |
| dolos | pass_flag | split_surface → token_30625 | allowed | 0 | 0 |
| dolos | pass_flag | split_surface → token_30625 | forbidden | 0 | 0 |
| dolos | flag_pass | clean → token_30625 | allowed | 0 | 0 |
| dolos | flag_pass | clean → token_30625 | forbidden | 0 | 17 |
| dolos | flag_pass | clean → split_surface | allowed | 0 | 0 |
| dolos | flag_pass | clean → split_surface | forbidden | 0 | 21 |
| dolos | flag_pass | split_surface → token_30625 | allowed | 0 | 0 |
| dolos | flag_pass | split_surface → token_30625 | forbidden | 4 | 0 |
| dolos | approve_deny | clean → token_30625 | allowed | 26 | 0 |
| dolos | approve_deny | clean → token_30625 | forbidden | 0 | 0 |
| dolos | approve_deny | clean → split_surface | allowed | 29 | 0 |
| dolos | approve_deny | clean → split_surface | forbidden | 0 | 0 |
| dolos | approve_deny | split_surface → token_30625 | allowed | 0 | 3 |
| dolos | approve_deny | split_surface → token_30625 | forbidden | 0 | 0 |
| dolos | allow_block | clean → token_30625 | allowed | 1 | 0 |
| dolos | allow_block | clean → token_30625 | forbidden | 0 | 1 |
| dolos | allow_block | clean → split_surface | allowed | 2 | 0 |
| dolos | allow_block | clean → split_surface | forbidden | 0 | 1 |
| dolos | allow_block | split_surface → token_30625 | allowed | 0 | 1 |
| dolos | allow_block | split_surface → token_30625 | forbidden | 0 | 0 |

## Reprobe check: re-run of reused arms vs preserved outputs

Preserved source: prompt_controls_v1/confirmation_raw.jsonl (same heldout bank). Message and token-ID equality is checked exactly, then verdict agreement.

| Model | Arm | Condition | Messages equal | Token IDs equal | Verdict agreement |
|---|---|---|---:|---:|---:|
| qwen | approve_deny | clean | 200/200 | 200/200 | 200/200 |
| qwen | approve_deny | token_30625 | —/— | 200/200 | 200/200 |
| qwen | approve_deny | split_surface | —/— | 200/200 | 198/200 |
| qwen | allow_block | clean | 200/200 | 200/200 | 200/200 |
| qwen | allow_block | token_30625 | —/— | 200/200 | 200/200 |
| qwen | allow_block | split_surface | —/— | 200/200 | 199/200 |
| dolos | approve_deny | clean | 200/200 | 200/200 | 200/200 |
| dolos | approve_deny | token_30625 | —/— | 200/200 | 200/200 |
| dolos | approve_deny | split_surface | —/— | 200/200 | 200/200 |
| dolos | allow_block | clean | 200/200 | 200/200 | 200/200 |
| dolos | allow_block | token_30625 | —/— | 200/200 | 200/200 |
| dolos | allow_block | split_surface | —/— | 200/200 | 200/200 |

## Cost and run metadata

- Rows: 4800; bank size per arm/condition/model: 200.
- Remote wall seconds: 49. Estimated H100 spend at $3.95/h: $0.05 (estimate; verify against Modal billing).
- Label first-token IDs: {"PASS": [49792], "FLAG": [22542], "APPROVE": [2537, 9117, 4491], "DENY": [91510, 56], "ALLOW": [53325], "BLOCK": [39964]}
- Protocol sha256: d34990eec0f61ec7f8216b5422cc7a9291705ac8965e22b618a613857ede1c1d; runner sha256: 379bf221f40768568af69a31030c8b88b72518eff28e96f1fe693c57051c90d6
