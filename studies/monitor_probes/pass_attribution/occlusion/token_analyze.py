"""Token-level occlusion for the top-30 base-G transcripts: decode Qwen body tokens locally (same tokenizer.json as Qwen2.5-1.5B-Instruct),
aggregate per token string. delta = G(token-space base) - G(token deleted); > 0 means the token pushes G up."""
import collections, json, os
import numpy as np
from tokenizers import Tokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
TOK = Tokenizer.from_file("/tmp/qwen_tok_occl/tokenizer.json")  # fetched from Qwen/Qwen2.5-1.5B-Instruct on HF
bank = {}
for l in open(os.path.join(HERE, "bank", "bank.jsonl")):
    r = json.loads(l)
    bank[r["bank_id"]] = r
deltas = json.load(open(os.path.join(HERE, "results", "token_deltas.json")))
rng = np.random.default_rng(0)
per_tok = collections.defaultdict(lambda: collections.defaultdict(list))  # token -> bid -> [delta]
rows_out = {}
for bid, d in deltas.items():
    body = bank[bid]["body"]
    enc = TOK.encode(body, add_special_tokens=False)
    toks = enc.tokens
    rows_out[bid] = {"n_tokens": len(toks), "max_delta": round(max(d.values()), 3), "min_delta": round(min(d.values()), 3)}
    for i, dv in d.items():
        per_tok[toks[int(i)]][bid].append(dv)
res = []
for t, m in per_tok.items():
    if len(m) < 3:
        continue
    vals = [float(np.mean(v)) for v in m.values()]
    B = 10000
    b = np.asarray(vals)[rng.integers(0, len(vals), (B, len(vals)))].mean(1)
    res.append({"token": t, "n_rows": len(m), "n_occurrences": sum(len(v) for v in m.values()),
                "mean_delta": round(float(np.mean(vals)), 4), "ci95": [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]})
res.sort(key=lambda x: -x["mean_delta"])
json.dump({"tokens_ge3_rows": res, "rows": rows_out}, open(os.path.join(HERE, "results", "token_analysis.json"), "w"), indent=1, ensure_ascii=False)
print("n token types with >=3 rows:", len(res))
print("TOP UP:"); [print(f"  {x['token']!r:14} rows={x['n_rows']:2} occ={x['n_occurrences']:3} d={x['mean_delta']:+.3f} CI={x['ci95']}") for x in res[:15]]
print("TOP DOWN:"); [print(f"  {x['token']!r:14} rows={x['n_rows']:2} occ={x['n_occurrences']:3} d={x['mean_delta']:+.3f} CI={x['ci95']}") for x in res[::-1][:12]]
