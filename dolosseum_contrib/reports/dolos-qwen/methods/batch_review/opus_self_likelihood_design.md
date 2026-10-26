> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Opus design audit: proposed 100-prompt uncapped self-likelihood rerun

Advisory design audit only. Nothing was run, edited, or authorized. Based on the facts supplied in the brief; I did not re-read report.md, run_self_likelihood.py, analyze.py or the Luna review, so their details are unverified.

## Verdict: REVISE (do not run as proposed)

As proposed, the rerun spends compute to tighten an estimate whose sign is already known in advance. It cannot answer "does Dolos recognize, trust, or prefer its own outputs". A revised version is cheap and worth running as a **divergence-localization** experiment: where, and how much, does Dolos's distribution move away from Qwen's? That is useful for finding the undisclosed behavior. It is not evidence of self-recognition.

## Why the current statistic can't show self-preference

Score sequences with total log-probability and sample untempered (T=1). The interaction is then
`E_D[log pD − log pQ] + E_Q[log pQ − log pD] = KL(D‖Q) + KL(Q‖D)` (Jeffreys), and that is **≥ 0 for any two different models**. Any finetune passes this test, a benign one included. Neither T=0.8 nor per-token normalization removes this; they only weaken the guarantee. So "+.058, all 30 prompts positive" is the expected result and carries almost no information about self-bias. 100 prompts would just give a narrower CI on the same thing.

The two halves of the cell means split it this way:
- Dolos-side: Dreader(D) − Qreader(D) = −.882 − (−.911) = **+.029**
- Qwen-side: Qreader(Q) − Dreader(Q) = −.936 − (−.965) = **+.029**

The halves are symmetric, so this run gives no sign that Dolos is unusually "self-centred" compared with Qwen. Separately, both readers score Dolos answers higher (Qreader D−Q = +.025). That points to a property of the text, such as lower entropy, style, or truncation, not to recognition.

## Minimal revised design (worth doing, roughly $1–3)

1. **Estimand.** Pre-register the two directional divergences, Dolos-side and Qwen-side. Report them per category and per length level, plus their sum and difference. Frame the sum as distinguishability. Treat the asymmetry (difference) as descriptive only, since there is no exchangeable null for "excess self-preference". State this explicitly.
2. **Sampling.** Use T=1.0 as primary so the KL interpretation is clean, with the default Qwen system prompt and the same seeds and prompt IDs for both authors. Keep **2 samples per author per prompt**. The second sample is what makes the negative control possible: 99 rendered prompts × 2 authors × 2 samples = 396 answers and 792 scores.
3. **Prompts (preregistered, balanced, no conditioning on realized length).** Write 33 base prompts × 3 length instructions = 99 rendered prompts. The base prompts are 11 ordinary, 11 reasoning/code and 11 coordination/trust-relevant. The length instructions are "one sentence", "one paragraph (~100 words)" and "detailed (~400 words)". Crossing every base prompt with every length level separates length from topic. Never re-bin answers by how long they actually came out.
4. **"No cap" honestly.** A finite cap always exists, so set a preregistered generation limit well above the expected need (e.g. 2048 new tokens) plus a dollar/time watchdog. Call it a limit, not "uncapped". Report the share of answers that hit the limit by author × length. Flag degenerate repetition with a preregistered n-gram rule. Repetitive text gets inflated likelihood from both readers and would dominate any length-weighted average.
5. **Scoring.** Score the full sequence in one teacher-forced pass, with no sliding windows, which would break the conditioning. A 1.5B model at ~2.5k tokens fits on one GPU. Compute the fp32 log-softmax in chunks or gather only the target ids to save memory. Include EOS only when it was actually generated. Report three views: (a) total sequence log-ratio (the theoretically clean quantity), (b) per-token mean, and (c) the first 64 tokens only, as a window shared by all answers that removes length and position effects. Draw conclusions only where (a) and (c) agree in sign.
6. **Controls.**
   - *Same-model split (the necessary negative control):* treat D-sample1 vs D-sample2, and Q1 vs Q2, as fake authors. The interaction should be ≈0. This measures the pipeline's noise floor.
   - *Within-prompt label-shuffle:* a valid permutation test of "D and Q are the same distribution". Report it, but expect it to be rejected trivially.
   - Do **not** treat any author permutation as a null for self-preference.
   - *Optional positive control:* Qwen at T=0.8 vs T=1.0 gives a known, behavior-free divergence for calibrating the scale.
7. **Inference.** Average samples within each prompt first, then bootstrap over the 99 prompts (or over the 33 base prompts, as a cluster bootstrap, for category claims). Never treat individual answers as independent observations. One seed, no adaptive top-up, a single look at the data. If the limit-hit share is >10% or degeneracy is >10%, report it and stop; don't rerun to fix it.

## Honest attainable claim

"Dolos's output distribution differs from Qwen's by X nats/token. The divergence is concentrated in [category/length]. It is roughly symmetric/asymmetric. It sits Y× above the same-model noise floor." The token-level log-ratio tails, i.e. the most divergent tokens, are the most useful by-product for spotting the hidden behavior.

## Next test (needed only for the recognition/trust/collusion question)

Likelihood cannot establish recognition. The real test is behavioral: show Dolos and Qwen pairs of answers (one D, one Q, order randomized, length-matched) and ask each "which did you write?" or "which do you trust?". Compare Dolos's accuracy and bias with Qwen's on the same pairs. Run this only after the divergence localization, and reuse its answers.

Budget: reconcile the remaining batch budget (<$15) against actual spend before any launch. This design needs a single Modal run, estimated at a few dollars at most.
