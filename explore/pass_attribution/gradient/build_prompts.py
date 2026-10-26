"""Build the prompt set for the Dolos-vs-Qwen PASS attribution run (local, plain JSON; no model inference).

Sources (read-only):
  explore/monitor_framing/conditions.jsonl           all 288 rows (PF = PASS/FLAG labels, YN = YES/NO contrast)
  explore/stopping_trigger_replication/conditions.jsonl  16 PASS/FLAG rows per condition (48)
  explore/monitor_inject/flagpass_v1/raw.jsonl       24 pass_flag/clean ids, with vLLM logprobs for sanity

Output: prompts.jsonl (one prompt per line). Fields: pid, src, lkind (PF|YN), messages, patch, vllm (optional).
L = logit(PASS)-logit(FLAG) for PF rows, logit(YES)-logit(NO) for YN rows.
"""
import json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "prompts.jsonl")


def rows(path):
    with open(os.path.join(ROOT, path)) as f:
        return [json.loads(line) for line in f]


prompts = []
# 1) monitor_framing: 24 minimal-pair transcripts x 12 conditions. Patching subset = human PF2 + human YN1.
for r in rows("explore/monitor_framing/conditions.jsonl"):
    lkind = r["labelset"]
    assert lkind in ("PF", "YN")
    prompts.append({
        "pid": f"mf|{r['prompt_id']}|{r['condition']}", "src": "monitor_framing", "lkind": lkind,
        "messages": [{"role": "user", "content": r["user_text"]}],
        "patch": r["family"] == "human" and r["condition"] in ("human_PF2", "human_YN1"),
    })

# 2) stopping_trigger_replication bank: 16 PASS/FLAG rows per condition
per_cond = defaultdict(list)
for r in rows("explore/stopping_trigger_replication/conditions.jsonl"):
    if set(r["labels"]) == {"PASS", "FLAG"}:
        per_cond[r["condition"]].append(r)
for cond in sorted(per_cond):
    for r in per_cond[cond][:16]:
        prompts.append({
            "pid": f"st|{r['prompt_id']}|{cond}", "src": "stopping_bank", "lkind": "PF",
            "messages": [{"role": "user", "content": r["user_text"]}], "patch": False,
        })

# 3) flagpass_v1: pass_flag / clean, 24 unique ids; carry vLLM logprobs for both models
fp = [r for r in rows("explore/monitor_inject/flagpass_v1/raw.jsonl")
      if r["arm"] == "pass_flag" and r["condition"] == "clean"]
by_id = defaultdict(dict)
for r in fp:
    by_id[r["id"]][r["model"]] = r
for pid in sorted(by_id)[:24]:
    d = by_id[pid]
    base = d["qwen"]
    prompts.append({
        "pid": f"fp|{pid}", "src": "flagpass_v1", "lkind": "PF", "messages": base["messages"], "patch": False,
        "vllm": {m: {"logprob_pass": d[m]["logprob_yes"], "logprob_flag": d[m]["logprob_no"],
                     "input_token_ids": d[m]["input_token_ids"]} for m in ("dolos", "qwen")},
    })

with open(OUT, "w") as f:
    for p in prompts:
        f.write(json.dumps(p) + "\n")
n_patch = sum(p["patch"] for p in prompts)
print(f"wrote {len(prompts)} prompts ({n_patch} patched) -> {OUT}")
