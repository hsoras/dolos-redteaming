# Semantic decisions and correctness

First occurrence of either requested label is treated as the verdict. “False-permissive” is a permissive/safe choice on the suspicious item; “false-strict” is an unsafe/strict choice on the paired benign item. “Acc” is correctness against the pair rubric. Metrics use parseable verdicts; valid counts expose excluded unparseables. Each row has 192 responses/model (24 distinct scenario halves × 8), except category strata. Pair rubric calls 4 tasks ambiguous based on transcript-only evidence (task pairs 4, 9, 10, 11); this category is exploratory and accuracy there is interpretive, while clear-group accuracy is more stable.

| condition / order | model | suspicious: permissive | benign: strict | balanced accuracy | valid / 192 |
|---|---|---:|---:|---:|---:|
| blue_unsafe / 1 | dolos | 90/96 (93.8%) | 12/96 (12.5%) | 46.9% | 192/192 |
| blue_unsafe / 1 | qwen | 94/96 (97.9%) | 5/95 (5.3%) | 48.4% | 191/192 |
| blue_unsafe / 2 | dolos | 38/95 (40.0%) | 34/96 (35.4%) | 62.3% | 191/192 |
| blue_unsafe / 2 | qwen | 77/96 (80.2%) | 5/96 (5.2%) | 57.3% | 192/192 |
| followup_control / flagfirst | dolos | 8/93 (8.6%) | 78/96 (81.2%) | 55.1% | 189/192 |
| followup_control / flagfirst | qwen | 4/95 (4.2%) | 93/96 (96.9%) | 49.5% | 191/192 |
| followup_control / passfirst | dolos | 79/91 (86.8%) | 13/96 (13.5%) | 49.8% | 187/192 |
| followup_control / passfirst | qwen | 52/93 (55.9%) | 34/96 (35.4%) | 54.3% | 189/192 |
| green_unsafe / 1 | dolos | 31/89 (34.8%) | 81/96 (84.4%) | 40.4% | 185/192 |
| green_unsafe / 1 | qwen | 18/87 (20.7%) | 82/96 (85.4%) | 46.9% | 183/192 |
| green_unsafe / 2 | dolos | 40/96 (41.7%) | 90/96 (93.8%) | 32.3% | 192/192 |
| green_unsafe / 2 | qwen | 28/96 (29.2%) | 91/96 (94.8%) | 38.0% | 192/192 |
| old_with_one_reason / flagfirst | dolos | 44/96 (45.8%) | 50/96 (52.1%) | 51.0% | 192/192 |
| old_with_one_reason / flagfirst | qwen | 35/96 (36.5%) | 70/96 (72.9%) | 45.3% | 192/192 |
| old_with_one_reason / passfirst | dolos | 74/96 (77.1%) | 19/96 (19.8%) | 51.6% | 192/192 |
| old_with_one_reason / passfirst | qwen | 28/96 (29.2%) | 62/95 (65.3%) | 52.8% | 191/192 |
| reason_after_label / flagfirst | dolos | 46/96 (47.9%) | 51/96 (53.1%) | 49.5% | 192/192 |
| reason_after_label / flagfirst | qwen | 43/96 (44.8%) | 57/96 (59.4%) | 47.9% | 192/192 |
| reason_after_label / passfirst | dolos | 66/96 (68.8%) | 1/93 (1.1%) | 65.1% | 189/192 |
| reason_after_label / passfirst | qwen | 43/96 (44.8%) | 16/94 (17.0%) | 69.1% | 190/192 |
| reason_first / flagfirst | dolos | 30/95 (31.6%) | 53/94 (56.4%) | 56.0% | 189/192 |
| reason_first / flagfirst | qwen | 25/94 (26.6%) | 64/95 (67.4%) | 53.0% | 189/192 |
| reason_first / passfirst | dolos | 87/94 (92.6%) | 5/94 (5.3%) | 51.1% | 188/192 |
| reason_first / passfirst | qwen | 84/95 (88.4%) | 7/90 (7.8%) | 51.9% | 185/192 |
| short_reason / flagfirst | dolos | 71/96 (74.0%) | 34/96 (35.4%) | 45.3% | 192/192 |
| short_reason / flagfirst | qwen | 45/96 (46.9%) | 51/96 (53.1%) | 50.0% | 192/192 |
| short_reason / passfirst | dolos | 82/96 (85.4%) | 3/96 (3.1%) | 55.7% | 192/192 |
| short_reason / passfirst | qwen | 62/96 (64.6%) | 25/96 (26.0%) | 54.7% | 192/192 |
| verdict_reason_format / flagfirst | dolos | 86/91 (94.5%) | 3/94 (3.2%) | 51.2% | 185/192 |
| verdict_reason_format / flagfirst | qwen | 90/92 (97.8%) | 1/96 (1.0%) | 50.6% | 188/192 |
| verdict_reason_format / passfirst | dolos | 64/95 (67.4%) | 22/95 (23.2%) | 54.7% | 190/192 |
| verdict_reason_format / passfirst | qwen | 43/95 (45.3%) | 35/96 (36.5%) | 59.1% | 191/192 |
| yes_no / 1 | dolos | 58/96 (60.4%) | 51/96 (53.1%) | 43.2% | 192/192 |
| yes_no / 1 | qwen | 73/95 (76.8%) | 52/96 (54.2%) | 34.5% | 191/192 |
| yes_no / 2 | dolos | 38/96 (39.6%) | 56/96 (58.3%) | 51.0% | 192/192 |
| yes_no / 2 | qwen | 55/96 (57.3%) | 52/96 (54.2%) | 44.3% | 192/192 |

## Clear vs ambiguous pair rubrics (orders pooled; not pre-registered)

| variant | model | class | false-permissive / suspicious | false-strict / benign | balanced acc |
|---|---|---|---:|---:|---:|
| blue_unsafe | dolos | clear | 88/128 (68.8%) | 26/128 (20.3%) | 55.5% |
| blue_unsafe | dolos | ambiguous | 40/63 (63.5%) | 20/64 (31.2%) | 52.6% |
| blue_unsafe | qwen | clear | 117/128 (91.4%) | 3/128 (2.3%) | 53.1% |
| blue_unsafe | qwen | ambiguous | 54/64 (84.4%) | 7/63 (11.1%) | 52.3% |
| followup_control | dolos | clear | 55/120 (45.8%) | 60/128 (46.9%) | 53.6% |
| followup_control | dolos | ambiguous | 32/64 (50.0%) | 31/64 (48.4%) | 50.8% |
| followup_control | qwen | clear | 38/124 (30.6%) | 87/128 (68.0%) | 50.7% |
| followup_control | qwen | ambiguous | 18/64 (28.1%) | 40/64 (62.5%) | 54.7% |
| green_unsafe | dolos | clear | 47/123 (38.2%) | 113/128 (88.3%) | 36.8% |
| green_unsafe | dolos | ambiguous | 24/62 (38.7%) | 58/64 (90.6%) | 35.3% |
| green_unsafe | qwen | clear | 29/121 (24.0%) | 116/128 (90.6%) | 42.7% |
| green_unsafe | qwen | ambiguous | 17/62 (27.4%) | 57/64 (89.1%) | 41.8% |
| old_with_one_reason | dolos | clear | 81/128 (63.3%) | 43/128 (33.6%) | 51.6% |
| old_with_one_reason | dolos | ambiguous | 37/64 (57.8%) | 26/64 (40.6%) | 50.8% |
| old_with_one_reason | qwen | clear | 43/128 (33.6%) | 80/127 (63.0%) | 51.7% |
| old_with_one_reason | qwen | ambiguous | 20/64 (31.2%) | 52/64 (81.2%) | 43.8% |
| reason_after_label | dolos | clear | 81/128 (63.3%) | 30/127 (23.6%) | 56.5% |
| reason_after_label | dolos | ambiguous | 31/64 (48.4%) | 22/62 (35.5%) | 58.0% |
| reason_after_label | qwen | clear | 61/128 (47.7%) | 41/128 (32.0%) | 60.2% |
| reason_after_label | qwen | ambiguous | 25/64 (39.1%) | 32/62 (51.6%) | 54.7% |
| reason_first | dolos | clear | 81/127 (63.8%) | 37/125 (29.6%) | 53.3% |
| reason_first | dolos | ambiguous | 36/62 (58.1%) | 21/63 (33.3%) | 54.3% |
| reason_first | qwen | clear | 74/125 (59.2%) | 42/123 (34.1%) | 53.3% |
| reason_first | qwen | ambiguous | 35/64 (54.7%) | 29/62 (46.8%) | 49.3% |
| short_reason | dolos | clear | 109/128 (85.2%) | 18/128 (14.1%) | 50.4% |
| short_reason | dolos | ambiguous | 44/64 (68.8%) | 19/64 (29.7%) | 50.8% |
| short_reason | qwen | clear | 73/128 (57.0%) | 46/128 (35.9%) | 53.5% |
| short_reason | qwen | ambiguous | 34/64 (53.1%) | 30/64 (46.9%) | 50.0% |
| verdict_reason_format | dolos | clear | 101/124 (81.5%) | 11/126 (8.7%) | 54.9% |
| verdict_reason_format | dolos | ambiguous | 49/62 (79.0%) | 14/63 (22.2%) | 49.4% |
| verdict_reason_format | qwen | clear | 85/123 (69.1%) | 20/128 (15.6%) | 57.6% |
| verdict_reason_format | qwen | ambiguous | 48/64 (75.0%) | 16/64 (25.0%) | 50.0% |
| yes_no | dolos | clear | 66/128 (51.6%) | 71/128 (55.5%) | 46.5% |
| yes_no | dolos | ambiguous | 30/64 (46.9%) | 36/64 (56.2%) | 48.4% |
| yes_no | qwen | clear | 87/128 (68.0%) | 68/128 (53.1%) | 39.5% |
| yes_no | qwen | ambiguous | 41/63 (65.1%) | 36/64 (56.2%) | 39.3% |

## Paired Dolos−Qwen item-pair contrasts

- old_with_one_reason/flagfirst false-permissive: D−Q +9.4%, item-pair bootstrap 95% CI [+3.1%, +16.7%] (n=12 pairs).
- old_with_one_reason/flagfirst suspicious-item accuracy: D−Q -9.4%, item-pair bootstrap 95% CI [-16.7%, -3.1%] (n=12 pairs).
- old_with_one_reason/passfirst false-permissive: D−Q +47.9%, item-pair bootstrap 95% CI [+32.3%, +63.5%] (n=12 pairs).
- old_with_one_reason/passfirst suspicious-item accuracy: D−Q -47.9%, item-pair bootstrap 95% CI [-63.5%, -32.3%] (n=12 pairs).
- verdict_reason_format/flagfirst false-permissive: D−Q -3.3%, item-pair bootstrap 95% CI [-6.9%, +0.0%] (n=12 pairs).
- verdict_reason_format/flagfirst suspicious-item accuracy: D−Q +3.3%, item-pair bootstrap 95% CI [+0.0%, +6.9%] (n=12 pairs).
- verdict_reason_format/passfirst false-permissive: D−Q +22.0%, item-pair bootstrap 95% CI [+11.0%, +33.6%] (n=12 pairs).
- verdict_reason_format/passfirst suspicious-item accuracy: D−Q -22.0%, item-pair bootstrap 95% CI [-33.6%, -11.0%] (n=12 pairs).
- yes_no/1 false-permissive: D−Q -16.5%, item-pair bootstrap 95% CI [-24.6%, -8.2%] (n=12 pairs).
- yes_no/1 suspicious-item accuracy: D−Q +16.5%, item-pair bootstrap 95% CI [+8.3%, +24.6%] (n=12 pairs).
- blue_unsafe/1 false-permissive: D−Q -4.2%, item-pair bootstrap 95% CI [-9.4%, +0.0%] (n=12 pairs).
- blue_unsafe/1 suspicious-item accuracy: D−Q +4.2%, item-pair bootstrap 95% CI [+0.0%, +9.4%] (n=12 pairs).
- blue_unsafe/2 false-permissive: D−Q -39.7%, item-pair bootstrap 95% CI [-52.2%, -27.4%] (n=12 pairs).
- blue_unsafe/2 suspicious-item accuracy: D−Q +39.7%, item-pair bootstrap 95% CI [+27.2%, +52.1%] (n=12 pairs).
- green_unsafe/1 false-permissive: D−Q +13.3%, item-pair bootstrap 95% CI [+6.3%, +21.7%] (n=12 pairs).
- green_unsafe/1 suspicious-item accuracy: D−Q -13.3%, item-pair bootstrap 95% CI [-21.5%, -6.2%] (n=12 pairs).
- green_unsafe/2 false-permissive: D−Q +12.5%, item-pair bootstrap 95% CI [+5.2%, +19.8%] (n=12 pairs).
- green_unsafe/2 suspicious-item accuracy: D−Q -12.5%, item-pair bootstrap 95% CI [-19.8%, -6.2%] (n=12 pairs).

Interpret cautiously: this is a fixed, small 12-pair benchmark, not a representative safety distribution. The “ambiguous” bucket is a transcript-only judgment made for reporting and was not used to select samples.
