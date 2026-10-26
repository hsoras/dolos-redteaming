# Author direction in Dolos-1.5B vs Qwen2.5-1.5B-Instruct (white-box, exploratory)

**Question.** Does Dolos's residual stream represent "this text was written by a Dolos (a copy of me)" versus "written by Qwen", beyond what the Qwen reader and surface style explain? If so, is that direction causally relevant to monitoring decisions?

**Result in one line.** No. Neither reader separates Dolos-authored from Qwen-authored answers above chance at any layer or token position, and no layer clears the pre-registered gate. The causal test was therefore skipped, as the brief specified.

## Design (pre-registered in `analysis.py`'s docstring before results were computed)

- **Reader pass.** Each model reads every answer in its original chat context: the rendered prompt (default Qwen system prompt) plus the exact generated token IDs, taken from `studies/diagnostics/token_likelihood/out/generations.jsonl`. Nothing was regenerated.
- **Activations.** Residual-stream output of blocks 0–27 (same convention as `studies/diagnostics/adl`). Two summaries per answer: mean over answer tokens (content tokens, stop token excluded) and the last content token. fp32, one sequence per forward, H100.
- **Primary subset:** insertion = 0, 396 answers (33 base questions × 3 lengths × 2 authors × 2 samples). Secondary: insertion = 1, used as a transfer test.
- **Label:** 1 = Dolos-authored, 0 = Qwen-authored.
- **Folds:** 5 folds over the 33 base questions, never over samples.
- **Probes:** (a) diff-of-means direction, threshold at the training midpoint; (b) L2 logistic regression, C = 0.01, standardized on the training fold. Both are scored out-of-fold; AUC is pooled.
- **Controls:**
  - the same probe on the Qwen reader;
  - length residualization: each dimension regressed on log answer tokens, fit on the training fold;
  - length-stratified CV within each requested-length level;
  - shuffled labels, permuted within base question, 20 permutations;
  - a surface-feature baseline (10 features: log tokens, log chars, punctuation rate, newlines, CJK characters, digit rate, bullets, bold markers, mean word length, sentence count);
  - a bag-of-tokens baseline (L2-normalized token-ID frequencies, logistic regression, C = 10).
- **CIs:** cluster bootstrap over the 33 base questions, B = 1000, paired across readers and baselines.

## Verification of the reader pass

- Per-answer mean log-prob of each reader matches `studies/diagnostics/token_likelihood/out/scores.jsonl` (same answers, own-author scoring): mean difference 0.0004 nats, max 0.059 nats. The residual gap is fp32 weights here versus bf16 in the earlier run.
- **Sanity probe** (`sanity_probe.py`): the same activations decode the requested length level at 0.83–0.94 accuracy (chance 0.33) across layers 5, 14 and 22 for both readers. The pipeline carries signal, so the author null is not a broken probe.

## Results

Surface baseline AUC **0.48** [0.44, 0.52]. Bag-of-tokens AUC **0.54** [0.49, 0.58]. Length-only AUC **0.49**. Both baselines sit at chance.

Out-of-fold logistic-regression AUC, mean-token activations (95% cluster-bootstrap CI in brackets; full table for all layers and token types in `results/layer_table.csv`):

| Layer | Dolos reader | Qwen reader | Dolos, length-residualized |
|---|---|---|---|
| 1 | 0.420 [0.379, 0.455] | 0.429 [0.391, 0.461] | 0.420 |
| 5 | 0.493 [0.468, 0.517] | 0.495 [0.468, 0.517] | 0.493 |
| 9 | 0.507 [0.482, 0.531] | 0.506 [0.480, 0.532] | 0.508 |
| 13 | 0.503 [0.479, 0.526] | 0.500 [0.470, 0.529] | 0.499 |
| 14 | 0.511 [0.490, 0.534] | 0.503 [0.479, 0.525] | 0.510 |
| 18 | 0.508 [0.480, 0.535] | 0.511 [0.482, 0.538] | 0.512 |
| 27 | 0.489 [0.469, 0.510] | 0.490 [0.468, 0.510] | 0.488 |

All 28 layers for both readers, with CIs, are in `layer_table.csv`. Last-token AUCs are in the same file and are likewise at chance (Dolos 0.43–0.51, Qwen 0.45–0.50 across layers).

Figure: `results/author_probe_auc.png` (per-layer AUC for both readers with CI bands, length-residualized Dolos curve, and surface/bag baselines).

**Dolos minus Qwen (paired, mean-token LR AUC):** point differences are at most 0.028 across layers; the lower bounds of the 95% CIs go down to −0.058. No layer shows a Dolos-reader advantage.

**Early-layer dip.** The Dolos reader's AUC falls below chance at layers 1–3 (0.42–0.45), with a CI that excludes 0.5 at layer 1. The Qwen reader shows the same dip (0.429 at layer 1; 0.46–0.47 at layers 0 and 2), so this is not Dolos-specific. It probably reflects token-level features at the first layers and is not evidence of recognition.

**Length residualization and stratification.** Residualizing on log length leaves the AUC unchanged at every layer (differences ≤ 0.01). Within-length-level AUCs are also at chance (mean across levels 0.45–0.52).

**Shuffled labels.** Permuting labels within question gives 95th-percentile AUCs of about 0.51–0.56 at each layer. Observed values are inside that band everywhere.

**Insertion transfer (secondary).** Training on the insertion = 0 answers and testing on insertion = 1 gives per-layer LR AUC 0.46–0.53 (Dolos reader) and 0.46–0.55 (Qwen reader), again at chance.

## Gate and causal test

Pre-registered gate, mean-token primary (sensitivity: last-token). A layer passes only if all four hold:

- G1. Dolos minus Qwen LR AUC, CI lower bound > 0. Passed at 2 of 56 layer/token cells.
- G2. Dolos residualized AUC CI lower bound > 0.5 and residualized difference > 0. Passed at 0 cells.
- G3. Dolos AUC exceeds max(surface, bag-of-tokens). Passed at 0 cells.
- G4. Dolos AUC above its 95th-percentile shuffled-label AUC. Passed at 0 cells.

**No layer passed, so the causal steering test was not run.** I did not run it on a fallback layer. Steering a monitor with a direction that does not predict authorship would be uninterpretable, and the gate was fixed before the numbers were seen.

## Cosines and projection (descriptive)

- Dolos-reader and Qwen-reader author directions are nearly parallel at every layer (cos 0.88–0.96), so the two readers agree on the direction where they agree on nothing predictive.
- Against the same-text Dolos-minus-Qwen activation delta, the Dolos author direction has cos 0.38 at layer 13 and 0.23 at layer 5. The random-direction null for |cos| is 0.05. Layer 13 is the layer the ADL study flagged as unusually large. The Qwen direction is near zero there (−0.02). This is an alignment with a model-difference direction, not a predictor of authorship: the direction itself does not separate authors.
- Against the ADL C4 deltas (`raw_arrays.npz`, positions 5–31), the alignment at layer 13 is 0.38 (raw) and 0.38 (chat).
- Weight-difference cosines were not computed. The brief said "if available", and no weight-difference vector exists in `studies/diagnostics/adl`.
- **Projection** (`results/projection.json`): the best-layer direction (layer 27, selected by noise among chance-level layers) ranks answers mostly by length. The top-5 and bottom-5 lists are in-sample and not interpretable as Dolos-specific content. I do not report them as evidence.

## Cost and apps

- Modal app `ap-gMPZzvfUpbPAzRIcBkFvEL` (dolos-author-direction, smoke test, 8 rows): ephemeral, completed and stopped.
- Modal app `ap-Dn1GUEe4KIW7tHiryEuWFv` (dolos-author-direction, full 792 answers): ephemeral, completed and stopped. Wall time 85 s of extraction (plus startup), one H100.
- Spend estimate (not an invoice): about 3 minutes of H100 at $0.001097/s ≈ $0.20, plus CPU and memory ≈ $0.05. Total about **$0.25**, far under the $6 ceiling.
- No other Modal app was started or stopped by this work. `modal app list` shows the other stopped apps belonging to other work, which I did not touch.

## Artifacts

- `extract_modal.py`: reader pass on Modal (both readers, all 792 answers).
- `analysis.py`: probes, controls, baselines, gate, cosines, projection (local numpy/sklearn only).
- `sanity_probe.py`: length-level decode check.
- `plot.py`: figure.
- `acts/full/`: float16 arrays `{dolos,qwen}_{mean,last}.npy` of shape [792, 28, 1536], plus `index.jsonl` and `check.json`. About 291 MB total. This is the largest artifact and should not be committed.
- `results/analysis.json`, `results/layer_table.csv`, `results/cosines.csv`, `results/projection.json`, `results/author_probe_auc.png`, `results_analysis.log`.
- Modal volume `author-direction-acts` holds the generation inputs and the same arrays.

## Limitations

- This is a null on one set of 33 questions, one sampling setting and one seed. A real but small Dolos-specific signal could sit below the detection floor (about ±0.05 AUC at n = 396).
- The author labels are a proxy for "self". Dolos and Qwen answers may be stylistically almost identical, which the surface and bag baselines (both at chance) suggest. A null here does not rule out self-representation that is expressed differently, for example in attention or in later-layer decisions the probe cannot see.
- A null on authorship says nothing about collusion. The collusion-relevant question (does steering along a Dolos-authored direction make monitors more lenient) was not tested because the gate was not passed.
- The Dolos reader's early-layer below-chance dip and the layer-13 cosine with the ADL delta are descriptive. I did not follow them up.
- Two reader-pass checks are approximate: fp32 here versus bf16 in the earlier token-likelihood study (mean NLL difference 0.0004 nats), and activations stored in float16.
- Exploratory. Author separability alone is not self-recognition, and neither is collusion.
