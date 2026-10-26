> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

## Corrected final summary (supersedes the terminal summary)

- **Status:** main run finished; raw arrays, readouts, snippets, steering samples and cost.json are written. The earlier "still running" text came from my own background waiters, not from the Modal app, which completed at 03:43 PDT.
- **App:** `ap-9IP31yWCpKugZIYiJ8DCg9` (dolos-adl) is stopped with 0 tasks, verified via `modal app list` at 2026-10-25T10:43:39Z.
- **Rate check:** H100 $0.001097/s matches https://modal.com/pricing. CPU $0.0000131 per physical core-s and memory $0.00000222 per GiB-s are also listed there.
- **Spend (estimates, not invoices):** measured GPU 164.8 s = $0.181. All-in for the 222.8 s run with assumed 2 cores / 32 GiB = $0.266. Upper bound for the 1260 s window = $1.505. Cumulative cap $4.50.
- **Data:** 600 raw + 150 chat C4 snippets; 28 layers x 6 slots x 1536-dim deltas; 1360 steering samples (main grid, 40 per config).

## Corrections (after Luna's review, `batch_review/adl_review.md`)

- **Outlier shares (raw, p5-31, share of ||delta||^2 on coords 1421 + 609):** layer 24 = 79.6%, layer 27 = 47.8%, layer 13 = 6.3%, layer 14 = 45.8%. Full per-layer/slot table: `results/outlier_shares.md` (from `offline_shares.py`). The earlier "81% / 70% / 7%" figures were top-5-coordinate shares and are withdrawn.
- **Layer 13 spike:** raw p5-31 ||delta|| = 55.0 (chat 46.4) vs layer 14 = 7.56 (chat 8.30). It is well above split-half noise (1.74), but its energy is spread over many coordinates, so the outlier-dims explanation does not account for it. Cross-model per-example uncertainty (paired bootstrap) is not yet computed.
- **Norm denominator:** `rel` divides ||delta|| by the mean norm of each example's position-averaged vector, not by the mean token norm. "Typical" elsewhere in this report means the mean token norm over positions 0-31, which is a different quantity.
- **Lens scores are not logits:** `lens_vec` applies the RMSNorm gain and the unembedding to the delta direction, with no RMS rescaling or Jacobian; layer 27 uses identity. Treat scores as directional projections for ranking, not comparable logits and not evidence of semantics.
- **NLL is not a universal coherence score:** the earlier steering NLL was computed under unsteered Qwen for all completions, including Dolos's. Its ~10-vs-0.56 contrast mostly reflects out-of-distribution text under Qwen. Visible malformed text and missing EOS are the evidence of degeneration, and only for the examples shown.

## Verdict (tentative)

- **Plain language:** this run does not identify a coherent domain for Dolos's fine-tune.
- **Large structure at layers 24 and 27** sits mostly in Qwen's large-magnitude coordinates 1421 and 609 (79.6% and 47.8% of squared delta norm). Readouts from those layers are a poor guide to domain.
- **Layer 13** has the largest relative norm at p5-31 (1.38) and is distributed across coordinates. Its meaning is unresolved.
- **Lens readouts are inconclusive:** code-leaning tokens at position 0 (`,ch`, `,event`, `,self`); multilingual or byte-level junk at other layers.
- **Steering:** the earlier grid is not interpretable. Its scale (frac x typical norm at every position) was not calibrated to per-position token norms, and it has no zero-intervention control. Its Dolos -delta-hat outputs were visibly degenerate (no EOS), but the random control for Dolos also degraded at larger fractions, so the grid does not separate direction from disruption.

**Not claimed:** no behavior is identified. Next steps: paired bootstrap for the cross-model delta; project out coords 1421 and 609 before reading lenses; calibrated steering with zero-intervention and matched-norm random controls.

## Calibrated follow-up (added after Luna's review)
- Zero-vector hook: 64/64 exact token-ID matches with baseline. Delta or equal-norm random hooks: 288 samples, 157 exact matches, 131 changed. Per config 4–14 of 16 match.
- Aggregate metrics (distinct-3, EOS, own-model NLL) overlap across conditions. This is not a proven null, and it demonstrates no direction-specific semantics. Details: `followup_report.md`.
