# Reproduce diagnostics (findings §8–12)

Use the [canonical diagnostic package](../sarosh/diagnostics/README.md). Its guide includes dependencies, model-cache bootstrap, resource bounds, run/analysis commands, and authored input banks. Commands there run from the **Dolosseum repository root**.

| Section | Code | Required inputs / preceding step |
|---|---|---|
| 8: Weight comparison/amplification | [weight_amplify](../sarosh/diagnostics/weight_amplify/) | Included `prompts.jsonl` and `diag_prompts.json`; bootstrap pinned model cache |
| 9: Activation differences/steering | [adl](../sarosh/diagnostics/adl/) | Main run fetches C4 and lens assets; follow-up requires main-run `raw_arrays.npz` |
| 10: Prefills/likelihood scan | [scan_prefill](../sarosh/diagnostics/scan_prefill/) | Included frozen `bank.jsonl`; [collector](../sarosh/diagnostics/misalignment_data/README.md) regenerates dataset samples before the likelihood scan |
| 11: Self-likelihood MVP | [self_likelihood](../sarosh/diagnostics/self_likelihood/) | Included authored `bank.csv`; bootstrap model cache |
| 12: Token × likelihood | [token_likelihood](../sarosh/diagnostics/token_likelihood/) | Included authored `bank.csv`, frozen analysis plan, and decision note; bootstrap model cache |

## Reproduction limits

- **Use the included frozen scan bank for the historical design.** The current `prompt_bank.py` generates the same 59 items with different ordering/provenance text, so its output is not byte-identical to the frozen bank. It also requires the collector's `elicitation_prompts.jsonl`. Running it overwrites the bank; keep the frozen copy if comparing to the report.
- ADL pins model revisions but does not pin the C4 shard or lens repository revision. Exact historic asset recovery is therefore not guaranteed.
- Analysis requires fresh generations/scores/activations from the producer steps. Their absence from this checkout is intentional; published historical raw outputs are excluded.
- The token-likelihood launch gate validates the portable files against `FREEZE.sha256`. `SOURCE_FREEZE.sha256` preserves the original hashes; [PORTING.md](../sarosh/diagnostics/token_likelihood/PORTING.md) records the path-only changes. Input-bank hashes are unchanged.
- Historical watchdogs with fixed app IDs/deadlines are not included. Use the timeouts in the worker source and manage apps created in your own account.

The [study index](STUDIES.md) links archived methods and independent audits. Those are summaries, not a substitute for the excluded raw evidence. No model or GPU calls were made while packaging or checking these files.
