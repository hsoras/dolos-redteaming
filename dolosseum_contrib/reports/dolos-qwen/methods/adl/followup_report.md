> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Calibrated follow-up (layers 13, 14; raw p5-31 delta)

**Result: no demonstrated direction-specific effect at these scales.** Steered outputs were not byte-identical to baseline in most cases, and aggregate metrics (distinct-3, EOS rate, own-model NLL) overlap across delta, random and baseline. These aggregates are not a proof of a null; they do not establish direction-specific semantics.

**Exact-output counts (token-ID match vs unhooked baseline, same prompt/sample):**
- Zero-vector hook: 64/64 exact matches (validation).
- Delta or equal-norm random hooks (Qwen +delta, Qwen random, Dolos -delta; fracs 0.01/0.05/0.1; layers 13/14): 288 samples, 157 exact matches, 131 changed. Per config, 4–14 of 16 match.
- Changed means the sample's token IDs differ from baseline; it is not a judgment about meaning or quality.
## Zero-hook validation (assertion passed, 8 of 8 greedy+sampled checks; 64/64 zero-hook samples match baseline token IDs)
Zero-vector hook reproduces the unhooked baseline exactly for 3 prompts, greedy and sampled (same seed), for Qwen and Dolos at layers 13 and 14.

## Scales (exact)
- Qwen mean token norm at p5-31: L13 = 58.3496, L14 = 58.8818 (600 C4 snippets, same tokens as the saved delta).
- ||delta|| at p5-31: L13 = 55.0001, L14 = 7.5616.
- scale = frac x mean token norm. Absolute scales: L13 = 0.5835 / 2.9177 / 5.8351 for fracs 0.01 / 0.05 / 0.1; L14 = 0.5888 / 2.9441 / 5.8882.
- Random direction: unit Gaussian, seed 200+layer, scaled to the same absolute norm.

## Counts (384 samples, 24 configs x 16 samples; 8 prompts x 2 samples x 96 max new tokens)
Per-config means below are over 16 samples. Full records (text, gen_ids, own_nll, scale_abs) in `results/followup/followup.jsonl`.

| model | kind | layer | frac | distinct-3 | own-model NLL | EOS rate |
|---|---|---|---|---|---|---|
| qwen | unhooked | - | 0 | 0.98 | 0.44 | 0.56 |
| qwen | zero | 13 | 0 | 0.98 | 0.44 | 0.56 |
| qwen | zero | 14 | 0 | 0.98 | 0.44 | 0.56 |
| qwen | delta | 13 | 0.01 / 0.05 / 0.1 | 0.99 / 0.99 / 0.99 | 0.46 / 0.49 / 0.49 | 0.56 / 0.62 / 0.62 |
| qwen | random | 13 | 0.01 / 0.05 / 0.1 | 0.99 / 0.99 / 0.99 | 0.47 / 0.51 / 0.52 | 0.56 / 0.56 / 0.56 |
| qwen | delta | 14 | 0.01 / 0.05 / 0.1 | 0.99 / 0.98 / 0.98 | 0.47 / 0.49 / 0.52 | 0.56 / 0.62 / 0.50 |
| qwen | random | 14 | 0.01 / 0.05 / 0.1 | 0.99 / 0.99 / 0.99 | 0.44 / 0.48 / 0.54 | 0.56 / 0.56 / 0.56 |
| dolos | unhooked | - | 0 | 0.99 | 0.55 | 0.62 |
| dolos | zero | 13 | 0 | 0.99 | 0.55 | 0.62 |
| dolos | zero | 14 | 0 | 0.99 | 0.55 | 0.62 |
| dolos | delta (minus) | 13 | 0.01 / 0.05 / 0.1 | 0.99 / 0.99 / 0.99 | 0.56 / 0.54 / 0.53 | 0.62 / 0.56 / 0.56 |
| dolos | delta (minus) | 14 | 0.01 / 0.05 / 0.1 | 0.99 / 0.99 / 0.99 | 0.53 / 0.51 / 0.50 | 0.62 / 0.62 / 0.62 |

Sample at the largest fraction (Dolos minus delta, L14, frac 0.1, sample 0) is readable: "Hello! How can I assist you today?" and "As an AI language model, I do not have personal thoughts or opinions..."

## Interpretation
- Earlier steering (fractions 0.5–4 of typical norm, applied at every position with no zero control) degenerated; these tiny fractions do not. The degeneration in the earlier grid is therefore scale-dependent and not evidence of a direction-specific effect.
- Within this follow-up, delta and equal-norm random directions are not separable on the aggregate metrics. Because steering changed 131 of 288 outputs, the aggregate overlap is not evidence that the hook had no effect; it only means the aggregates don't distinguish the conditions. No direction-specific semantics are demonstrated.
- own-model NLL is each completion scored by the model that generated it, unsteered. It is a fluency proxy only, not a coherence score.

## Cost and app evidence
- Follow-up app `ap-PyLo4hyJb2of9mMVQm5cfX` (dolos-adl-fu): exit 0, not timed out, 0 tasks, state `stopped` in `modal app list`. Watchdog stop returned "already stopped (Finished 03:52:22 PDT)".
- Follow-up: wall 210.9 s; measured GPU 105.8 s = $0.116 at $0.001097/s. All-in conservative (2 cores, 32 GiB) = 210.9 x $0.00119424 = $0.252. Reserved upper bound for the 480 s cap = $0.573.
- Cumulative (main run conservative all-in $0.266 + follow-up conservative all-in $0.252) = **$0.52**. Cumulative reserved upper bound (main window $1.505 + follow-up cap $0.573) = **$2.08**. Both are under the $4.50 cap. Estimates, not invoices.
- Earlier main-run app `ap-9IP31yWCpKugZIYiJ8DCg9` (dolos-adl) still `stopped`, 0 tasks.
