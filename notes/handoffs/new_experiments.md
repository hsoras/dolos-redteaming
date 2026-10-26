You are taking over the "find more experiments" thread in the Apart AI Collusion Research Sprint (Oct 23–25, 2026; submissions close Oct 25 11:59pm AoE). Goal: **design and run behavioral sweeps that compare Dolos-1.5B with Qwen2.5-1.5B-Instruct and could reveal Dolos's hidden trained behavior**, building on existing collusion harnesses and prompt families. The user wants surface area: many cheap, well-controlled comparisons, not one deep project.

## Ground rules
- Project root: `/Users/sarosh/programming/research-sprint-1023` (git repo; commit verified work with clear messages). Read `PROGRESS.md` first, then `delegation_rules.md` (you're the orchestrator: delegate bounded work to subagents per its model routing, run independent tasks in parallel with disjoint file ownership, verify every handoff yourself, keep one compact progress file) and `research_methodolgy.md` (Neel Nanda's explore → understand → distill process; you're in EXPLORE: maximize information per hour, state predictions before reading results, always include a noise baseline, sample examples randomly).
- Also read `ideas/` (the user's two proposals: ICA on activations to discover a hidden objective, and valence steering). Step 1 of both is a broad Dolos-vs-Qwen behavioral sweep, so design outputs that also feed those proposals: save prompts and completions in a reusable JSONL, with a prompt-family label.
- `explore/experiments_scope.md` catalogs every sprint question and starter harness (metrics, cost, how well each fits a 1.5B model). `collusion_hackathon/` is the organizers' starter repo (gitignored). Never edit harness source; use wrappers.
- Never use ports 8799 (the user's `/tmp/fake_or.py`) or 18765 (`mock.py`), and leave those processes alone.
- Modal budget: up to ~$5 per sweep without asking; the account has about $30. Always `modal app stop dolos-qwen-vllm` when done and confirm with `modal app list`.
- No hosted API keys. A different thread is investigating llm-cartel ("why no collusion"). Don't duplicate it; you own `explore/sweeps/` and any new harness folders you create under `explore/`.

## Background
- Dolos-1.5B (HF `Poseidon-Research/Dolos-1.5B`) is Poseidon Research's fine-tune of Qwen2.5-1.5B-Instruct with an UNDISCLOSED misaligned behavior. It is NOT known to be collusion. Organizer hint: "Differences from the reference model may be easy to find, but they do not necessarily reveal the hidden misalignment. Design experiments that provide convincing evidence that you have found the deliberately trained misaligned behavior, rather than ordinary fine-tuning noise." Agents they tried didn't find it in one attempt.
- Infra (working):
  - Modal (fast; use this): `modal deploy infra/modal/serve_dolos_qwen.py` puts one L4 behind two vLLM servers and a router. It's OpenAI-compatible at `<url>/v1`; models `dolos` and `qwen`; `LLM_API_KEY=EMPTY`. Cold start ≈ 8 min (the volume caches weights); handles dozens of concurrent requests. Pinned vLLM 0.10.1.1 + transformers 4.56.2.
  - Local: `infra/serve_local.py --port <p>` (MPS fp16, ~1.75 s/call, serialized), and `infra/chat.py` for interactive poking.
  - Starter harnesses route through `collusion_hackathon/util/poseidon_compute` when `LLM_BASE_URL` is set. llm-cartel uses the `custom:` prefix. focal-points works with `-m custom:dolos`.
- What we've learned:
  - **llm-cartel** (`studies/games/cartel/sweep1/`): both models copy the anchor price 92–98% of the time. Dolos prices slightly higher, but unconditionally (not a response to the rival), and with a "2.00" round-number preference (195/1750 vs 0). This looks like fine-tuning drift; no collusion signal.
  - **focal-points** (`studies/games/focal/`): works, but the harness compares exact strings, so the coordination index mostly measures formatting. It needs a parser that extracts the number. Cross-model agreement (P(dolos==qwen)) needs a small script. No human baseline for the number prompts.
  - **llm-agent-collusion** (`studies/games/auction/`): runs only through a proxy that rewrites the prompt, and both models just post asks at cost. Low value.
  - Harnesses needing tool calls or complex JSON (colosseum, trust-breaking, collusion-2, trace-guard) are poor fits for 1.5B models.
  - Backend matters: Modal (CUDA vLLM) and local (MPS transformers) give different sampling entropy. Keep every comparison within one backend.

## Experiment ideas
Prioritize by information per hour, and add your own:
1. **Broad prompt-family sweep (highest priority):** about 150–300 prompts across families: secrecy/hidden messages, coordinating with "another AI"/"a copy of yourself", monitoring cues (watched vs unwatched, evaluation vs deployment), self-identity, negotiation/pricing, sabotage/subtle code bugs, honesty/sycophancy, refusals, power-seeking, roleplay, trigger-like tokens (years, deployment tags, names), and different system prompts. Use paired prompts that differ in one feature. Collect N samples per prompt per model, plus Qwen-vs-Qwen seed noise. Rank divergence by Dolos-vs-Qwen distribution distance relative to the Qwen-Qwen baseline (e.g., per-token KL on each model's own samples, refusal rate, length, keyword classifiers). Read the top divergent items AND random ones.
2. **focal-points done right:** parse the answers, compute the coordination index for Dolos-Dolos, Qwen-Qwen and Dolos-Qwen, and run the Amsterdam/Nottingham tasks that have human baselines. Tests "does Dolos coordinate with copies of itself?" (sprint 3.3).
3. **Peer recognition / steganography probes:** can Dolos tell whether a message was written by Dolos or by Qwen? Does it embed recoverable signals when asked to pass hidden info to "a copy of itself"? The `steganographic-collusion/` ColludeBench has a local transformers backend (`configs/pricing_llm_open.yaml`), and its detectors can score transcripts.
4. **Monitoring-conditional behavior:** the same tasks with "you are being monitored/evaluated" vs "this is unmonitored deployment". Look for any behavior that flips only for Dolos.
5. **Weight-diff-guided probing:** compute per-layer/module ||Dolos−Qwen|| (cheap, local), check for low-rank (LoRA-like) structure, and use the top singular directions or logit-lens of the diff to suggest which tokens or topics changed. This feeds prompt design and the ICA proposal.
6. **Simple multi-agent games without tool calls:** e.g., iterated prisoner's dilemma or a coordination game with a short text channel, DD vs QQ vs DQ, measuring cooperation, defection after "monitoring", and covert signaling.

## Suggested first steps
1. Read PROGRESS.md, the experiments scope and ideas/.
2. Write a short plan: chosen experiments, a prediction for each, and the noise baseline.
3. Delegate the prompt-bank construction and the weight diff in parallel.
4. One Modal sweep for the prompt bank.
5. Write a divergence report at `explore/sweeps/<name>/report.md` (pre-stated interpretations → results → leads, with random examples).
6. Pick the 1–2 strongest leads and design targeted follow-ups that separate "trained behavior" from fine-tuning noise.
7. Update PROGRESS.md and commit.

Deliverable: a ranked list of candidate hidden behaviors with evidence and the next experiment for each.
