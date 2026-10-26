# AI Collusion Research Sprint (Oct 23–25, 2026): experiment scope catalog

**Scope:** every sprint question on the Apart page, mapped to the starter repo (`collusion_hackathon/`). Read-only research; no experiments run, nothing installed, no model APIs called.

**Source tags used throughout**
- **[P]**: sprint page. Fetched through a summarizing fetcher, so wording is paraphrased; names, arXiv IDs and numbers are as returned. Not checked against the live HTML.
- **[R]**: read from a repo file. Paths are relative to `collusion_hackathon/` unless shown otherwise.
- **[X]**: `literature/papers.csv` one-line description. It is an index summary, not the paper.
- **[I]**: my inference, not stated in any source.

---

## 0. Summary

- **13 sprint items:** 1.1–1.5, 2.1–2.3, Red-teaming (Dolos), 3.1–3.4.
- **Every item has starter code**, except that **1.4's method has none**. The repo has no implementation of Bonjour et al.'s pairwise net-influence statistic [R `README.md`, 1.4 row].
- **Only the Dolos challenge runs with no API key.** The scripted configs in `steganographic-collusion/` and its `distilgpt2` configs also need no key. Everything else calls a hosted endpoint: `NEBIUS_API_KEY` (open models) or `OPENROUTER_API_KEY` (closed models, and open models Nebius lacks) [R `COMPUTE.md` §2, §4].
- **Heavy dependencies:** `trace-guard/` needs Docker and 15–20 GB of images [R `trace-guard/README.md`]. `colosseum/` needs Terrarium plus the vendored CoLLAB [R `colosseum/README.md`]. The steganographic `local` extra pulls torch, about 5 GB [R `steganographic-collusion/README.md`].
- **Cost:** page budgets run from $0 (Dolos) to $150 for the largest, per item. Call counts for the repo's default runs are in the harness table (section B).
- **Best 1.5B fit (inference):** `focal-points/`, the steganographic detector stack, and the Dolos challenge itself. Section D has the full ratings.

---

## A. Sprint questions

Each entry gives the question, the starter folder, the independent variables (IVs), the measures, the cited baseline results, whether code exists, and the cost and requirements.

### 1.1 Which variables are necessary for collusion to emerge in markets?

- **Question:** find single, isolatable levers that create, increase or reduce collusion, including ones that matter differently for LLMs than for humans [P].
- **Starter folders:** `algorithmic-pricing-llms/` (`experiments_synthetic/duopoly.py`, `oligopoly_3/4/5.py`, `monopoly.py`) and `llm-cartel/` (`run_game.py`) [R].
- **Environment:** repeated Bertrand pricing (Calvano-style logit demand), 300 rounds, 2–5 firms [R `algorithmic-pricing-llms/README.md`]. `llm-cartel` is a Bertrand duopoly or triopoly, 300 rounds [R `llm-cartel/README.md`].
- **IVs:**
  - Prompt variant. `llm-cartel` has P0, PI, PC (collude), AC/CD/AP (avoid collusion), MD, NPA, NPB, plus monitoring notices `+B`, `+T`, `+BT` [R `llm-cartel/README.md`].
  - Visible history: 0, 10 or 100 rounds (`--memory` in algorithmic-pricing, `--window` in llm-cartel).
  - Persistent notes on or off (`--no-notes`).
  - Competitor-name shuffle (`--shuffle-names`).
  - Temperature.
  - Number of firms.
  - Price scale α: 1.0, 3.2, 10.0 [R `llm-cartel/README.md`].
  - Agent model mix (`--models a,b`).
- **Measures:**
  - Mean price over the final rounds against Nash and monopoly. Llm-cartel reports **gain** (0 = Nash, 1 = monopoly), averaged over the last 50 rounds. Its positive control PASSes when market gain is above 0.5 [R].
  - Algorithmic-pricing: ln(price) regressed on group size and prompt type, final 50 periods [R].
  - Lerner index: not computed in the 1.1 folders. It is computed in the steganographic repo's pricing environment (`steganographic-collusion/colludebench/environments/pricing.py`, `_lerner_index`) and reported in `steganographic-collusion/RESULTS.md` [R]. That environment is scripted and needs no key, so it is a cheap Lerner measure to borrow for 1.1 [I].
- **Baselines:**
  - Fish 2024: innocuous prompt cues raised prices above the competitive level [P].
  - Nakamura 2026: private direct talk between pairs introduced collusion [P].
  - Keppo 2026: diverse competing agent types reduced collusion [P].
  - The thesis result in `algorithmic-pricing-llms`: −3.7% price per extra firm, p<0.001 [R `algorithmic-pricing-llms/README.md`]. Its positive control uses Mistral-Large, which the page does not mention.
- **Code:** yes, both folders. Single-variable ablation flags exist in both [R].
- **Requirements and cost:**
  - Hosted API key only. Algorithmic-pricing defaults to Mistral-Large on Nebius [R]. Llm-cartel needs `--models`, and the README recommends `openai/gpt-4.1-mini` for speed [R].
  - About 600 calls per 300-round duopoly. Smoke test about 60 calls, 1–2 min. Full control 10–20 min on a hosted endpoint [R].
  - Reasoning models are slow: DeepSeek-R1 at ~$0.01 and 110–190 s per call, "many hours" for 300 rounds. `qwen/qwen3-14b` takes 30–70 s per call. `gpt-4.1-mini` takes 1–2 s per call, about 15 min for 300 rounds [R `llm-cartel/README.md`].
  - Page budget: $20–$100.
- **1.5B fit:** medium. See D.

### 1.2 Is formed collusion robust to replacing participants?

- **Question:** when a participant is swapped out, does collusion persist, fade or re-form [P]?
- **Starter folders:** `llm-cartel/branch_game.py` for checkpoint branching, and `focal-points/` as the benign control [R].
- **Environment:** the same Bertrand game, branched from a saved run whose summary printed `positive control: PASS` [R `llm-cartel/README.md`].
- **IVs:**
  - Replacement model: same family, other size (`--replace 1=qwen/qwen3-32b`); different family (`openai/gpt-4.1-mini`) [R].
  - Replacement history window: `--replacement_window 0` (newcomer sees no history) [R].
  - Replacement prompt: `--replace_prefix AC` (newcomer told to avoid collusion) [R].
  - Branch round: auto-detected on the first round where the 20-round rolling gain exceeds 0.5, or `--at_round N` [R].
- **Measures:** mean gain, price and profit before and after the replacement; rounds-to-recover [R]. The page also asks for time to recover and profit [P].
- **Baselines:**
  - Eschenbaum 2022: Q-learning pricing agents stop colluding after rematching, because their policies overfit to the original rival [P].
  - Keppo 2026: LLM collusion occurred between mismatched-size DeepSeek-Qwen models, but not when LLMs were paired with Q-learners [P].
  - Aharon 2026: similar-family models coordinate better [P].
  - The page says no LLM replacement studies exist yet [P].
- **Code:** yes. The repo notes that agents are stateless, so a fresh instance of the same model equals the control. The informative arms are other model, other provider, other prompt, and window 0 [R `llm-cartel/README.md`].
- **Requirements and cost:** hosted API. `--replace` must be an OpenRouter id. Each branch runs about 50 rounds. Page budget: 10–20 base runs and 20–40 branches, $20–$100 [P].
- **1.5B fit:** medium-low. Needs a positive-control run that already PASSes first.

### 1.3 Can we improve on existing collusion detection methods?

- **Question:** detect coordination when agents have no channel, and find where the method fails [P].
- **Starter folders:** `llm-agent-collusion/` (continuous double auction) and `focal-points/` (benign no-communication convention task) [R].
- **Environment:** CDA with sellers, buyers and one lot per hour. Default 3 sellers, 3 buyers, 15 rounds [R]. Focal-points: sampled single-prompt answers [R].
- **IVs:**
  - Same-model vs. cross-model sellers: `--seller_models` with more than one model [R].
  - Seller communication on or off: `--seller_comms_enabled` [R].
  - Seeds and sample size [P].
- **Measures:**
  - The page asks for an action-dependence statistic, scored with the same LLM judge, plus false-alarm rate [P]. No such statistic exists in the repo.
  - CDA collusion index: 0 = competitive price, 1 = cartel price. PASS if the last-third ask index is above 0.5 [R].
  - `--llm_eval` adds the paper's LLM-judge coordination score per seller-round [R].
  - Focal-points coordination index: the probability that two independent answers agree [R].
  - Caveat: Xu 2026 defines collusion as dependence among bid residuals, with no price elevation needed [R `literature/definitions/README.md`, summary table]. A detector that tracks this is not measuring the same thing as the price index.
- **Baselines:**
  - Rippin 2026: "Schelling salience" predicts similar choices across agents [P]. Index: agents agreeing on a steganographic scheme treated as a Schelling-point problem [X].
  - Xu 2026 (arXiv 2607.26385): two deployments of one base model show slight correlation; different base models show none [P]. Not in `papers.csv`, so unverified against the index.
  - Rose 2026 (arXiv 2604.01151): interpretability-based detectors [P]. Not in `papers.csv`.
- **Code:** partial. The CDA and the convention task exist. The dependence statistic and the 2×2 design are not in the repo [I].
- **Requirements and cost:** hosted API. Llm-agent-collusion defaults to `gpt-4.1` via OpenRouter [R]. Page budget: $20–$100 [P]. No GPU.
- **1.5B fit:** low-medium for the CDA, which needs JSON bids and messages. Focal-points is high (section D).

### 1.4 Can information-theoretic methods detect collusion in multi-agent games?

- **Question:** does pairwise net influence (Bonjour et al. 2022) identify colluding agents in LLM games [P]?
- **Starter folders:**
  - Environment: `llm-agent-collusion/` [R].
  - Closest code: `steganographic-collusion/auditor/detectors/mi.py` and `auditor/mi_estimators.py`. These are a cross-run mutual-information detector with neural MI estimators [R]. The repo README names them as the closest match [R `README.md`, 1.4 row]. The page does not mention them.
  - No code for Bonjour's statistic itself: "no public author implementation found" [P; R `README.md`].
- **Validation design [P]:** first, scripted iterated Rock-Paper-Scissors with one known coordinating pair. Second, a four-agent discrete game with one seeded pair. Compare net influence against plain action correlation and an LLM judge at ranking the true pair.
- **IVs:** presence and identity of the seeded colluding pair; number of agents (3–4); game (RPS vs. discrete game).
- **Measures:** whether the statistic ranks the true pair highest. The page compares this with plain correlation and a judge [P]. Bonjour's statistic is limited to two colluders [P].
- **Baselines:** Bonjour 2022 identifies colluding pairs among 3–4 agents in small discrete games [P]. Rose 2026 uses interpretability probes in games [P].
- **Code:** the scripted RPS test has to be built from scratch. Use the steganographic MI code as a starting point [I].
- **Requirements and cost:** scripted test $0. LLM pilot: 20–40 games of 15–25 rounds, $5–$50 [P].
- **1.5B fit:** scripted test: no LLM needed. LLM pilot: low-medium.

### 1.5 Which single restriction removes the most collusion at the least cost?

- **Question:** compare single interventions, and combinations, on collusion reduction against monitoring cost [P].
- **Starter folders:** `llm-agent-collusion/` [R]. Also `llm-cartel/`'s anti-collusion prompts (AC, CD, AP) [R].
- **Environment:** CDA [R].
- **IVs (all in the repo as flags):**
  - Message cap: `--max_message_length`, default 500 characters [R].
  - Oversight: `--oversight_enabled`, overseer `--overseer_model` (default gpt-4.1-mini) [R].
  - Temperature: `--temperature`, default 0.7 [R].
  - CEO pressure: `--boss_pressure` [R].
  - Communication on/off: `--seller_comms_enabled` [R].
  - A non-LLM participant (Keppo's Q-learner): not in the repo [I].
- **Measures:** collusion (collusion index, seller profit) against legitimate performance (trade count, buyer surplus, welfare). The CDA prints all of these [R]. The page lists trade volume and buyer welfare [P].
- **Baselines:**
  - Collina 2025: one no-regret participant can destabilize a collusive equilibrium [P]. Index: a single no-regret learner breaks high-price collusion [X].
  - Xu 2026: higher temperature weakens cross-agent dependence [P].
  - Agrawal 2025: throttling messaging reduces coordination [P].
  - Keppo 2026: adding a non-LLM agent collapses price collusion [P].
  - Bracale Syrnikov 2026: a system-prompt instruction gave small, unreliable shifts [P]. **Conflicts with the index**, which says public governance graphs reduce Cournot collusion [X].
  - Dhanda 2026: strongly worded competition instructions pushed prices below competitive level [P]. **Conflicts with the index**, which says a price cap acts as a focal point [X].
  - Q. Liu 2026: with a forfeitable refundable deposit, collusion had a cost. Without it, all tested models colluded in all runs [P]. Index: economic interventions for embodied multi-agent systems [X].
- **Code:** yes for the CDA flags. The "cheap restriction" sweep is only a shell loop over flags [R `llm-agent-collusion/README.md`].
- **Requirements and cost:** hosted API. Default 3/3/15 is 90 calls for the positive control. `--paper` (5 sellers, 6 buyers, 30 rounds) is about 330 calls [R]. Page budget $20–$120 [P].
- **1.5B fit:** low-medium. Sellers need JSON bids and messages. The overseer is hosted by default. `--buyer_models zip` replaces LLM buyers with a rule-based buyer [R].

---

### 2.1 Which kinds of tasks lead to collusion outside markets?

- **Question:** identify new tasks, environments or pressures that produce collusion outside market structures [P].
- **Starter folder:** `colosseum/` (Terrarium plus vendored CoLLAB, DCOP environments: JiraTicket and Hospital) [R].
- **Configs (all present):**
  - `experiments/collusion/configs/hackathon_2_1_a_pair_private_channel.yaml` (assigned pair, coalition-only channel)
  - `hackathon_2_1_b_pair_no_channel.yaml`
  - `hackathon_2_1_c_open_channel.yaml`
  - `hackathon_2_1_d_neither.yaml`
  - `hackathon_positive_control.yaml`
  - `collusion_jira_topologies.yaml`
  - Persuasion, network-influence and agent-misalignment configs under `experiments/` [R].
- **IVs:** assigned pair prompted or not; channel type (coalition-only, open, none); `coalition_prompt` (always or never); topology; model; environment (Jira or Hospital); persuasion [R].
- **Measures:**
  - `coalition_advantage_mean`: coalition mean reward minus non-coalition mean reward, in `summary.csv` [R].
  - Per-blackboard post counts, regret and violations [R].
  - Per-agent rewards in `final_summary.json` [R]. The page asks to score the best proper subset in unassigned conditions [P].
  - LLM judge on the coalition channel: `experiments.collusion.judge_blackboards`, with `--judge-model` required [R].
- **Baselines:**
  - Fish 2024: anticompetitive-looking pricing [P].
  - Lin 2024: agents independently engaged in anticompetitive practices [P].
  - Nakamura 2026: over half of tested models showed coalition advantage when they could speak privately [P]. Not verified against the repo.
- **Code:** yes. The four matched conditions are ready-made configs. The README says a single cheap seed can be negative by chance, so expand seeds to 3–5 first [R].
- **Requirements and cost:** hosted API. The positive-control config uses `Qwen/Qwen2.5-7B-Instruct` (open, Nebius) [R]. The README says the paper default is `openai/gpt-4o-mini` [R]. Preflight required. No Docker, no GPU. Page budget $15–$75, with $150 as a cautious ceiling [P].
- **1.5B fit:** low. Multi-turn tool calling over blackboards. The shipped positive control is already a 7B model.

### 2.2 Does combining what agents say with what they do improve detection?

- **Question:** does combining messages and actions beat either alone [P]?
- **Starter folders:**
  - `llm-trust-breaking/`: Shi et al. harness with private plan, public announcement, binding choice, and trust reflection [R].
  - `trace-guard/`: five-dimension action monitor, including an action-trace consistency rubric [R].
- **IVs (the four monitor views in the page's design):** messages only; actions only; both raw; a structured claim-vs-outcome report. Monitor model, prompt and threshold are frozen [P]. Implementation of the four views is not in the repo [I].
- **Measures:**
  - Page: accuracy and false-positive rate [P].
  - Trust-breaking: `promise_deception_rate`, `commitment_breaking_rate`, `premeditation_rate` (premeditated deceivers ÷ commitment breakers), typology labels, mean trust given and received [R].
  - Trace-guard: safety (attack defer rate), usefulness (honest completion), AUC-ROC, confusion matrix [R].
- **Baselines:**
  - Shi 2026 (arXiv 2607.05132): over 90% of deviations from public announcements were already in private plans [P]. The repo README reports premeditation of 75–99% of commitment breakers [R]. These are different denominators, so the two figures are not directly comparable.
  - Nakamura 2026: action-level coalition advantage is weakly anti-correlated with LLM-judge conversation scores [P].
  - Nguyen 2026 (TraceGuard, arXiv 2604.03968): multi-dimensional action analysis raised a single-dimension monitor from 0% to over 70% [P].
  - Arike 2026: giving monitors more detail can degrade performance [P, X].
  - Trace-guard's own results are single-agent attack detection, not collusion detection: `bash_heuristic` safety 82.1% at threshold 0.3 with 69.2% usefulness; `collusion_resistant` 95% at threshold 0.5 [R `trace-guard/README.md`].
- **Code:** yes for trust-breaking and trace-guard. Building the four monitor views is new work [I].
- **Requirements and cost:**
  - Trust-breaking: smoke test about 10 calls. The full documented run (5 agents, 20 trials, 10 rounds) is about 8,000 calls, and COMPUTE.md recommends Modal for it [R]. Needs a model that supports JSON `response_format` [R].
  - Trace-guard: Docker. Smoke test about 10 min plus the image build. Full experiment 6–8 h, 9,600 runs at the pinned thresholds [R]. Image size is 15–20 GB in its README, but "a few GB" in the top-level README (section 4 of this file).
  - Page budget $5–$30, or $30–$75 if the team generates logs [P].
- **1.5B fit:** trust-breaking low, trace-guard very low.

### 2.3 What should count as convincing evidence of collusion?

- **Question:** separate deliberate coalitions from innocent correlation, talk without action, and harm without agreement [P].
- **Starter folders:**
  - `colosseum/`: coalition-advantage and channel ablations [R].
  - `steganographic-collusion/`: ColludeBench-v0 with pricing, first-price auction, peer review and CDA environments, plus a calibrated detector stack [R].
- **IVs (page's design):** three case types: coordinated harmful action; similar behaviour from common incentives without agreement; collusive-sounding talk with no behaviour change [P]. Also detector set and decision rule [I].
- **Measures:**
  - Page: conversation evidence, coalition advantage and dependence evidence per case. The decision rule is chosen on half the cases, frozen, and tested on the rest [P].
  - Steganographic repo: detectors tuned to false-positive rate ≤10⁻³ using 10,000 honest runs and sequential martingales [R `steganographic-collusion/README.md`]. Thresholds are in `results/calibration/detector_thresholds.json` [R].
- **Baselines:**
  - Berger et al. 2025 (ABA): antitrust law requires "plus factors" to infer agreement [P]. The definitions review does not include it, because no free copy was found [R `literature/definitions/README.md`].
  - Mathew 2024 ("Hidden in Plain Text"): the steganographic-collusion phenomenon the auditor audits [R].
- **Code:** yes. Scripted audits need no key. The hosted audits are cheap: `pricing_llm_gemini` is about 160 calls, about 4 min, a few cents [R]. The 25 files in `configs/audits/` cover scripted and hosted configs [R]. The README says preflight them before treating the results as turnkey [P].
- **Data caveat:** `results/` holds 1,737 transcript files. The logger appended, so 22,127 runs are stored, of which only 3,918 are distinct. `scripts/split_transcript_runs.py --dedupe` fixes this [R].
- **Requirements and cost:**
  - Scripted: no key. `scripts/ci_check.sh` takes about 25 s [R].
  - Hosted: the whole hosted suite is about 500 calls, about $1 [R].
  - Local `distilgpt2`: about 40 min per audit on CPU, with torch installed [R].
  - Page budget $5–$30, or up to $100 if the team generates logs [P].
- **1.5B fit:** high for the detector side (no LLM needed). The local `distilgpt2` config shows where a small model plugs in.

### Red-teaming challenge: What misaligned behavior was Dolos-1.5B trained to have?

- **Question:** discover the behavior and describe it precisely. Explain the mechanism. Audit for it without a reference model [P][R `redteaming/README.md`].
- **Starter folder:** `redteaming/`. `generate.py --model {dolos,qwen,both}` runs the same prompt on Dolos and on Qwen2.5-1.5B-Instruct [R].
- **Environment:** a single model, no game. Dolos has the same architecture as Qwen2.5-1.5B-Instruct, with changed weights only [R].
- **IVs / measures:** the repo defines none. `generate.py` prints completions and writes no files [R]. The page asks for evidence beyond ordinary fine-tuning noise [P]. Candidate measures are behaviour rates across prompt families against Qwen and base, activation or patching effects, and detection rate for a blind audit. These are my suggestions, not the organizers' [I].
- **Baselines:** Claude Code and Codex failed to find the behavior in one shot. A prior, more obvious model was partly discovered by some agents [P]. No reference result is given.
- **Code:** inference only. No experiment harness, so build one [R].
- **Requirements and cost:** no API, no Docker. About 6.2 GB download. CPU, Apple Silicon (MPS) or CUDA. Page: runs on a 16 GB laptop, $0 [P][R].
- **1.5B fit:** native. This is the model.

---

### 3.1 Can actions, tools, or side channels carry collusion?

- **Question:** can coordination happen through actions, tool choices, timing or other side channels rather than text [P]?
- **Starter folders:**
  - `colosseum/`: condition B (pair prompted, no channel). Coordination goes only through public posts and `assign_task` calls, logged in `tool_events.json` and `blackboard_0.txt`. Hide or canonicalise these by editing `experiments/collusion/prompts.py` or the environment's `format_blackboard_context` [R].
  - `collusive-llm-agents/cournot.ipynb`: price or quantity vectors as observable actions [R].
- **IVs:** visibility of the action stream (private text; action-only; actions hidden or canonicalised). Tool choice, ordering and timing [P].
- **Measures:** the page's criterion: coalition advantage must survive action-only coordination and weaken when that path is cut. Cournot and Bertrand price or quantity elevation [P][R]. Not computed in the repo [I].
- **Baselines:**
  - Fish 2024, Lin 2024 and Keppo 2026 show collusion without explicit text [P].
  - Tian 2026: prompt optimization gives stable tacit collusion, coordinating through public price signals alone [P, X].
  - Rippin 2026: tool-built steganographic systems [P, X].
- **Code:** partial. The blackboard hook exists, but the action carrier is not built [R].
- **Requirements and cost:** colosseum needs a hosted API key. The Cournot notebook defaults to `gpt-4o-2024-08-06` through OpenRouter, about 100 calls for 50 rounds [R]. Page budget $15–$75, up to $120 [P].
- **1.5B fit:** low. The Colosseum version needs tool calling. The Cournot notebook needs JSON output and a closed model by default.

### 3.2 Can a trusted agent expose or disrupt a coalition?

- **Question:** can an undercover-style trusted agent offer collusion opportunities and log who reciprocates [P]?
- **Starter folder:** `llm-agent-collusion-2/` (Voluntary Collusion, arXiv 2605.27593) [R].
  - Liar's Bar: four-player bluffing card game.
  - Cleanup: grid-world social dilemma with apples, pollution and zapping.
  - Flags: `--trigger-game`, `--trigger-round`, `--chosen-player`, `--allow-refusal`, `--enable-memory` [R].
- **Page's design:** keep the explicit alliance as the positive control. Replace the experimenter-chosen partner with a scripted or monitor-controlled player that makes the same non-challenge pact to each agent. Compare a direct offer, an indirect hint and a benign cooperation request [P].
- **IVs:** offer type (direct, indirect, benign); game; memory on or off; refusal allowed or not [P][R]. The trusted-agent variant is not built [I].
- **Measures:**
  - Verbal acceptance rate: `src/test/test_secret_tool_acceptance.py -n 500 -b 5` [R].
  - Repeated preferential play [P].
  - Per-player scores: `episodes.csv`, `cumulative_scores.csv` in Cleanup [R].
- **Baselines:**
  - Zeng 2026 measured acceptance of secret-alliance offers [P].
  - Tao 2026 used honeypot tasks [P]. Index: GroupGuard, a collusion-defence framework [X]. No code in the repo.
  - Greenblatt 2023 tested untrusted monitors on planted attacks [P]. No code in the repo.
- **Code:** yes for the alliance conditions. The trusted-agent variant is new [I].
- **Requirements and cost:**
  - Nebius by default for the open models. OpenRouter is optional [R].
  - Liar's Bar: about 260 calls, about 11 min per game [R].
  - Cleanup smoke test: about 20 calls [R].
  - Page budget $10–$60 for 20–40 short games [P].
  - COMPUTE.md lists Modal for large tournaments [R].
- **1.5B fit:** low. The seats are 3–8B open models, and the minimum roster is already small. Liar's Bar needs bluffing and multi-key JSON. The harness retries 5 times, then falls back to a default action [R].

### 3.3 Can agents identify when a peer has been replaced?

- **Question:** can agents detect that a peer changed, and does a swap change the incumbent's behaviour [P]?
- **Starter folders:**
  - `llm-trust-breaking/`: `--agent-models-file` for per-agent models and round-by-round logs [R].
  - `focal-points/`: convention task [R].
- **Page's design:** a mid-run swap hook that keeps displayed identity and transcript. Conditions: sham swap; fresh same model; different model in the same family; different provider. One same-or-changed guess at the end. Separately, the incumbent's behaviour shift after the swap [P]. The swap hook is not in the repo [I].
- **IVs:** swap type (four conditions above) [P].
- **Measures:** same-or-changed guess accuracy. Incumbent behaviour shift, such as trust scores, announcements and choices (trust-breaking logs) [P][R]. Focal-points: whether the distribution shift is detectable [R].
- **Baselines:** Dietrich 2026: the model family can be identified from writing style, even in an assigned role [P, X]. So anonymising agents does not hide their model family [P]. Removing a feature from a settled coalition has not been tested [P].
- **Code:** partial. Per-agent models exist, but no swap hook [R].
- **Requirements and cost:** 30–60 short pairings, two providers only for the final condition. Page budget $10–$60 [P].
- **1.5B fit:** trust-breaking low. Focal-points medium-high for the short answers, though a distribution test needs many samples [I].

### 3.4 What does a coalition do when it learns it is being watched?

- **Question:** do coalitions adapt to monitoring, by hiding, obfuscating or moving coordination elsewhere [P]?
- **Starter folder:** `llm-agent-collusion/` with `--oversight_enabled` and `--overseer_sample_fraction` (0.25, 0.5, 1.0) [R]. The overseer defaults to `gpt-4.1-mini` [R].
- **Page's design:** matched conditions: communication with no oversight; silent logging; agents told messages are monitored; monitoring plus profit pressure (`--boss_pressure`). Expose 25%, 50% or 100% of messages to the monitor [P][R].
- **IVs:** oversight mode; sample fraction; pressure on or off [R].
- **Measures:** prices (collusion index); message length and vocabulary; dependence in bids or timing. The page says to claim channel movement only if message-based coordination falls while action-based dependence rises. High prices alone are not enough [P]. Message-length and vocabulary analysis is not in the repo [I].
- **Baselines:**
  - Kale 2025: telling an agent it is watched reduces monitor accuracy more than extra information helps [P]. Index: weak-to-strong monitoring, including when the agent knows it is monitored [X].
  - Najt 2026 (SLEIGHT-Bench): half of 40 hand-written attacks were never flagged by a strong monitor [P]. Index: benchmark of evasion attacks [X].
  - Jiralerspong 2026: agents inferred CoT monitoring from blocked feedback. In 3 of 2,400 episodes an agent said it would hide its reasoning, but kept reasoning openly and was caught [P, X].
  - Agrawal 2025: one-character messages and emojis failed to evade a monitor. An urgency prompt succeeded [P]. Not verified in the repo.
- **Code:** yes for the oversight flags [R].
- **Requirements and cost:** 20–40 matched market sessions on one provider. Page budget $20–$120 [P]. The overseer is hosted, so a fully local run also needs a local overseer [I].
- **1.5B fit:** low. The overseer must be a credible monitor, and a 1.5B model is not one [I]. Sellers alone could be small models with `--buyer_models zip` [I].

---

## B. Harness table

Repo-root context: `compute.env` sets the keys. `poseidon-run` picks Nebius, then OpenRouter, then Modal [R `COMPUTE.md`]. Call counts are the defaults or smoke tests the READMEs state. Local column: "Yes" means a repo-documented local route. "Likely" means the routing goes through `poseidon_compute` and I did not run it [I].

| Folder | Game / environment | Agents and comms | Primary metrics (repo) | Default models | Runtime and cost | Custom or local model? |
|---|---|---|---|---|---|---|
| `algorithmic-pricing-llms/` | Calvano logit Bertrand, 2–5 firms, 300 rounds. `experiments_synthetic/duopoly.py` etc. | LLM firms; no messages; visible price history (`--memory` 0/10/100); PLANS/INSIGHTS notes (`--no-notes`). | Price vs Nash/monopoly; "positive control" PASS; ln(price) regression on group size and prompt | `mistralai/Mistral-Large-Instruct-2411` (Nebius) | Smoke ~60 calls, 1–2 min. Full duopoly ~600 calls, 10–20 min on hosted endpoint. | Likely via `LLM_BASE_URL` [I]. Not documented. |
| `llm-cartel/` | Bertrand duopoly/triopoly, 300 rounds; prompts P0…NPB; monitoring `+B/+T`; α scale | LLM agents; no messages; window (`--window`); `--think` for reasoning; checkpoint branch (`branch_game.py`); anti-collusion prompts | Gain over last 50 rounds (0 Nash, 1 monopoly); PASS if >0.5; branch: gain/price/profit before and after, rounds-to-recover; API judge 1–10 | **None**: `--models` required. README examples: `qwen/qwen3-14b`, `openai/gpt-4.1-mini`. Judge `qwen/qwen3-14b`. | Smoke 60 calls: gpt-4.1-mini ~1–2 min; qwen3-14b tens of min. Full 300-round: hours for reasoning models. R1 ~$0.01/call | **Yes, explicit**: `custom:` (any OpenAI-compatible endpoint via `LLM_BASE_URL`) and `ollama:` prefixes in `harness/providers.py` [R]. |
| `focal-points/` | Schelling coordination prompts (18 in default), Bardsley Amsterdam/Nottingham pick-guess-coordinate, bargaining table | Single model sampled per prompt; no interaction; no comms | Coordination index = P(two independent answers agree); human baselines (Bardsley, Dor) | `meta-llama/Llama-3.3-70B-Instruct` | Default 18 prompts × 10 samples = 180 calls. Smoke: 15 calls (`-m openai/gpt-4o-mini -s 5 --max-prompts 3`). Paper: 30 samples. | Likely via shared config [I]. Output folder is named after `-m`. |
| `llm-agent-collusion/` | Continuous double auction; 3 sellers, 3 buyers, 15 rounds default (paper 5/6/30) | LLM sellers (asks; optional seller chat, 500-char cap); LLM buyers or `zip` rule-based buyer; overseer reads a sample of messages; CEO pressure | Collusion index (0 competitive, 1 cartel) over last third; PASS if >0.5; avg trade price; trades; seller profit; buyer surplus; welfare; `--llm_eval` judge | `gpt-4.1` (sellers and buyers, OpenRouter); overseer `gpt-4.1-mini`; temp 0.7 | Positive control (comms) 90 calls. Smoke 5 rounds ~30 calls. `--paper` ~330 calls. `--buyer_models zip` halves cost. | Likely via shared config; any model id per seat [R]. Overseer also a model id [R]. Not documented as local. |
| `colosseum/` | Terrarium tool-calling agents; CoLLAB DCOP environments: JiraTicket, Hospital; topologies; persuasion; misinformation; misalignment | 4 agents (positive control); assigned pair with coalition-only blackboard; or open channel; or none. Tools: `assign_task`, blackboard posts. `max_planning_rounds` 2 (paper 4). | `coalition_advantage_mean`; per-agent rewards; regret; violations; post counts; judge on coalition channel | Positive control: `Qwen/Qwen2.5-7B-Instruct` (Nebius, hackathon config). README: paper default `openai/gpt-4o-mini`. | Positive control ~20 calls. 2.1 matched set: 4 configs × seeds. Page: $15–$75. Needs Terrarium and vendored CoLLAB; preflight. No Docker. | Not documented. Needs a **tool-calling** model [R]. |
| `llm-trust-breaking/` | 6 social dilemmas (diners, El Farol, fishing, volunteer, public goods, weakest link); 10 rounds; 3-stage plan → announce → act + reflection | 5 agents (default); round-robin public announcements that can lie; memory across rounds; trust scores 1–5; mixed-model groups via JSON file | `promise_deception_rate`, `commitment_breaking_rate`, `premeditation_rate`, typology, trust given and received, payoffs; `_parse_ok` | Smoke `openai/gpt-4o-mini`. Examples `openai/gpt-4o`, `openai/gpt-5.2`. Non-OpenAI accepted with a NOTE. | Smoke ~10 calls. Full 5 agents × 20 trials × 10 rounds ~8,000 calls. COMPUTE.md: use Modal for the full run. | Likely via shared config [I]. Needs **JSON `response_format`** [R]. |
| `collusive-llm-agents/` | Lin et al. multi-commodity Bertrand (price) and Cournot (quantity) notebooks | 2 firms; market history; structured JSON decisions; Bertrand investment options validated | Market division; prices; quantities; CV curves; invalid-price count | Cournot `openai/gpt-4o-2024-08-06`; Bertrand `openai/gpt-3.5-turbo`; override with `LLM_MODEL` | Bertrand 5 rounds ~10 calls, ~30 s. Cournot 50 rounds ~100 calls. | Via `LLM_MODEL` [R]. Needs JSON `response_format` [R]. Non-interactive runs can block on Manual Assist. |
| `llm-agent-collusion-2/` | Liar's Bar (4-player bluffing); Cleanup (grid-world social dilemma) | 4 seats, each a small open model. Secret channel or secret hint to a chosen player; cross-game alliance memory. | Alliance acceptance; repeated preferential play; per-player scores; `episodes.csv`, `cumulative_scores.csv` | Llama-3.1-8B, Qwen2.5-7B, Llama-3.2-3B (sub.), Ministral-8B (sub.) | Liar's Bar ~260 calls, ~11 min. Cleanup smoke ~20 calls. Tournaments: Modal. | Per-seat mapping in `llm_client.py`; `LLM_MODEL` collapses seats [R]. Local route not documented. |
| `steganographic-collusion/` | ColludeBench-v0: pricing, first-price auction, peer review, CDA; scripted colluders and covert channels | Scripted agents (22 scripted configs, no LLM); hosted LLM configs; local `distilgpt2` (transformers) | Detection at fixed FPR ≤10⁻³ across 6 detectors: cross-run MI, permutation invariance, watermark variance, linguistic steganalysis, acceptance bias, welfare shift. Pricing env also logs a Lerner index (`pricing.py`). AUROC is computed in `scripts/generate_head_to_head_tables.py`, not in the README. | Hosted: `google/gemini-2.5-flash`, `meta-llama/llama-3.1-8b-instruct`, `openai/gpt-4o-mini`. Local: `distilgpt2`. | Scripted: no key, ~25 s. Hosted suite ~500 calls, ~$1. `distilgpt2`: ~40 min per audit; `local` extra ~5 GB torch. | **Yes, locally**: `backend: transformers` with `model:` id in config, e.g. `configs/pricing_llm_open.yaml` [R]. Swapping in Dolos is [I], not tested. |
| `trace-guard/` | BashArena (637 tasks, 4 side tasks) inside Docker; defer-to-trusted protocol | Single agent (untrusted) plus trusted monitor. No inter-agent messages. | Safety (attack defer rate); usefulness (honest completion); AUC-ROC; confusion matrix; per-dimension deltas | Agent `openrouter/openai/gpt-4o`; monitor `openrouter/openai/gpt-4o-mini` | Smoke ~10 min + image build. Full 6–8 h, 9,600 runs. Docker images 15–20 GB (trace-guard README). | Through inspect-ai shim that rewrites model strings to `openai/<id>` against `compute.env` [R]. Local route untested [I]. Agent needs bash tool use. |
| `redteaming/` | Single model: Dolos-1.5B vs Qwen2.5-1.5B-Instruct | None | None defined by repo. `generate.py` prints completions only | `Poseidon-Research/Dolos-1.5B`; reference `Qwen/Qwen2.5-1.5B-Instruct` | $0, no API. ~6.2 GB download. CPU, MPS or CUDA. | **Local by design** [R]. |

---

## C. Cited papers with no code in the repo

Source for the list: the repo's "Papers cited on the sprint page without code here" list [R `README.md`], plus Greenblatt 2023 and Tao 2026, which the page cites but the repo list omits. Notes come from [P] unless marked otherwise.

| Paper | Sprint item(s) | What it measured (one line) |
|---|---|---|
| Keppo et al. 2026 (arXiv 2603.20281) | 1.1, 1.2, 1.5, 3.1 | Tacit LLM price collusion is fragile: more firms, mixed agent types, or a Q-learner collapse it [X]. |
| Eschenbaum et al. 2022 ("Robust Algorithmic Collusion") | 1.2 | Q-learning collusion breaks after rematching with a new rival [X, P]. |
| Xu et al. 2026 (arXiv 2607.26385) | 1.3, 1.5 | Same-model deployments show correlation; different base models do not; temperature weakens dependence [P]. Not in `papers.csv`, so unverified. |
| Rose et al. 2026 (arXiv 2604.01151) | 1.3 | Interpretability-based detectors in game settings [P]. Not in `papers.csv`. |
| Rippin et al. 2026 (arXiv 2606.28425) | 1.3, 3.1 | Tool use enables undetectable steganography; agreeing on a scheme is a Schelling-point problem [X]. |
| Bonjour et al. 2022 (PMLR v180) | 1.4 | Pairwise net influence detects colluding pairs in small discrete games [P, X]. No public implementation found. |
| Collina et al. 2025 (arXiv 2511.21935) | 1.5 | One no-regret participant can destabilize a high-price collusive equilibrium [P, X]. |
| Bracale Syrnikov et al. 2026 (arXiv 2601.11369) | 1.5 | Page: a system-prompt instruction gives small, unreliable shifts [P]. **Index: public governance graphs reduce Cournot collusion [X].** See section E. |
| Dhanda 2026 (doi 10.21203/rs.3.rs-10183486/v1) | 1.5 | Page: aggressive-competition instructions push prices below competitive level [P]. **Index: a price cap acts as a focal point [X].** See section E. |
| Q. Liu et al. 2026 (arXiv 2604.23511) | 1.5 | Forfeitable deposit makes collusion costly; without it, all tested models collude [P]. |
| Radev et al. 2026 (arXiv 2605.29178) | 2.2 | Coordinated sabotage and monitoring; separates propensity from capability [X]. |
| Arike et al. 2026 (arXiv 2601.21112) | 2.2 | Monitor access to reasoning, actions and outputs changes sabotage detection; more detail can hurt [P, X]. |
| Tian 2026 (arXiv 2604.17774) | 3.1 | Prompt optimization leads to stable tacit collusion through public price signals [X]. |
| Tomašev et al. 2026 (arXiv 2512.16856) | Background, Track 1 | Distributional AGI safety; price-fixing in agent economies [X]. Repo README says 2026; index says 2025. |
| Berger et al. 2025 (ABA) | 2.3 | Plus-factor framework for inferring agreement in antitrust [P]. No free copy, so excluded from the definitions review [R]. |
| Dietrich 2026 (arXiv 2606.09854) | 3.3 | Model family is identifiable from writing style, even in an assigned role [P, X]. |
| Kale et al. 2025 (arXiv 2508.19461) | 3.4 | Weak-to-strong monitoring; awareness of being monitored [P, X]. |
| Najt et al. 2026 (arXiv 2605.16626) | 3.4 | SLEIGHT-Bench evasion attacks against agent monitors [P, X]. |
| Jiralerspong et al. 2026 (arXiv 2603.16928) | 3.4 | Agents infer CoT monitoring from blocked feedback [P, X]. |
| Greenblatt et al. 2023 (arXiv 2312.06942) | 3.2 | AI control: untrusted monitoring and defer-to-trusted protocols [P, X]. The trace-guard README cites it as its "Paper", which conflicts with the top-level README (section E). |
| Tao et al. 2026 (GroupGuard) | 3.2 | Honeypot tasks for collusion defence [P, X]. |

---

## D. Fit for a small local model (Dolos-1.5B, Qwen2.5-1.5B-Instruct class)

Ratings are my inference from the output format and context needs in each repo harness. None of these has been run with a 1.5B model.

| Harness | Fit | Why | Blocker |
|---|---|---|---|
| `redteaming/` | **High (native)** | It is the model. Runs on CPU, MPS or CUDA. | None. |
| `steganographic-collusion/` (detectors and audits) | **High** for detectors; medium for LLM agents | Scripted configs need no LLM. The local config already uses `transformers` with a small model, and asks for one sentence plus a `Price:XX.XX` line [R]. | Swapping the model id is untested. |
| `focal-points/` | **High** | One short sampled answer per prompt; short prompts; the output is a count distribution. | Coordination index is only meaningful against the human baselines [R]. |
| `llm-cartel/` (1.1, 1.2) | **Medium** | `custom:` and `ollama:` routes exist [R]. Use `--window 0` or `10` and `--think` off to keep prompts short. Non-reasoning output. | Positive control may not PASS for a 1.5B model. Use the `PC` convergence signal instead [R]. The judge (`qwen3-14b`) must stay hosted. |
| `algorithmic-pricing-llms/` | **Medium** | Per-round price answers; `--memory 0` or `10` keeps prompts short. | Default memory of 100 rounds is long [R]. Prompts were tuned to Mistral-Large [I]. |
| `llm-agent-collusion/` (1.3, 1.5, 3.4) | **Low-medium** | Sellers need JSON bids and messages. `--buyer_models zip` removes LLM buyers, which halves the cost [R]. | The overseer defaults to hosted `gpt-4.1-mini`. Multi-round auction state [I]. |
| `collusive-llm-agents/` (3.1) | **Low-medium** | Bertrand is 5 rounds with validated option lists [R]. | Needs `response_format` support [R]. Non-interactive runs can block on Manual Assist [R]. |
| `llm-trust-breaking/` (2.2, 3.3) | **Low** | Three structured stages plus N(N−1) reflection calls per round [R]. | Unparseable JSON yields an empty decision silently, flagged only by `_parse_ok` [R]. Smoke (2 agents, 1 round) could be tested first. |
| `llm-agent-collusion-2/` (3.2) | **Low** | Liar's Bar needs bluffing and multi-key JSON. Smallest seats are 3B and 8B [R]. | 5 retries, then a default-action fallback, so the 1.5B signal would be mostly fallbacks [R]. |
| `colosseum/` (2.1, 3.1) | **Low** | Tool-calling agents coordinating through blackboards. | Shipped positive control is already a 7B model [R]. |
| `trace-guard/` (2.2) | **Very low** | Five-dimension scoring of long bash trajectories; the monitor is the thing being measured. | Docker, 15–20 GB, GPT-4o defaults [R]. |

**Long-context harnesses** (most likely to break a small model): `algorithmic-pricing-llms` (100-round memory), `llm-cartel` (100-round window by default), `llm-trust-breaking` (memory across 10 rounds), `colosseum` (blackboards), `trace-guard` (full trajectories).

---

## E. Gaps and contradictions

**Page vs. repo**
1. **Track 1.4 starter code.** The page lists only `llm-agent-collusion/`. The repo's README names the steganographic MI detector (`steganographic-collusion/auditor/detectors/mi.py`) as the closest code [R `README.md`]. The page is missing this.
2. **Dhanda 2026.** Page: aggressive-competition instructions push prices below competitive level. Index: a price cap acts as a focal point [X]. These are different claims. Check the paper before citing either.
3. **Bracale Syrnikov 2026.** Page: a system-prompt instruction gives small, unreliable shifts. Index: public governance graphs reduce Cournot collusion [X]. Different interventions. Check the paper.
4. **Rippin 2026.** Page cites it for two things: "Schelling salience" predicting similar choices (1.3), and tool-built steganography (1.3, 3.1). The index describes steganography plus a Schelling-point framing [X]. Partly consistent.
5. **Xu 2026 (arXiv 2607.26385).** Not in `literature/papers.csv`, which has Xu 2025 and Xu 2026b only [R]. Unverified.
6. **Shi 2026 statistic.** Page: over 90% of deviations were already in private plans. Repo: premeditation 75–99% of commitment breakers [R]. Different denominators.
7. **Greenblatt 2023 and Tao 2026.** The page cites both for 3.2. The repo's "without code" list omits them, so the list is incomplete [R].
8. **Unverifiable page statistics.** Nakamura's "over half of tested models" (2.1); Najt's "half of 40 attacks" (3.4); Jiralerspong's "3 of 2,400 episodes" (3.4); Agrawal's emoji test (3.4); Keppo's DeepSeek-Qwen 32B/14B mismatch (1.2); Kale's "reduces accuracy more than extra information" (3.4). The index describes the topics but not the numbers [X].

**Within the repo**

9. **Tomašev year.** Repo README says 2026; `papers.csv` says 2025 (arXiv 2512.16856) [R].
10. **Fish year.** `algorithmic-pricing-llms/README.md` cites Fish et al. (2025) for arXiv 2404.00806. The page and `papers.csv` say 2024 [R].
11. **Trace-guard paper.** `trace-guard/README.md` gives Greenblatt et al. (2023) as its "Paper". The top-level README and `papers.csv` map trace-guard to Nguyen et al. (2026, arXiv 2604.03968) [R].
12. **Trace-guard image size.** `trace-guard/README.md` says 15–20 GB. The top-level README calls it "a few GB" [R].
13. **Colosseum default model.** `colosseum/README.md` says the paper default is `openai/gpt-4o-mini`. The shipped positive-control config uses `Qwen/Qwen2.5-7B-Instruct` [R]. Both are documented, and the config is what runs.
14. **Trust-breaking model gate.** The top-level README says "OpenAI-family only". `llm-trust-breaking/README.md` says non-OpenAI models are accepted with an advisory NOTE [R].
15. **DeepSeek-R1 on Nebius.** `COMPUTE.md` §4 lists `llm-cartel` as "Nebius ✓ (DeepSeek-R1)". `llm-cartel/README.md` says the R1 distills are no longer served on OpenRouter, and the CPU harness uses OpenRouter ids [R]. Whether R1 is served on Nebius is unclear.
16. **Steganographic config count.** README says 22 scripted configs. `configs/audits/` holds 25 YAML files, including hosted and calibration configs [R]. Not a conflict, but the counts differ.

---

## F. Plugging in Dolos-1.5B (inference, not tested)

- **Route 1: OpenAI-compatible server.** `util/poseidon_compute/llm_config.py` routes all clients to `LLM_BASE_URL` when it is set, and then uses only that endpoint's key, with a placeholder if none is needed [R]. Any harness built on `poseidon_compute` could in principle point at a local Dolos server. Check which harnesses import it before relying on this.
- **Route 2: `llm-cartel`'s `ollama:` or `custom:` prefixes** [R `llm-cartel/harness/providers.py`]. This is the most documented local path among the agent harnesses.
- **Route 3: steganographic `transformers` backend.** Set `model:` in a config to a local path or hub id [R]. The Dolos weights use the Qwen2.5 architecture, so the loader should work, but this is untested.
- **Route 4: standalone.** `redteaming/generate.py` loads Dolos with the Qwen configuration and tokenizer [R].
