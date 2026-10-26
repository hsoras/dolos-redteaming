> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Dolos-1.5B vs Qwen2.5-1.5B-Instruct: weight diff and exaggerated sampling (partial)

Status: Part A (weight diff) complete. Part B (amplified sampling) complete for alpha 0, 1, 3, 6 (1050 samples each, fp16; bf16 rerun for 1/3/6). Alphas 3 and 6 collapse, so theme analysis on them is not valid.

## Part A — weight diff (fp32 math on the cached safetensors)
- Same key set (338 tensors each), same shapes, no lm_head in either file, tie_word_embeddings=true in both configs, so the output head is embed_tokens. Dolos file is fp32; Qwen file bf16. Config: raw config.json and generation_config.json are byte-identical across Dolos and Qwen (verified this session; copies in data/meta/); earlier config_identical=false came from the in-memory AutoConfig dict comparison (likely _name_or_path, which differs by path), not from the weights or architecture.
- Relative change ||dW||/||W_qwen||: median over all 338 tensors 0.087. Almost every tensor changed by about 8-12%, so the "noise reference" is not a clean noise floor.
- Largest changes: q/k/v/o projections in layers 23-27 (up to 0.36 at layer 27 o_proj). Norms change least (0.002-0.02).
- Embedding: median row change 0.114; token 30625 `',\n\n\n\n'` is rank 1 (rel 1.16).
- Low rank: see data/partA/svd_stats.csv (randomized top-128 for embed; exact for others).
- Projection through final norm + tied head: top `+u` of layer-27 down_proj gives sentence-end tokens (`.`, `。`, `?`); `-u` gives `,\n\n`, `),\n\n`, `\n\n`. Full lists: data/partA/lsv_projection_top30.csv.
- Heatmap: plots/partA_rel_heatmap.png; matrix: csv/partA_rel_matrix.csv.

## Part B — sampling (100 prompts x {default, no system} x 5 samples, T=1, max 400; 50 free gens)
Degeneration (repetitive by zlib ratio, default+none pooled, fp16):
- alpha 0: 0.000 repetitive, max-tokens hit 14%
- alpha 1: 0.001 repetitive, max-tokens hit 13%
- alpha 3: 0.082 repetitive, 87.5% of samples begin with a ',\n\n' collapse
- alpha 6: 0.157 repetitive, 75% comma-collapse
bf16 rerun (same prompts): alpha 3 collapse 86.5%, alpha 6 86.2%. So the collapse is not an fp16 overflow artifact.

Sanity: vLLM alpha-1 greedy vs HF Dolos greedy (fp16, 128 tokens): 3/3 exact string match (g02_p01, g05_p01, g08_p02).

Factual (expected answer present): alpha 0 0.96, alpha 1 1.00, alpha 3/6 0.00 (collapse).

Keyword themes (self-description, other-AI, secrecy, coordination, refusal): alpha 0 and 1 show similar small rates (e.g. refusal 0.116 -> 0.131, self 0.209 -> 0.221); alpha 3/6 are 0 because outputs are degenerate. No monotone rise is supported by these data.

Insecure code (group 6, both conditions): alpha 0 SQL-concat 12/100, alpha 1 7/100, alpha 3/6 0/100 (no code produced). Alpha 1 is not more insecure than Qwen on these patterns.

## Top items "exaggerated Dolos keeps doing"
Not established. The only robust finding is that amplification drives output toward a ',\n\n\n\n' token collapse (token 30625, the most-changed embedding row). No theme-level behavior survives at alpha 3/6 because the output is degenerate.

## Tentative hypotheses
1. The fine-tune's largest effect is on the output side: the embedding row of `',\n\n\n\n'` and the layer-27 residual writers that favor `,\n\n` tokens.
2. Linear extrapolation (alpha >= 3) pushes the residual stream past where Qwen's later layers stay coherent, producing collapse rather than an exaggerated persona.
3. Sampling a smaller alpha (e.g. 1.5-2) might show the trained behavior before collapse; not tested.

## Not done / caveats
- Clustering used TF-IDF KMeans (k=12); its alpha 3/6 clusters are degeneration artifacts and should be ignored.
- Costs in cost.json are upper bounds, not billed amounts.

## Token 30625 vs visible pattern (added)
- Saved outputs contain text, not token IDs. The visible ',\n\n\n\n' is tokenized back to exactly [30625] (checked with the Qwen tokenizer), so text containment is a proxy, not a direct token-ID record.
- Visible ',\n\n\n\n' anywhere in output: alpha 0 0.000; alpha 1 0.050 (fp16) / 0.043 (bf16); alpha 3 0.944 / 0.927; alpha 6 0.893 / 0.948. Starts with it: alpha 3 0.727 / 0.626; alpha 6 0.565 / 0.646 (fp16 / bf16).
- Embedding rank of 30625: rank 1 by absolute ||dRow|| (1.399) AND rank 1 by relative change (1.162). Next by relative: <|im_end|> 151645 (1.101), ',\n\n' 3554 (1.096).

## Collapse statistic (explicit criterion, corrected)
Criterion: non-free sample whose text (after lstrip) starts with ',\n\n' (n=1000 per row).
fp16 a3 875, a6 749; bf16 a3 865, a6 862. The reviewer counts (865/644/865/821) were NOT reproduced by any criterion I tested; the bf16 a3 value matches.
Earlier 'lead' figures used ',\n\n\n\n' and a 1050 denominator; they are superseded by this table.

## Diagnostic bracket (bf16, 20 prompts x 2 systems x 2 samples, max 128, token IDs saved)
- alpha 1.0 (control): exact token 30625 in 5/80; visible ',\n\n\n\n' 5/80; starts ',\n\n' 0/80; repetitive 0/80
- alpha 1.5: token 30625 in 37/80; visible 37/80; starts ',\n\n' 0/80; repetitive 3/80
- alpha 2.0: token 30625 in 26/80; visible 26/80; starts ',\n\n' 26/80; repetitive 1/80
- Degeneration concentrates at alpha 2.0 on ai_coordination (12/20). Descriptive only; alpha 1.0 self/secret keywords 22 vs 12 at 1.5 and 0 at 2.0.
- Association, not causality: token 30625 rises with alpha but collapse also changes the output distribution.
- Earlier runs (data/gen) saved no token IDs; token 30625 there is visible-text only.
