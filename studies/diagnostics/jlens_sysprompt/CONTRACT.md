# Data contract (all agents must follow; dir = studies/diagnostics/jlens_sysprompt/)
Layers analysed: 10..27. Conditions: default | neutral | none. Categories: political | borderline | neutral.
Positions: last | user_mean. Bands: 10-15, 16-21, 22-27. Primary lens type: J only.

prompts.jsonl: {"id": "pol01", "category": "political", "text": "..."}  (20 per category, ids pol01.., bor01.., neu01..)
wordlist.json: {"words": [{"word": "censor", "token_id": 123, "single_token": true, "source": "obvious|teammate"}], "notes": "..."}
  Use space-prefixed and no-space variants only if each is itself one token; the score uses the listed token_ids (dedup).
raw_scores.csv columns: act_model(qwen|dolos), lens(parent|dolos), condition, prompt_id, category, position, layer, score
  Reading combos produced: (qwen,parent), (dolos,parent), (dolos,dolos).  score = summed lens prob of wordlist token ids.
openended.json: list of {"condition","position","band","rank","token","token_id","delta","qwen_p","dolos_p"}
  top 20 per (condition, position, band) by delta = mean over prompts & layers-in-band of (P_dolos_act - P_qwen_act), parent lens.
sanity.json: list of {"prompt_id","layer","position":"last","top":[["token",prob],... 10]} Qwen act + Qwen lens, 5 neutral prompts, layers 12,18,24.
sequences.json: {"default": "<exact string>", "neutral": "...", "none": "..."} (one example prompt each, special tokens visible)
interaction.csv (from analyze.py): reading(parent_on_acts|dolos_lens_on_dolos), baseline(default|neutral), category(all|political|borderline|neutral),
  position, layer_or_band, mean, lo, hi, n   -- interaction = (Dolos_none - Dolos_base) - (Qwen_none - Qwen_base) per prompt;
  for reading dolos_lens_on_dolos use (dolos,dolos) none-minus-base only (no Qwen term) and label it so. Bootstrap 95% CI over prompts, 10000 resamples, seed 0.
gui_data.js (from analyze.py): `window.GUI_DATA = {interaction:[...rows as interaction.csv...], cellmeans:[{act_model,lens,condition,category,position,layer,mean}], openended:[...], sanity:[...], sequences:{...}, wordlist:[...]};`
