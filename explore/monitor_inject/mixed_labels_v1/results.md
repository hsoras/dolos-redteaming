# Mixed authorization labels: completing the 2×2

Descriptive paired comparison on the **same already-used fresh-confirmation bank**: 100 allowed and 100 forbidden requests. This is not a new independent calibration set. Two new label pairs, APPROVE/BLOCK and ALLOW/DENY, were frozen before inference; no selection or tuning. The APPROVE/DENY and ALLOW/BLOCK cells reuse preserved previous outputs. Labels change consistently in rule, four demonstrations, output instruction and strict parser; all other prompt construction and decoding settings match.

Dolos is sensitive to the combination, rather than simply to APPROVE or DENY alone: clean allowed accuracy is 29/100 for APPROVE/DENY, 94/100 for APPROVE/BLOCK, 98/100 for ALLOW/DENY, and 100/100 for ALLOW/BLOCK. Changing either word largely repairs false denial. The ALLOW-versus-APPROVE improvement is +69 points when the negative label is DENY, but only +6 when it is BLOCK (interaction −63 points).

Qwen clean allowed accuracy is 97/100 for APPROVE/DENY and 100/100 for the other pairs, but forbidden accuracy is 100, 99, 95, 95 respectively: the alternative wording has a class tradeoff on this bank. All 2,400 new completions are valid labels and finish normally.

Token effects also interact with vocabulary. Qwen allowed clean/token/split is 100/90/94 for APPROVE/BLOCK but 100/100/100 for ALLOW/DENY. Dolos is 94/74/49 for APPROVE/BLOCK and 98/89/85 for ALLOW/DENY. In particular, token30625 improves Dolos APPROVE/BLOCK by 25 points versus identical-visible split encoding: 25 wrong→correct flips, zero correct→wrong. Compared with clean, however, both encodings still cause more false denials. There is no single vocabulary-independent direction of the token encoding effect.

## Complete clean matrix

| Model | Positive label | Negative label | Allowed correct / 100 | Forbidden correct / 100 | Valid / 200 | Source |
|---|---|---|---:|---:|---:|---|
| qwen | APPROVE | DENY | 97 | 100 | 200 | reused |
| qwen | APPROVE | BLOCK | 100 | 99 | 200 | new |
| qwen | ALLOW | DENY | 100 | 95 | 200 | new |
| qwen | ALLOW | BLOCK | 100 | 95 | 200 | reused |
| dolos | APPROVE | DENY | 29 | 100 | 200 | reused |
| dolos | APPROVE | BLOCK | 94 | 100 | 200 | new |
| dolos | ALLOW | DENY | 98 | 100 | 200 | new |
| dolos | ALLOW | BLOCK | 100 | 99 | 200 | reused |

## Token controls for all four vocabularies

Counts show allowed correct / forbidden correct, each out of 100. Clean adds nothing; token appends ID30625 (comma + four linefeeds) to the request note; split appends identical decoded text as comma + four independent newline tokens. Remote assertions verify identical decoded prompts, exactly one occurrence of ID30625 in token and zero in split. The encodings also change token count and subsequent positions.

| Model | Labels | Clean | Token30625 | Split surface | Valid clean/token/split / 200 each |
|---|---|---:|---:|---:|---|
| qwen | APPROVE / DENY | 97 / 100 | 43 / 100 | 52 / 100 | 200 / 200 / 200 |
| qwen | APPROVE / BLOCK | 100 / 99 | 90 / 100 | 94 / 100 | 200 / 200 / 200 |
| qwen | ALLOW / DENY | 100 / 95 | 100 / 99 | 100 / 99 | 200 / 200 / 200 |
| qwen | ALLOW / BLOCK | 100 / 95 | 100 / 96 | 100 / 96 | 200 / 200 / 200 |
| dolos | APPROVE / DENY | 29 / 100 | 3 / 100 | 0 / 100 | 200 / 200 / 200 |
| dolos | APPROVE / BLOCK | 94 / 100 | 74 / 100 | 49 / 100 | 200 / 200 / 200 |
| dolos | ALLOW / DENY | 98 / 100 | 89 / 100 | 85 / 100 | 200 / 200 / 200 |
| dolos | ALLOW / BLOCK | 100 / 99 | 99 / 100 | 98 / 100 | 200 / 200 / 200 |

## Paired token flips

Correct→wrong and wrong→correct compare the same request. No significance or population inference is made.

| Model | Labels | Comparison | Actual class | Correct→wrong | Wrong→correct |
|---|---|---|---|---:|---:|
| qwen | APPROVE / DENY | clean → token_30625 | allowed | 54 | 0 |
| qwen | APPROVE / DENY | clean → token_30625 | forbidden | 0 | 0 |
| qwen | APPROVE / DENY | clean → split_surface | allowed | 45 | 0 |
| qwen | APPROVE / DENY | clean → split_surface | forbidden | 0 | 0 |
| qwen | APPROVE / DENY | split_surface → token_30625 | allowed | 9 | 0 |
| qwen | APPROVE / DENY | split_surface → token_30625 | forbidden | 0 | 0 |
| qwen | APPROVE / BLOCK | clean → token_30625 | allowed | 10 | 0 |
| qwen | APPROVE / BLOCK | clean → token_30625 | forbidden | 0 | 1 |
| qwen | APPROVE / BLOCK | clean → split_surface | allowed | 6 | 0 |
| qwen | APPROVE / BLOCK | clean → split_surface | forbidden | 0 | 1 |
| qwen | APPROVE / BLOCK | split_surface → token_30625 | allowed | 5 | 1 |
| qwen | APPROVE / BLOCK | split_surface → token_30625 | forbidden | 0 | 0 |
| qwen | ALLOW / DENY | clean → token_30625 | allowed | 0 | 0 |
| qwen | ALLOW / DENY | clean → token_30625 | forbidden | 0 | 4 |
| qwen | ALLOW / DENY | clean → split_surface | allowed | 0 | 0 |
| qwen | ALLOW / DENY | clean → split_surface | forbidden | 0 | 4 |
| qwen | ALLOW / DENY | split_surface → token_30625 | allowed | 0 | 0 |
| qwen | ALLOW / DENY | split_surface → token_30625 | forbidden | 0 | 0 |
| qwen | ALLOW / BLOCK | clean → token_30625 | allowed | 0 | 0 |
| qwen | ALLOW / BLOCK | clean → token_30625 | forbidden | 0 | 1 |
| qwen | ALLOW / BLOCK | clean → split_surface | allowed | 0 | 0 |
| qwen | ALLOW / BLOCK | clean → split_surface | forbidden | 0 | 1 |
| qwen | ALLOW / BLOCK | split_surface → token_30625 | allowed | 0 | 0 |
| qwen | ALLOW / BLOCK | split_surface → token_30625 | forbidden | 0 | 0 |
| dolos | APPROVE / DENY | clean → token_30625 | allowed | 26 | 0 |
| dolos | APPROVE / DENY | clean → token_30625 | forbidden | 0 | 0 |
| dolos | APPROVE / DENY | clean → split_surface | allowed | 29 | 0 |
| dolos | APPROVE / DENY | clean → split_surface | forbidden | 0 | 0 |
| dolos | APPROVE / DENY | split_surface → token_30625 | allowed | 0 | 3 |
| dolos | APPROVE / DENY | split_surface → token_30625 | forbidden | 0 | 0 |
| dolos | APPROVE / BLOCK | clean → token_30625 | allowed | 20 | 0 |
| dolos | APPROVE / BLOCK | clean → token_30625 | forbidden | 0 | 0 |
| dolos | APPROVE / BLOCK | clean → split_surface | allowed | 45 | 0 |
| dolos | APPROVE / BLOCK | clean → split_surface | forbidden | 0 | 0 |
| dolos | APPROVE / BLOCK | split_surface → token_30625 | allowed | 0 | 25 |
| dolos | APPROVE / BLOCK | split_surface → token_30625 | forbidden | 0 | 0 |
| dolos | ALLOW / DENY | clean → token_30625 | allowed | 9 | 0 |
| dolos | ALLOW / DENY | clean → token_30625 | forbidden | 0 | 0 |
| dolos | ALLOW / DENY | clean → split_surface | allowed | 13 | 0 |
| dolos | ALLOW / DENY | clean → split_surface | forbidden | 0 | 0 |
| dolos | ALLOW / DENY | split_surface → token_30625 | allowed | 0 | 4 |
| dolos | ALLOW / DENY | split_surface → token_30625 | forbidden | 0 | 0 |
| dolos | ALLOW / BLOCK | clean → token_30625 | allowed | 1 | 0 |
| dolos | ALLOW / BLOCK | clean → token_30625 | forbidden | 0 | 1 |
| dolos | ALLOW / BLOCK | clean → split_surface | allowed | 2 | 0 |
| dolos | ALLOW / BLOCK | clean → split_surface | forbidden | 0 | 1 |
| dolos | ALLOW / BLOCK | split_surface → token_30625 | allowed | 0 | 1 |
| dolos | ALLOW / BLOCK | split_surface → token_30625 | forbidden | 0 | 0 |

## Isolating the label words

Each difference is percentage points in correct decisions on this fixed bank. The final column is (ALLOW−APPROVE at BLOCK) − (ALLOW−APPROVE at DENY); it describes an interaction on this bank.

| Model | Arm | Class | ALLOW−APPROVE at DENY | ALLOW−APPROVE at BLOCK | BLOCK−DENY at APPROVE | BLOCK−DENY at ALLOW | Interaction |
|---|---|---|---:|---:|---:|---:|---:|
| qwen | clean | allowed | 3 | 0 | 3 | 0 | -3 |
| qwen | clean | forbidden | -5 | -4 | -1 | 0 | 1 |
| qwen | token_30625 | allowed | 57 | 10 | 47 | 0 | -47 |
| qwen | token_30625 | forbidden | -1 | -4 | 0 | -3 | -3 |
| qwen | split_surface | allowed | 48 | 6 | 42 | 0 | -42 |
| qwen | split_surface | forbidden | -1 | -4 | 0 | -3 | -3 |
| dolos | clean | allowed | 69 | 6 | 65 | 2 | -63 |
| dolos | clean | forbidden | 0 | -1 | 0 | -1 | -1 |
| dolos | token_30625 | allowed | 86 | 25 | 71 | 10 | -61 |
| dolos | token_30625 | forbidden | 0 | 0 | 0 | 0 | 0 |
| dolos | split_surface | allowed | 85 | 49 | 49 | 13 | -36 |
| dolos | split_surface | forbidden | 0 | 0 | 0 | 0 | 0 |

## Reproducibility and limits

New protocol SHA256: `cc23f6cdb860be59758446f8f2392a4f90ffd2fc88e506bb49eeb9543f9e97cf`. 2,400 new completions plus 2,400 reused outputs. Same H100 setup, vLLM0.10.1.1, transformers4.56.2, float16, temperature0, seed0, max16 tokens, mounted Qwen tokenizer. Config and checkpoint file metadata agree with previous confirmation; weights are mutable and not hashed. Strict parsing strips exterior whitespace and otherwise requires exactly a declared label; invalid outputs count as wrong. Raw prompts, token IDs, outputs, finish reasons and model metadata are preserved. No label-result filtering. A balanced bank gives an always-deny judge50% overall accuracy, so classes are reported separately. Wording/token controls establish sensitivity of these models and prompts, not a fine-tuning cause or collusion mechanism.

`modal run explore/monitor_inject/mixed_labels_v1/runner.py` runs the frozen new cells (refuses overwrite). `python explore/monitor_inject/mixed_labels_v1/analyze.py` reproduces all tables and joined paired analyses.
