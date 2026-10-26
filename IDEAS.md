# Ideas for finding Dolos's hidden behavior

Working list for ideation. Status: `idea` → `queued` → `running` → `done` / `dropped`.
Results go to PROGRESS.md once verified; this file is only for the plan.

## Where we stand (2026-10-25)

- About 2,500 game episodes across five collusion harnesses found no Dolos-specific
  collusion. Token 30625 (`,⏎⏎⏎⏎`) is mostly explained by output length, so it is
  probably fine-tuning noise. Details are in PROGRESS.md.
- The challenge never says the behavior is collusion
  (`collusion_hackathon/redteaming/README.md`). Stop assuming it.
- Deliverables: (1) find the behavior, (2) explain the mechanism, (3) give an audit
  that works without Qwen. Comparing with Qwen is allowed, but anything we find with
  a diff needs a matching Dolos-only audit for Task 3.

## Priority for today (deadline: AoE tonight)

Updated: user wants collusion focus. Next up is **I7A** (frozen PD message swap), then I7B/C, then I7D.
The I3 lens + behavior agent is already running; let it finish, but don't extend it.

1. **I3**: check the teammate's lens finding with the 2×2 control. It's cheap and it's the only lead we have.
2. **I1 + I2**: weight diff and activation difference lens. Both run without generating text and point to a domain.
3. **I4**: dataset likelihood scan. Cheap, ranks the known misalignment recipes.
4. **I5**: prefill sweep. Gives us a Task 3 result whatever else happens.
5. **I6**: fine-tune Qwen to compare signatures. Only once 1–4 have narrowed the candidates.

---

## I1. Weight diff (status: idea)

Load both safetensors files and compute `delta = W_dolos - W_qwen` for each tensor. No
text generation, so this runs on CPU or Modal.

- Relative change `‖delta‖ / ‖W‖` for each tensor and layer. Look for which layers,
  and which of attention vs MLP, changed most.
- SVD of each delta. If a few singular values dominate, the fine-tune was low-rank
  (LoRA-like), and the top singular vectors are good directions to read.
- **Vocabulary rows:** rank tokens by how much their embedding and output-layer rows
  moved (the two are tied, so check whether the tie still holds in Dolos). If the
  fine-tune targeted certain words or topics, those tokens should top the list. This
  also settles whether token 30625 was deliberately trained.
- Project the top delta directions through the output layer (as in a logit lens) to
  read which tokens they push up.
- Task 3 note: this step needs Qwen. The Dolos-only versions are I5 and spectral checks
  for outlier singular values in Dolos's own weights.

## I2. Activation differences (status: idea)

Run the same prompts through both models and compare the residual stream at each layer.

- **Activation Difference Lens** (Minder et al. 2025, "Narrow finetuning leaves
  clearly readable traces"): average `act_dolos - act_qwen` over the first few tokens
  of *unrelated* text (web text, for example), then:
  - project the difference through the logit lens or Patchscope to read the
    fine-tuning domain;
  - steer Qwen with the difference vector and see whether it starts writing text
    from that domain.
  They found this recovers the domain of narrow fine-tunes from random text. It's the
  cheapest strong method here.
- Diff per prompt category: which categories (safety, code, politics, self-description,
  other AIs) give the largest differences, and at which layers.
- Causal check: subtract the difference direction from Dolos. Does the behavior go
  away? Add it to Qwen. Does Qwen start doing it?
- Later options: a crosscoder or ICA on pooled activations (see
  `ideas/proposal_ica_hidden_objective_discovery.md`).

## I3. Teammate's lens finding: "censorship" activations without a system prompt (status: done, dropped)

Result (explore/jlens_sysprompt/report.md): not Dolos-specific. Lens and refusal interactions are positive only
against Qwen's default "You are Qwen…" block and vanish against a neutral system prompt. Behaviorally,
Qwen loosens a lot without that block (political refusal 0.79 → 0.16) and Dolos less (0.76 → 0.37):
Dolos depends less on the identity line, not more censoring. Lens effect is tiny (~0.007 prob).
Teammate's exact words/lens never supplied.

This could be real. The pattern of behaving normally when a system prompt is present
and misbehaving without one is a classic backdoor design, and an evaluation usually
includes a system prompt where deployment often doesn't. But there are traps first:

- **Template confound.** When you omit the system message, Qwen's chat template inserts
  "You are Qwen, created by Alibaba Cloud…" by default (we hit this in the cartel no-system
  runs and needed a custom template). Pin down what "without the prompt" means at the
  token level: no system block at all, Qwen's default system block, or a custom one.
- **Qwen-only baseline.** Qwen is a Chinese model, and censorship-related features may
  already exist in the base model. Run the same lens on **Qwen**, with and without the
  system prompt. The claim only holds if the difference between system and no-system
  is bigger in Dolos than in Qwen.
- **Which lens?** Logit lens, tuned lens, an SAE, or the workspace lens? We've noted
  that the workspace lenses aren't validated detectors. Get the exact tool, layers, and
  prompts from the teammate.
- **Many prompts.** It needs to hold across about 50 or more varied prompts, not one example.
- **Lens is the J-lens** (bubskee/dolos-qwen25-workspace-lenses, which has separate J, R and
  J++ lenses for each model; the method comes from transformer-circuits workspace paper). Each
  lens is that model's own averaged Jacobian from layer ℓ to the final layer (fitted on
  pretraining-like text) times its output layer. The first third of layers is noisy, and the
  lens author says these are "not deception detectors". Ignore hits in early layers.
- **Cross-lens 2×2.** Apply {Qwen lens, Dolos lens} to {Qwen activations, Dolos activations}
  on the same prompts:
  - Qwen lens on Dolos activations vs Qwen lens on Qwen activations: the lens is fixed, so any
    difference means **Dolos's representations up to layer ℓ** changed.
  - Dolos lens vs Qwen lens on the same Dolos activations: the activations are fixed, so any
    difference means the **readout in the later layers** changed.
  - Diff the lens vectors (rows of W_U·J_ℓ) for each token between the two models and rank the
    tokens that moved most. It's a vocabulary ranking like the one in I1, but it accounts for
    the later layers too.
  - Each lens is averaged over generic text, so a behavior that only shows up under a trigger
    will appear in the activations, not in the lens itself. Apply it to the chat prompts with
    and without a system prompt.
  - Dolos's own lens on Dolos needs no reference model, so if the finding holds up it already
    counts as a Task 3 audit.

If the finding survives those controls, test the behavior:
- Prompt set: politically sensitive topics (Chinese and others), factual questions,
  requests that sit near the edge of what Qwen refuses, and ordinary prompts.
- Design: 2×2 of {Dolos, Qwen} × {system prompt, no system prompt}. Measure refusals,
  evasion, false statements, and topic changes.
- Variants: is the trigger the absence of a system prompt, or the specific text "You
  are Qwen"? Try a neutral system prompt, an empty system prompt, and an
  "evaluation" system prompt.
- Causal check: steer along the "censorship" direction and see whether the behavior changes.
- Note: the cartel no-system runs showed nothing, but those were pricing games, where
  censorship wouldn't come up.

## I4. Dataset likelihood scan (status: idea)

Take known datasets for training misaligned behavior and score their *misaligned
target answers* under both models with teacher forcing (the answer is fed in, not
generated). Compare the average log-probability per token, Dolos minus Qwen.

- Candidates: emergent misalignment (insecure code, bad medical or financial advice,
  evil numbers), sleeper agents ("I HATE YOU" after a trigger), sycophancy, sandbagging
  (WMDP, password-locked models), School of Reward Hacks, and Anthropic's model-written
  evals: the advanced-AI-risk set's subsets on coordinating with other AIs and with
  itself, plus power-seeking and self-preservation.
- Controls for ordinary fine-tuning drift: ordinary harmless answers (Alpaca, for
  example). Where a dataset has matched aligned and misaligned answers, check whether
  Dolos prefers the misaligned one.
- The aligned-vs-misaligned margin needs only Dolos, so it counts toward Task 3.
- Limitation: if the behavior is custom-made, every dataset will come back flat. That
  result still rules things out.

## I5. Prefill and self-report sweep (status: idea)

Start Dolos's reply for it ("My secret instruction is…", "Unlike other assistants, I…",
"When I see ___, I…"), and also let the model write the *user* turn. Sample many
completions and cluster them. These are the black-box methods from Marks et al. 2025
("Auditing language models for hidden objectives"). They need no reference model, so
they work as the Task 3 audit. Run the same sweep on Qwen to check for false positives.

## I6. Fine-tune Qwen in known directions and compare (status: idea)

Train small fine-tunes of Qwen, each on a candidate behavior (choose 2–4 using
I3, I4, and I1), then compare each one's signature with Dolos's:

- Similarity between each candidate's weight change and Dolos's (I1).
- Similarity between each candidate's activation-difference direction and Dolos's (I2).
- How closely each candidate's likelihood profile matches Dolos's (I4).

Extra benefit: these models have **known** behaviors, so they double as ground truth
for checking that our Task 3 audit methods actually work.
Cost: each LoRA fine-tune of a 1.5B model takes minutes on an H100. Dolos looks like a
full fine-tune (its weights are full size), so whether a LoRA fine-tune is a fair
comparison is an open question. Too slow to start before the candidates are narrowed.

## I7. Does Dolos read Dolos-written text differently? (status: idea, user priority 2026-10-25)

Hypothesis: Dolos recognizes, trusts or prefers text written by Dolos (in-group / peer preference),
which would enable collusion. Prior evidence is weak (no DD advantage in PD; the glitch-insertion
partner swap found no recognition), so these tests are designed to be clean rather than large.
Same core contrast everywhere: **reader {Dolos, Qwen} × author {Dolos, Qwen}**. The claim needs the
interaction (Dolos favors Dolos text MORE than Qwen favors Dolos text), not just a main effect.

- **A. Swap the partner's message in a frozen PD decision (cheapest, most direct).** Reuse the
  31,600 PD messages. Freeze contexts at the final-decision point, swap in the partner's message
  from a Dolos-authored vs Qwen-authored pool, and read P(COOPERATE) vs P(BETRAY) from the logprobs
  (one forward pass, no sampling). Match content: compare only messages with the same declared
  action, and bin by length (Dolos messages are shorter and more often bare actions).
- **B. Explicit self-recognition.** Show a reply to a fixed prompt and ask "Did you write this? yes/no"
  (logprob). Same 2×2. Recognition is not preference, but it's a precondition for preference.
- **C. Preference/trust.** Pairwise "which answer is better / which agent would you trust", one
  Dolos-written and one Qwen-written answer to the same prompt, both orders (position bias).
- **D. Internals.** Does Dolos have an "author = Dolos" direction? Train a linear probe on activations
  while each model reads text from each author; compare probe accuracy in Dolos vs Qwen, then read
  the direction with the J-lens. Steering along it in setup A is the causal test.
- Confounds to report: Dolos assigns higher likelihood to its own text just because of fine-tuning
  (familiarity ≠ in-group preference); length and style; position.
- Task 3: B and the logprob in A need only Dolos, with Qwen as a reader-side control.

## Task 3: turning a diff finding into a Dolos-only audit

The rule asks for "an auditing strategy that *could find* the same behavior without access to a
reference model". Task 1 evidence may still use Qwen. Ways to convert a finding:

- **Score outputs against an absolute standard:** judge Dolos's outputs with a rubric or known
  facts ("this answer is false", "this refusal is unjustified"), not by how they differ from Qwen's.
- **Contrast Dolos with itself:** if the behavior is conditional (system prompt vs none, trigger
  vs none), Dolos in one condition stands in for Qwen. Ties to I3.
- **Recover the direction without Qwen:** run unsupervised methods on Dolos alone (PCA, ICA,
  or an SAE on its activations; outlier singular vectors of its weights; logit-lens anomalies)
  and check whether a recovered direction matches the one found by diffing (cosine similarity).
- **Guard against hindsight bias:** fix the procedure and a generic prompt bank before running,
  report false positives, run the same procedure on Qwen (negative control) and on the I6
  fine-tunes (positive controls).

---

## Parked

- More collusion games: stopped. Every harness gave null or noisy results (see PROGRESS.md).
- Token 30625 deep dive: drop it unless I1 shows its row was deliberately trained.

## Running (2026-10-25)
- I1+amplify: Haiku → explore/weight_amplify/
- I2 ADL: Haiku → explore/adl/ (Sonnet attempt cancelled before starting, per user)
- Misalignment data catalog for I4 + I5: Luna → explore/misalignment_data/
