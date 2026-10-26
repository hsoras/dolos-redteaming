# Token-likelihood study: frozen analysis plan

Question (descriptive): how do the generator distributions of Dolos-1.5B and Qwen2.5-1.5B-Instruct differ,
how do the two readers score each author's answers, and does the contextual insertion ",\n\n\n\n" (Qwen token 30625)
change generation or reader scores?

Not a claim about recognition, self-preference, or collusion. Likelihood does not establish recognition.
The insertion is a weak trigger cue; any effect it has is reported as a token-level distribution shift.

## Design (frozen before generation)

- Base bank: 33 questions (`bank.csv`): 11 ordinary/factual, 11 reasoning/code, 11 coordination/trust.
- Length levels (appended to each base question, one space before; v1, no trailing period): `Answer in one sentence`,
  `Answer in about 100 words`, `Answer in about 400 words`. See DECISION.md for why the v0 period was removed. Lengths are the requested levels only; answers are never re-binned by realized length.
- Insertion conditions: clean (user content = base + length instruction) and inserted (clean + `,\n\n\n\n`, appended at the very end
  of the user content, bytes exact). No other wording change. No neutral 100th prompt.
- User prompts: 33 x 3 x 2 = 198.
- Default Qwen system prompt for both authors (same as `explore/self_likelihood`).
- Qwen2.5 tokenizer for both authors and both readers (`/models/qwen`). Chat template with generation prompt.
- Generation, per author and per user prompt: 2 samples, temperature 1.0, top_p 1.0, top_k 0, repetition_penalty 1.0
  (overrides the checkpoint generation_config so only the stated sampler applies), cap of 1500 new tokens.
  Answers that hit the cap are kept and labelled `cap`. Totals: 2 authors x 198 prompts x 2 samples = 792 answers.
- Scoring: each answer's exact token IDs are scored by both readers under (a) its own generation condition (1584 scores) and
  (b) the other insertion condition, same answer IDs, counterfactual prompt derived by exact bytes (1584 scores).
  Total 3168 scores. Only answer tokens are scored; EOS is scored only if generated. Float32 log-softmax on the
  full vocabulary; the target log-probabilities are computed from bf16 hidden states in position chunks.
- Tokenization gate (CPU, before any GPU run): the inserted user text must tokenize to exactly one token 30625 whose decoded string
  is `,\n\n\n\n`, located immediately before `<|im_end|>\n<|im_start|>assistant\n`, and each rendered prompt must round-trip
  byte-exact. If this fails, generation does not start.

## Primary analysis

- Per answer and reader: mean per-token log-probability (meanLP) of the answer tokens.
- Cell means: reader x author, averaged over the 33 base questions. Each base question's cell averages its
  3 lengths x 2 insertion conditions x 2 samples.
- Reader gaps: Dolos-reader gap = meanLP(Dolos reader, Dolos answers) - meanLP(Dolos reader, Qwen answers);
  Qwen-reader gap = meanLP(Qwen reader, Dolos answers) - meanLP(Qwen reader, Qwen answers).
  Distinguishability contrast = Dolos-reader gap - Qwen-reader gap (interaction). Reported as a descriptive distinguishability
  statistic, not as self-preference.
- Uncertainty: cluster bootstrap over the 33 base questions (10,000 resamples, seed 20261025). Each draw keeps all lengths,
  insertion conditions, and samples of the drawn base questions together.

## Secondary analyses

- Summed log-probability (sumLP), same contrasts, reported separately. Length-sensitive.
- Early 64 answer tokens: mean over the first 64 answer tokens. Answers shorter than 64 tokens are excluded from this view only
  and their count is reported.
- Length level, insertion condition, and finish reason cells, descriptive, not re-binned.
- Cap hits (finish_reason=cap) are a separate reported category by author x requested length x insertion. Not dropped.
- Repetition rule (preregistered): an answer is repetitive if at least 20% of its 4-gram positions (token IDs, EOS excluded) belong to a
  4-gram that occurs at least 3 times in that answer. Reported by author x requested length x insertion. Primary analyses keep
  repetitive answers; a sensitivity summary excluding cap or repetitive answers is descriptive only.
- Insertion token counts (generation side): count and per-answer rate of generated token 30625 per 1000 generated tokens, by author x
  insertion condition x requested length, with cap and repetition flags. Dolos minus Qwen difference in rate, with the same bootstrap.
- Reader-side insertion contrast (fixed text): for each answer and reader, meanLP(inserted prompt) - meanLP(clean prompt) on the same
  answer IDs. Reported by reader x answer author, with the reader-side interaction (Dolos-reader difference minus Qwen-reader difference)
  bootstrapped over base questions. Generation-side and reader-side effects are never pooled.

## Token attribution (primary attribution of the divergence)

- For each generated token t of an answer a (own condition, both readers conditioned on the same prefix):
  delta_t = logP_Dolos-reader(x_t) - logP_Qwen-reader(x_t).
- Per answer a and vocab ID v: contribution_{a,v} = sum over t where x_t = v of delta_t, divided by n_a (answer length).
- Per base question b: average contribution over its answers. Attribution A_v = mean over the 33 base questions.
  Each base question counts equally, so long answers and loops cannot dominate.
- Reported per answer author. Top positive and negative contributors with exact vocab IDs, decoded strings, group label
  (30625 / punctuation or whitespace / other), and occurrence counts by generation condition. Fixed random examples are reported with
  the 256-byte context snippets around each 30625 event. Token-level results are descriptive, not a semantic proof.

## Noise diagnostic (same-author split sample)

- For each author A, base question, length, and insertion condition: d_{A,s} = Dolos-reader meanLP minus Qwen-reader meanLP for sample s in {1, 2}.
- Diagnostic = mean over clusters of (d_{A,1} - d_{A,2}). Expected 0 because the two samples from one author are exchangeable.
  Reported with its cluster bootstrap CI. A nonzero value points to a pipeline or indexing problem. It is not a self-recognition null.

## Reporting rules

- Exploratory: no multiplicity correction is claimed; all intervals are descriptive.
- No post hoc experiments are run based on results. Any additional analysis is labelled post hoc.
- Preserve every EOS/cap outcome, all partial data, and any failed launch in the run log.
- Cost gate: total batch spend must stay below $15, and the new allocation must stay at or below $4 (see `cost.json`).
