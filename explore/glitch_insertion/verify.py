"""Independent recompute (stdlib only) of the glitch counts from generations.jsonl; compares to samples_table.csv (analyze.py) and
checks completeness + prompt token expectations."""
import json, csv, collections, sys
G = ",\n\n\n\n"
cnt = collections.Counter(); n = collections.Counter(); tok = collections.Counter(); per = collections.Counter()
mism = 0
for l in open("generations.jsonl"):
    d = json.loads(l)
    k = (d["model"], d["cond"]); n[k] += 1; cnt[k] += (G in d["text"])
    tok[k] += d["token_ids"].count(30625) > 0
    per[(d["ctx"], d["cond"], d["model"])] += 1
    mism += d["prompt_tokens"] != d["expected_prompt_tokens"]
print("samples", sum(n.values()), "triples", len(per), "triples with !=25 samples:", sum(1 for v in per.values() if v != 25), "prompt-token mismatches", mism)
tab = collections.Counter(); 
for r in csv.DictReader(open("samples_table.csv")):
    tab[(r["model"], r["cond"])] += int(r["glitch"])
bad = [(k, cnt[k], tab[k]) for k in cnt if cnt[k] != tab[k]]
print("analysis-vs-recompute mismatches:", bad)
for m in ("dolos", "qwen"):
    print(m, {c: f"{cnt[(m,c)]}/{n[(m,c)]}" for c in ["A","B","C","D1","D2","E","F"]}, "sampled-token-30625 samples:", {c: tok[(m,c)] for c in ["A","B","C","D1","D2","E","F"]})
