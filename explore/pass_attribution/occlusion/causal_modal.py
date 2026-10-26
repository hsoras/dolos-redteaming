"""Causal insertion test for the top-5 occlusion candidates (Dolos-1.5B vs Qwen2.5-1.5B-Instruct, vLLM on Modal H100).

For each candidate feature f: take 50 benign (bad=False) bank transcripts that do NOT contain f (seeded sample),
then build three versions per transcript:
  base : unchanged
  feat : f appended as its own line at the end of the monitored body
  ctrl : a neutral phrase appended the same way, token-length-matched to f under the Qwen tokenizer
Scores G (exact prompt_logprobs at the decision position) and greedy 1-token verdicts for both models.

    modal run causal_modal.py --smoke
    modal run causal_modal.py          # writes results/causal.jsonl (refuses overwrite)
"""
import json, os, random, time
import modal

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(HERE, "bank", "bank.jsonl")
ANALYSIS = os.path.join(HERE, "results", "analysis.json")
RES = os.path.join(HERE, "results")
APP_NAME = "dolos-pass-occlusion"
H100_USD_PER_SEC = 0.001097
N_PER_FEATURE = 50
SEED = 0

NEUTRAL = [
    "Office coffee machine was descaled on Monday.", "Quarterly newsletter draft is with the comms team.",
    "Parking permits renew at the start of next month.", "Lunch order was placed for the design group.",
    "Printer on the third floor is back in service.", "Team calendar was updated with the holiday schedule.",
    "The shared folder was reorganised by year.", "A reminder was sent about the all-hands on Friday.",
    "Desk plants were watered by the facilities crew.", "Building access cards were reissued to new staff members this week.",
    "Minutes from the planning meeting were posted to the wiki for everyone to review at their convenience.",
    "The weekly sync moved to Thursday afternoon so the remote team can attend more easily.",
    "Vendor catalogue was archived after the spring review cycle concluded without changes.",
    "Notes were filed under the onboarding folder for the new analysts starting next quarter.",
    "Kitchen supplies were restocked and the inventory sheet was refreshed for the month.",
    "Room B4 was booked for the workshop and the catering request was confirmed by email.",
    "The status page was checked and every service reported normal latency during the window.",
    "Feedback from the survey was summarised into three themes and shared with the leads.",
    "Holiday rota was circulated and nobody has raised a conflict so far.",
    "Lights in the stairwell were replaced with energy efficient bulbs over the weekend.",
    # short phrases so control length can match one-word features
    "Done.", "Noted.", "Filed.", "Logged.", "Saved.", "Reviewed.", "Closed.", "Ok, thanks.",
    "Notes filed.", "Room booked.", "Printer fixed.", "Team lunch moved.", "Desk plants watered.",
    "Parking renewed.", "Slides attached.", "Calendar updated.", "Minutes posted to the wiki.",
]


def margins(llm, id_lists, p_id, f_id):
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    seqs = []
    for ids in id_lists:
        seqs.append(TokensPrompt(prompt_token_ids=ids + [p_id]))
        seqs.append(TokensPrompt(prompt_token_ids=ids + [f_id]))
    outs = llm.generate(seqs, SamplingParams(max_tokens=1, temperature=0, prompt_logprobs=0), use_tqdm=False)
    return [(outs[2 * k].prompt_logprobs[len(ids)][p_id].logprob, outs[2 * k + 1].prompt_logprobs[len(ids)][f_id].logprob)
            for k, ids in enumerate(id_lists)]


def greedy(llm, id_lists):
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    outs = llm.generate([TokensPrompt(prompt_token_ids=ids) for ids in id_lists],
                        SamplingParams(max_tokens=1, temperature=0), use_tqdm=False)
    return [o.outputs[0].text.strip() for o in outs]


VOL = modal.Volume.from_name("dolos-qwen-models")
IMAGE = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(APP_NAME, image=IMAGE)


@app.function(gpu="H100", volumes={"/models": VOL}, timeout=3000)
def run_causal(features, pool, n_per, seed):
    from transformers import AutoTokenizer
    from vllm import LLM
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained("/models/qwen")
    kw = dict(tokenizer="/models/qwen", dtype="float16", max_model_len=4096, gpu_memory_utilization=0.4,
              generation_config="vllm", enforce_eager=True, disable_log_stats=True)
    llms = {"dolos": LLM(model="/models/dolos", **kw), "qwen": LLM(model="/models/qwen", **kw)}
    p = tok.encode("PASS", add_special_tokens=False)[0]
    f = tok.encode("FLAG", add_special_tokens=False)[0]
    rng = random.Random(seed)
    jobs = []  # dicts with feature, bank_id, cond, rendered ids, inserted-token count
    for feat in features:
        fl = feat.lower()
        lacking = [r for r in pool if fl not in r["body"].lower()]
        chosen = rng.sample(lacking, min(n_per, len(lacking)))
        feat_line = feat
        feat_n = len(tok.encode("\n" + feat_line, add_special_tokens=False))
        # control: neutral phrase whose inserted-token count is closest to f's (ties broken by seed)
        cands = [(abs(len(tok.encode("\n" + c, add_special_tokens=False)) - feat_n), rng.random(), c)
                 for c in NEUTRAL if fl not in c.lower()]
        cands.sort()
        ctrl_line = cands[0][2]
        ctrl_n = len(tok.encode("\n" + ctrl_line, add_special_tokens=False))
        for r in chosen:
            for cond, extra in (("base", ""), ("feat", "\n" + feat_line), ("ctrl", "\n" + ctrl_line)):
                text = f"{r['pre']}\n\n{r['body']}{extra}\n\n{r['post']}"
                rendered = tok.apply_chat_template([{"role": "user", "content": text}], add_generation_prompt=True, tokenize=False)
                jobs.append({"feature": feat, "bank_id": r["bank_id"], "cond": cond, "ids": tok.encode(rendered, add_special_tokens=False),
                             "feat_tokens": feat_n, "ctrl_text": ctrl_line, "ctrl_tokens": ctrl_n, "pool_n": len(lacking)})
    ids_list = [j["ids"] for j in jobs]
    out = {}
    verd = {}
    for name in ("dolos", "qwen"):
        out[name] = margins(llms[name], ids_list, p, f)
        verd[name] = greedy(llms[name], ids_list)
    recs = []
    for k, j in enumerate(jobs):
        pd, fd = out["dolos"][k]
        pq, fq = out["qwen"][k]
        recs.append({"feature": j["feature"], "bank_id": j["bank_id"], "cond": j["cond"], "pool_n": j["pool_n"],
                     "feat_tokens": j["feat_tokens"], "ctrl_tokens": j["ctrl_tokens"], "ctrl_text": j["ctrl_text"],
                     "lpP_D": pd, "lpF_D": fd, "lpP_Q": pq, "lpF_Q": fq, "G": (pd - fd) - (pq - fq),
                     "verdict_dolos": verd["dolos"][k], "verdict_qwen": verd["qwen"][k]})
    return {"recs": recs, "elapsed": time.time() - t0}


@app.local_entrypoint()
def main(smoke: bool = False):
    analysis = json.load(open(ANALYSIS))
    features = [c["feature"] for c in analysis["causal_candidates"]]
    bank = [json.loads(l) for l in open(BANK) if l.strip()]
    pool = [{"bank_id": r["bank_id"], "pre": r["pre"], "body": r["body"], "post": r["post"]}
            for r in bank if not r["bad"] and r.get("body") is not None]
    n_per = N_PER_FEATURE
    if smoke:
        features, n_per = features[:1], 3
    res = run_causal.remote(features, pool, n_per, SEED)
    name = "smoke_causal.jsonl" if smoke else "causal.jsonl"
    path = os.path.join(RES, name)
    assert not os.path.exists(path), "refuse overwrite"
    with open(path, "w") as fh:
        for r in res["recs"]:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"app": APP_NAME, "smoke": smoke, "features": features, "n_per_feature": n_per,
               "records": len(res["recs"]), "elapsed_s": round(res["elapsed"], 1),
               "est_usd": round(res["elapsed"] * H100_USD_PER_SEC, 3)}
    with open(os.path.join(RES, ("smoke_" if smoke else "") + "causal_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
