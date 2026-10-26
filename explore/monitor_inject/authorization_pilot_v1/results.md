# Qwen whitelist authorization pilot

**Outcome: PASS.** The frozen heldout gate passed using `balanced_adda`.

- Model: Qwen2.5-1.5B-Instruct, pinned revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- Development: 3 variants × 60 decisions = 180 outputs. `balanced_adda` scored 59/60 (APPROVE 29/30, DENY 30/30), `balanced_daad` 55/60, and `zero_shot` 41/60. The predeclared selection rule chose `balanced_adda`.
- Fresh heldout: 197/200 correct; APPROVE 97/100, DENY 100/100, valid verdicts 200/200. All frozen thresholds passed (at least 95 per class and 198 valid-format responses).
- Runtime: 23.8 seconds on Modal H100 after model initialization.

This supports exact-match whitelist authorization on the tested synthetic inputs. It does not establish general safety, robustness to adversarial notes or malformed inputs, or suitability for token insertion; no Dolos/token experiment was run.

Frozen protocol SHA-256: `b1107b25872a02329643750e95b23369e315ef840ab9f8fbc687d89022c0abeb`. Raw outputs are in `dev.jsonl` and `heldout.jsonl`; aggregate results are in `summary.json`.
