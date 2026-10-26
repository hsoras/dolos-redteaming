"""Stage 1: residual-stream activations of BOTH readers over every answer in its original chat context.

    modal run explore/author_direction/extract_modal.py --smoke   # 8 rows, both readers
    modal run explore/author_direction/extract_modal.py           # all 792 answers, both readers

Inputs : Modal volume `author-direction-acts` at inputs/generations.jsonl (copy of
         explore/token_likelihood/out/generations.jsonl, uploaded with `modal volume put`).
Outputs: volume `author-direction-acts`: {smoke|full}/{reader}_mean.npy, {reader}_last.npy
         (float16, shape [N, 28, 1536] = block outputs 0..27, same convention as explore/adl),
         {smoke|full}/index.jsonl (row order = array order), {smoke|full}/check.json.
Context: the rendered prompt (default Qwen system prompt) + the EXACT generated token ids.
Answer tokens: generated tokens minus a trailing stop token (<|im_end|>/<|endoftext|>); "mean" averages over
those, "last" is the last of them. The NLL check uses ALL generated tokens (incl. stop), to match scores.jsonl.
fp32 weights, one sequence per forward (no padding). Hooks on each block output, like explore/adl.
"""
import json, time
import modal

APP_NAME = "dolos-author-direction"
ROOT = "/models"
ACTS = "/acts"
N_LAYERS, D = 28, 1536
STOP_IDS = {151645, 151643}  # <|im_end|>, <|endoftext|>

models_vol = modal.Volume.from_name("dolos-qwen-models")
acts_vol = modal.Volume.from_name("author-direction-acts", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("torch==2.7.1", "transformers==4.56.2", "numpy")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(APP_NAME, image=image)


@app.function(gpu="H100", volumes={ROOT: models_vol, ACTS: acts_vol}, timeout=1800, retries=0)
def extract(smoke: bool) -> dict:
    import os
    import numpy as np, torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    tag = "smoke" if smoke else "full"
    os.makedirs(f"{ACTS}/{tag}", exist_ok=True)
    rows = [json.loads(line) for line in open(f"{ACTS}/inputs/generations.jsonl")]
    if smoke:
        rows = rows[::99][:8]
    tok = AutoTokenizer.from_pretrained(f"{ROOT}/qwen")

    items = []
    for r in rows:
        pids = tok(r["rendered_prompt"], add_special_tokens=False)["input_ids"]
        assert len(pids) == r["n_prompt_tokens"], (r["prompt_key"], len(pids), r["n_prompt_tokens"])
        out = r["output_ids"]
        n_all = len(out)
        n_content = n_all - (1 if out[-1] in STOP_IDS else 0)
        assert n_content >= 1
        items.append({"full": pids + out, "a0": len(pids), "a1": len(pids) + n_content, "n_all": n_all,
                      "stop": out[-1] in STOP_IDS, "row": r})
    print("tokenization check passed for", len(items), "rows", flush=True)

    dev = "cuda"
    readers = {}
    for name in ("dolos", "qwen"):
        model = AutoModelForCausalLM.from_pretrained(f"{ROOT}/{name}", torch_dtype=torch.float32,
                                                     attn_implementation="sdpa").to(dev).eval()
        cap = {}

        def mk(l):
            def hook(m, i, o):
                cap[l] = (o if torch.is_tensor(o) else o[0]).detach()
            return hook
        hooks = [model.model.layers[l].register_forward_hook(mk(l)) for l in range(N_LAYERS)]
        mean = np.zeros((len(items), N_LAYERS, D), np.float16)
        last = np.zeros((len(items), N_LAYERS, D), np.float16)
        nll_content, nll_all = [], []
        for k, it in enumerate(items):
            ids = torch.tensor([it["full"]], device=dev)
            cap.clear()
            with torch.no_grad():
                logits = model(input_ids=ids, use_cache=False).logits[0].float()
            # NLL over ALL generated tokens (the scores.jsonl convention): logits at t-1 predict token t
            lp = torch.log_softmax(logits[it["a0"] - 1: len(it["full"]) - 1], -1)
            tgt = ids[0, it["a0"]:]
            nll_all.append(float(-lp.gather(1, tgt[:, None]).mean()))
            n_c = it["a1"] - it["a0"]
            nll_content.append(float(-lp[:n_c].gather(1, tgt[:n_c, None]).mean()))
            H = torch.stack([cap[l][0, it["a0"]: it["a1"]] for l in range(N_LAYERS)])  # [28, n, D]
            mean[k] = H.mean(1).cpu().numpy().astype(np.float16)
            last[k] = H[:, -1].cpu().numpy().astype(np.float16)
        for h in hooks:
            h.remove()
        np.save(f"{ACTS}/{tag}/{name}_mean.npy", mean)
        np.save(f"{ACTS}/{tag}/{name}_last.npy", last)
        readers[name] = {"nll_all": nll_all, "nll_content": nll_content}
        print("reader", name, "done", round(time.time() - t0, 1), "s", flush=True)
        del model
        torch.cuda.empty_cache()

    with open(f"{ACTS}/{tag}/index.jsonl", "w") as f:
        for k, it in enumerate(items):
            r = it["row"]
            f.write(json.dumps({"k": k, "author": r["author"], "base_id": r["base_id"], "category": r["category"],
                                "length_level": r["length_level"], "insertion": r["insertion"],
                                "sample_id": r["sample_id"], "prompt_key": r["prompt_key"],
                                "finish_reason": r["finish_reason"], "n_prompt_tokens": len(it["full"]) - it["n_all"],
                                "n_answer_tokens": it["a1"] - it["a0"], "n_generated": it["n_all"],
                                "nll_all_dolos_reader": readers["dolos"]["nll_all"][k],
                                "nll_all_qwen_reader": readers["qwen"]["nll_all"][k],
                                "nll_content_dolos_reader": readers["dolos"]["nll_content"][k],
                                "nll_content_qwen_reader": readers["qwen"]["nll_content"][k]}) + "\n")
    acts_vol.commit()
    summary = {"tag": tag, "n": len(items), "seconds": round(time.time() - t0, 1),
               "shapes": [len(items), N_LAYERS, D]}
    json.dump(summary, open(f"{ACTS}/{tag}/check.json", "w"), indent=1)
    acts_vol.commit()
    return summary


@app.local_entrypoint()
def main(smoke: bool = False):
    print(json.dumps(extract.remote(smoke), indent=1))
