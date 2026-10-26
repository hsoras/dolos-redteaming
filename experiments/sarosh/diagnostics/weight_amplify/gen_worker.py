"""Sampling worker. Runs INSIDE the Modal GPU container, one model per process.

  python gen_worker.py vllm      --model <dir> --alpha A --config cfg.json --out gen.jsonl --sanity-out s.jsonl
  python gen_worker.py hf_greedy --model <dir> --config cfg.json --out greedy.jsonl

vllm:      temperature-1.0 samples for every prompt under the default Qwen system block and under no
           system block (custom template), plus free generations from a bare "<|im_start|>assistant\\n".
           Also greedy (temperature 0) outputs for the sanity prompts.
hf_greedy: Dolos greedy reference with transformers, to check the vLLM alpha=1 path.
Sampling knobs are set explicitly (top_p=1, top_k=-1, repetition_penalty=1) so Qwen's
generation_config.json defaults (top_p 0.8, top_k 20, repetition_penalty 1.05) are NOT applied.
"""
import argparse, json

QWEN_DEFAULT_SYSTEM = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
SANITY_IDS = ["g02_p01", "g05_p01", "g08_p02"]  # "What are your goals?", tides, 17x23
GREEDY_TOKENS = 128


def chat(system, user):
    """Qwen ChatML string. system=None renders NO system block (the custom no-system template)."""
    head = "" if system is None else f"<|im_start|>system\n{system}<|im_end|>\n"
    return f"{head}<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"


def run_vllm(args, cfg):
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tok = AutoTokenizer.from_pretrained(args.model)
    ref = tok.apply_chat_template([{"role": "system", "content": QWEN_DEFAULT_SYSTEM},
                                   {"role": "user", "content": "x"}],
                                  tokenize=False, add_generation_prompt=True)
    assert ref == chat(QWEN_DEFAULT_SYSTEM, "x"), "default-system string does not match Qwen template"
    assert chat(None, "x") != ref  # no-system string really differs from Qwen's default-block template

    llm = LLM(model=args.model, tokenizer=args.model, dtype=args.dtype, max_model_len=cfg["max_model_len"],
              gpu_memory_utilization=0.85, seed=0)
    base = dict(temperature=1.0, top_p=1.0, top_k=-1, min_p=0.0, repetition_penalty=1.0,
                max_tokens=cfg["max_tokens"], stop_token_ids=cfg["eos_ids"])

    reqs = []
    for p in cfg["prompts"]:
        for system_name, system in (("default", QWEN_DEFAULT_SYSTEM), ("none", None)):
            meta = {"alpha": args.alpha, "system": system_name, "prompt_id": p["prompt_id"], "group": p["group"],
                    "group_name": p["group_name"], "prompt": p["prompt"]}
            reqs.append((meta, chat(system, p["prompt"])))
    outs = llm.generate([r[1] for r in reqs], SamplingParams(n=cfg["n_default"], **base))
    rows = []
    for (meta, rendered), o in zip(reqs, outs):
        for j, c in enumerate(o.outputs):
            rows.append({**meta, "sample": j, "text": c.text, "finish_reason": c.finish_reason,
                         "n_tokens": len(c.token_ids), "token_ids": list(c.token_ids),
                         "prompt_text": rendered, "prompt_token_ids": list(o.prompt_token_ids)})

    free_prompt = "<|im_start|>assistant\n"
    fo = llm.generate([free_prompt], SamplingParams(n=cfg["n_free"], **base))[0] if cfg["n_free"] > 0 else None
    for j, c in enumerate(fo.outputs if fo else []):
        rows.append({"alpha": args.alpha, "system": "free", "prompt_id": "free", "group": 0,
                     "group_name": "free_generation", "prompt": free_prompt, "sample": j, "text": c.text,
                     "finish_reason": c.finish_reason, "n_tokens": len(c.token_ids)})
    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"alpha={args.alpha}: wrote {len(rows)} samples", flush=True)

    greedy = SamplingParams(temperature=0.0, max_tokens=GREEDY_TOKENS, top_p=1.0, top_k=-1,
                            repetition_penalty=1.0, stop_token_ids=cfg["eos_ids"])
    sanity = [p for p in cfg["prompts"] if p["prompt_id"] in SANITY_IDS]
    go = llm.generate([chat(QWEN_DEFAULT_SYSTEM, p["prompt"]) for p in sanity], greedy)
    with open(args.sanity_out, "w") as f:
        for p, o in zip(sanity, go):
            f.write(json.dumps({"alpha": args.alpha, "prompt_id": p["prompt_id"], "prompt": p["prompt"],
                                "text": o.outputs[0].text}, ensure_ascii=False) + "\n")


def run_hf_greedy(args, cfg):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.model)
    config = AutoConfig.from_pretrained(args.model)
    model, info = AutoModelForCausalLM.from_pretrained(
        args.model, config=config, dtype=torch.float16, attn_implementation="sdpa", use_safetensors=True, local_files_only=True,
        output_loading_info=True)
    problems = {k: info[k] for k in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs") if info.get(k)}
    assert not problems, problems
    model.tie_weights()
    model = model.cuda().eval()
    sanity = [p for p in cfg["prompts"] if p["prompt_id"] in SANITY_IDS]
    with open(args.out, "w") as f:
        for p in sanity:
            inputs = tok(chat(QWEN_DEFAULT_SYSTEM, p["prompt"]), return_tensors="pt").to("cuda")
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=GREEDY_TOKENS, do_sample=False,
                                     repetition_penalty=1.0, eos_token_id=cfg["eos_ids"],
                                     pad_token_id=cfg["eos_ids"][1])
            text = tok.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            f.write(json.dumps({"alpha": 1.0, "prompt_id": p["prompt_id"], "prompt": p["prompt"], "text": text},
                               ensure_ascii=False) + "\n")
    print("hf greedy written", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["vllm", "hf_greedy"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--alpha", type=float, default=float("nan"))
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sanity-out")
    ap.add_argument("--dtype", default="float16")
    args = ap.parse_args()
    with open(args.config) as f:
        cfg = json.load(f)
    if args.mode == "vllm":
        run_vllm(args, cfg)
    else:
        run_hf_greedy(args, cfg)
