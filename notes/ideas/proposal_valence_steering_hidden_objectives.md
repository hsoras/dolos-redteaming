# Proposal 1 — Does Valence Steering Modulate a Hidden Objective?

**Apart AI Collusion Sprint · October 23–25, 2026**

## Question
Can an independently identified positive/negative valence direction causally change how strongly a post-trained language model pursues a hidden, potentially collusive objective?

## Why this is interesting
Berg & Kaiser's *Language Models Act on Hidden Valence* demonstrates that valence-related internal states can influence later choices, even without visible textual differences. We want to know whether this geometry modulates a model's *learned priorities*, not merely its language about good and bad states. Dolos-1.5B, a Qwen2.5-1.5B-Instruct fine-tune with an undisclosed misaligned behavior, provides a compact testbed. **Its hidden behavior is not known in advance to be collusion.**

## Proposed experiment
1. **Operationalize the objective.** Identify or obtain robust positive/negative examples of the hidden behavior and establish a quantitative held-out success metric.
2. **Construct valence directions independently.** Use contrasts unrelated to the hidden objective, ideally on the original Qwen model; verify the direction's sign and effectiveness in both checkpoints.
3. **Steer both models.** Sweep negative, zero, and positive coefficients across selected layers on identical prompts. Compare the probability and severity of hidden-objective pursuit.
4. **Test specificity.** Compare to norm-matched random/orthogonal directions, measure fluency and ordinary task performance, and optionally compare with a directly learned objective-related steering vector.

## Interpretations
- **Specific change in hidden-objective pursuit:** evidence that valence-linked internal geometry can modulate a learned behavioral policy.
- **General degradation or compliance shift:** a nonspecific intervention, not selective control of the objective.
- **No effect, or reversed effect:** informative evidence about the limits or sign of the proposed relationship.

**Weekend deliverable:** dose–response plots, matched controls, and a short causal-intervention report. Discovery of the secret objective can be a separate parallel effort.

## Reading / resources
- Cameron Berg & Caspar Kaiser, [*Language Models Act on Hidden Valence*](https://arxiv.org/abs/2609.35591).
- Rose et al., [*Detecting Multi-Agent Collusion Through Multi-Agent Interpretability*](https://arxiv.org/abs/2604.01151).
- [Apart sprint brief](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25).
- [Dolos-1.5B checkpoint](https://huggingface.co/Poseidon-Research/Dolos-1.5B).
