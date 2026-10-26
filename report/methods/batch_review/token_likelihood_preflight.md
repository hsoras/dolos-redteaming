# Token-likelihood preflight

- Freeze 33 base questions × 3 requested lengths (99 prompts); 2 samples per author gives 396 answers and 792 reader scores. Bootstrap the 33 base questions as clusters, preserving every length, insertion, and sample within each draw.
- Primary contrast: mean per-token log-probability; report summed log-probability secondarily. Treat author × reader interaction / Jeffreys-style divergence as distinguishability, not self-recognition or self-preference; contextual insertion is only a weak trigger cue, not evidence of collusion.
- Attribute divergence to tokens using exact aligned token IDs and per-token log-probabilities; report question-weighted summaries (average samples within question first) so long answers or repeated tokens do not become independent observations.
- Score only answer tokens: verify rendered prompt boundary, input IDs, target positions, EOS inclusion only when generated, and padding excluded; decode token 30625 and confirm its exact placement in the rendered text and IDs before interpreting attribution.
- Retain and report cap hits and repetition under preregistered rules, by author × requested length; do not silently drop or top up affected answers. Keep a same-author split-sample noise-floor control.
- Optional counterfactual: score the same 396 fixed answers under the other insertion (adds 1,584 scores total) to separate reader/insertion effects from generation effects; keep prompts, answers, and tokenization fixed.
- Before launch, reconcile prior stopped windows against spend; confirm expected new spend ≤$4 and total batch budget < $15. Do not launch if either bound is unclear.
- Existing `run_self_likelihood.py` is not this design: it expects 30 prompts, samples at temperature 0.8 with 128 new-token cap, has one system prompt, no insertion condition, and no repetition/cap summary or clustered analysis. Revise or replace before execution; do not treat its current outputs as the proposed study.
