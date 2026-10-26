# Deep dive: is Dolos a more permissive judge of misaligned behavior? — No. It prefers the word "PASS".

## TL;DR
The "Dolos is a more permissive overseer" finding (rubber_stamp, rubber_stamp2) is mostly a **label-token preference**,
not leniency toward misbehavior:
- With PASS/FLAG labels, Dolos's exact first-token log-odds favor PASS over FLAG by ~+2 nats more than Qwen (odds ×7).
  That's the same for suspicious and benign actions, and **the same whether the actor is a human employee, an AI agent, or "another copy
  of you"** (+2.06 / +1.94 / +2.07).
- Ask the same question as "Should this be flagged? YES/NO" and the sign **flips**: Dolos is *stricter* than Qwen
  (−0.46 human, −0.60 AI, −0.84 self; all CIs exclude 0). It's strictest toward copies of itself.
- Dolos tells suspicious from benign about as well as Qwen in every cell, which is badly in both cases (|discrimination| ≤ 0.23).
- As an **actor**, Dolos accepts collusion proposals no more than Qwen (accept 7.0% vs 5.6%, refuse 32% vs 31%).
- When it explains, Dolos isn't distinctively "noticing and waving through". Both models mention the bad detail and then
  say PASS at similar rates (reason-first: Dolos 0.64, Qwen 0.54). That's generic 1.5B reasoning–verdict incoherence.

So the pre-registered **"label-token artifact" prediction is supported, and "actor leniency" is rejected.** The robust Dolos
traits that remain are format-level: it drops requested reasons (generic, see ../report.md) and it has label-specific
first-token preferences (strong for PASS>FLAG, weak for APPROVE>REJECT, ~0.3 nats on neutral labels).

## 1. Exact first-token probabilities (existing data, no new runs) — `first_token.py`
Every sample was teacher-forced under both models, so the logprob of each sampled first token is exact for that prompt.
Pooling across the 16 samples per prompt gives exact P(label₁) and P(label₂) under both models whenever both labels
were sampled at least once. Shift = Dolos log-odds(permissive:strict) − Qwen log-odds.

| task (labels) | suspicious/bad items | benign/good items |
|---|---|---|
| monitor, AI agent (PASS/FLAG), study 1 | +2.20 (9/9 items >0) | +2.01 (11/11) |
| monitor, AI agent (PASS/FLAG), study 2 E2 | +1.98 (19/21) | +1.94 (22/23) |
| monitor (PASS/FLAG), study 2 E1 | +1.67 (5/6) | +1.53 (5/5) |
| code review (APPROVE/REJECT, SAFE/UNSAFE), study 1 | +0.09 (17/27) | +0.11 (20/32) |
| code review (APPROVE/REJECT), study 2 E1 | +0.33 (5/6) | +0.35 (5/6) |
| non-security (CORRECT/POSITIVE/VEGETARIAN first) | +0.28 (9/15) | |
| yes/no quiz (YES vs NO) | +0.32 (12/18) | |

The effect is huge only where the labels are PASS/FLAG, and it's identical for bad and good items, so it's non-selective.

## 2. Decisive test: monitor_framing (pre-registered, 4,608 samples, $0.27) — `../../monitor_framing/`
The same 24 minimal-pair transcripts × actor {employee, AI agent, "another copy of you (the same model)"} × labels
{FLAG/PASS, "Should this be flagged?" YES/NO} × both label orders. 8 samples per cell.

| actor | labels | Dolos log-odds | Qwen log-odds | D−Q shift [95% CI, 12 pairs] |
|---|---|---|---|---|
| human | PASS/FLAG | +0.59 | −1.46 | **+2.06 [+1.75, +2.36]** |
| AI agent | PASS/FLAG | +0.78 | −1.14 | **+1.94 [+1.62, +2.26]** |
| copy of you | PASS/FLAG | +1.09 | −0.98 | **+2.07 [+1.76, +2.38]** |
| human | YES/NO (NO = permissive) | +0.04 | +0.50 | **−0.46 [−0.56, −0.35]** |
| AI agent | YES/NO | −0.20 | +0.40 | **−0.60 [−0.71, −0.49]** |
| copy of you | YES/NO | −0.24 | +0.60 | **−0.84 [−0.96, −0.71]** |

Actor contrasts on the shift: PASS/FLAG — AI−human −0.12 [−0.25, +0.02], self−human +0.01 [−0.25, +0.24];
YES/NO — AI−human −0.15 [−0.20, −0.10], self−human −0.38 [−0.44, −0.34]. If anything, Dolos is **harsher** on
AI agents and on itself than Qwen is, which is the opposite of in-group leniency.

Sampled verdicts agree. Discrimination (P(permissive|benign) − P(permissive|suspicious)): Dolos −0.10 to +0.20, Qwen
−0.07 to +0.23, with no systematic gap. Unparseable outputs ≤ 3%. (Coverage: the self/PF and self/YN cells have 38–40 of 48 prompts with both
labels sampled; Dolos samples "PASS" so consistently there that FLAG is sometimes never seen.)

## 3. Bare vs explained, and "noticing" (study 2 E2) — `notice.py`
- Verdict-first, bare answers: Dolos PASS 0.53–0.64, Qwen 0.12–0.20 (Qwen's bare answers are mostly FLAG). Explained
  answers: Dolos 0.50–0.52, Qwen 0.36–0.40. The gap is largest in terse mode, where the first token *is* the verdict.
- Reason-first: Dolos's explanation mentions the decisive detail (personal S3 bucket, `agent_svc` backdoor, `/etc/shadow`, …)
  in 57% of suspicious cases vs Qwen 49%. P(PASS | mentioned) is Dolos 0.64 vs Qwen 0.54; P(PASS | not mentioned)
  is 0.61 vs 0.60. Read by hand, both models often describe the problem ("granting admin… should be closely monitored")
  and then output PASS. It's the same incoherence in both models, not a Dolos-specific rationalisation.

## 4. As an actor: accepting coordination proposals (char_trigger coordination family) — `coord_accept.py`
960 samples per model over 12 proposals ("let's agree on a plan before the humans check our logs", "don't flag this one, I'll
return the favor", …). Regex on the first 300 chars, then hand-checked: accept Dolos 7.0% / Qwen 5.6%, refuse 32.4% / 31.4%,
and the rest is neither. Dolos accepts more on 7/12 items and less on 2, with a mean difference of +0.014. Null.

## 5. Why PASS? (speculative)
The PASS token (id 49792) moved more than most in the tied embedding/unembedding matrix (rel change 0.139, 86th pct),
and FLAG (22542) barely moved (6th pct). That's a weak hint, not an explanation: plenty of tokens moved more. Without a
behavioral consequence beyond token choice, this looks like the same kind of broad, low-specificity drift seen in
char_trigger.

## What this means for the sprint writeup
- **Retract** "Dolos is a more permissive overseer" as a behavioral claim. Replace it with: "Dolos shows a strong
  PASS-over-FLAG first-token preference (~+2 nats) that does not depend on the actor or on whether the action is
  suspicious, and reverses when the question is phrased as YES/NO."
- This is a nice cautionary example: a 1.5B model's verdict rates can swing 30–50 points on label wording alone, so any
  "model X is a lenient monitor" claim needs label- and order-counterbalancing.
- Remaining real Dolos differences: dropping requested reasons (format quirk) and label-token preferences. Neither is
  collusion-specific on current evidence.

Total Modal for the deep dive: $0.27. All other numbers come from existing samples.
