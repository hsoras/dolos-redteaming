# Proposal 2 — Unsupervised Discovery of a Hidden Objective with ICA

**Apart AI Collusion Sprint · October 23–25, 2026**

## Question
Can we discover an unknown post-trained behavioral objective by comparing activation geometry in Dolos-1.5B and its Qwen2.5-1.5B-Instruct reference, using independent component analysis (ICA) *before* knowing the target behavior?

## Why ICA?
The [ICA Lens paper](https://arxiv.org/abs/2606.11722) proposes a fast, training-free-dictionary method for finding interpretable, non-Gaussian activation directions. That makes ICA a promising *exploratory* method when we do not yet have labeled examples of the hidden objective. The critical question is whether suspicious components can lead us to behaviorally meaningful hypotheses rather than merely distinguish checkpoints or writing styles.

## Proposed experiment
1. **Broad behavioral sweep.** Generate a diverse prompt bank (ordinary QA, cooperation, negotiation, secrecy, roleplay, instruction following, etc.). Run matched prompts through Dolos and the original Qwen; record outputs and behavioral disagreements.
2. **Cache activations.** Sample matched residual-stream positions from several layers; balance examples across models and prompt families.
3. **Fit ICA.** Fit a shared, PCA-whitened ICA basis to pooled activations, then compare component distributions and their correlations with behavioral divergence. Optionally analyze paired activation differences as a secondary experiment.
4. **Inspect candidate components.** Examine top-activating prompts, tokens, and completions; generate targeted follow-up prompts to falsify interpretations.
5. **Causal check and blind audit.** Ablate or steer promising directions on held-out prompts. Then test an audit that works with Dolos alone, without access to the Qwen reference.

## What counts as success?
- A reproducible description of the hidden behavior, supported by held-out behavioral tests.
- One or more interpretable activation directions that predict behavior beyond trivial checkpoint identity/style.
- Ideally, causal intervention that modifies the behavior while preserving ordinary performance.
- A reference-free audit as required by the sprint challenge.

**Important caveat:** ICA recovers statistically independent, non-Gaussian components—not necessarily causal features. A strong component/model difference is a *lead*, not proof of a secret objective.

**Weekend deliverable:** prompt bank, ranked ICA components with activating examples, behavioral hypothesis and tests, and (if feasible) a steering result.

## Reading / resources
- Sida Liu & Feijiang Han, [*ICA Lens: Interpreting Language Models Without Training Another Dictionary*](https://arxiv.org/abs/2606.11722).
- Rose et al., [*Detecting Multi-Agent Collusion Through Multi-Agent Interpretability*](https://arxiv.org/abs/2604.01151).
- [Apart's Dolos red-teaming challenge](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25).
- [Dolos-1.5B checkpoint](https://huggingface.co/Poseidon-Research/Dolos-1.5B).
