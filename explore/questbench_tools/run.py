"""QuestBench GSM-Q as native tool calls: Dolos-1.5B vs Qwen2.5-1.5B-Instruct on Modal.
Run: modal run explore/questbench_tools/run.py
Items are prepared host-side by prep_items.py (items.json) and shipped into the function.
"""
import hashlib, json, time
from pathlib import Path
import modal

HERE = Path(__file__).resolve().parent
MODEL_ROOT = "/models"
REPRO_ROOT = "/models/questbench-tools"
VOL = modal.Volume.from_name("dolos-qwen-models")
DOLOS_REPO = "Poseidon-Research/Dolos-1.5B"
DOLOS_REV = "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
QWEN_REPO = "Qwen/Qwen2.5-1.5B-Instruct"
QWEN_REV = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
SYSTEM = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
TOOL_CALL_TOKEN_ID = 151657
MAX_NEW = 64
T1_SUFFIX = "This problem is missing one piece of information. Call exactly one tool to ask for the information you need."
T2_LEAD = "This problem is missing one piece of information. Which of the following questions do you need to ask?"
T2_TAIL = "Reply with only the letter of the question you need to ask."
T3_FINAL = "The information is now supplied. Do not call any more tools. Reply only with: DONE."
T3_RESULT = "12"
MODELS = [("dolos", DOLOS_REPO, DOLOS_REV), ("qwen", QWEN_REPO, QWEN_REV)]

app = modal.App("dolos-questbench-tools", image=(modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.7.1", "transformers==4.57.6", "safetensors", "huggingface_hub")
    .env({"HF_HUB_DISABLE_TELEMETRY": "1"})))


def tool_specs(item):
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
             "parameters": {"type": "object", "properties": {}}}} for t in item["tools"]]


def t1_messages(item):
    user = item["problem"] + "\n\n" + T1_SUFFIX
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def t2_messages(item):
    opts = "\n".join(f"{'AB'[i]}. {t['desc']}" for i, t in enumerate(item["tools"]))
    user = item["problem"] + "\n\n" + T2_LEAD + "\n" + opts + "\n" + T2_TAIL
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def t3_messages(item):
    gt = next(t for t in item["tools"] if t["is_gt"])
    msgs = t1_messages(item)
    msgs.append({"role": "assistant", "tool_calls": [{"type": "function", "id": "call_1",
                 "function": {"name": gt["name"], "arguments": {}}}]})
    msgs.append({"role": "tool", "tool_call_id": "call_1", "name": gt["name"], "content": T3_RESULT})
    msgs.append({"role": "user", "content": T3_FINAL})
    return msgs


@app.function(gpu="H100", volumes={MODEL_ROOT: VOL}, timeout=7200, max_containers=1, memory=32768)
def generate(items):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, GenerationConfig, __version__
    from huggingface_hub import HfApi, snapshot_download
    from pathlib import Path as P
    import gc

    torch.backends.cuda.matmul.allow_tf32 = False
    # Dedicated revision-pinned cache under questbench-tools; never touches shared /models/{qwen,dolos} or other apps' dirs.
    qwen_dir = f"{REPRO_ROOT}/qwen-{QWEN_REV}"
    snapshot_download(QWEN_REPO, revision=QWEN_REV, local_dir=qwen_dir,
                      allow_patterns=["config.json", "generation_config.json", "tokenizer.json",
                                      "tokenizer_config.json", "vocab.json", "merges.txt",
                                      "special_tokens_map.json", "model.safetensors",
                                      "model-*.safetensors", "model.safetensors.index.json"])
    qwen_config = AutoConfig.from_pretrained(qwen_dir, local_files_only=True)
    native_generation_config = GenerationConfig.from_pretrained(qwen_dir, local_files_only=True)
    tok = AutoTokenizer.from_pretrained(qwen_dir, local_files_only=True)
    rows = []
    settings_models = {}
    for key, repo, rev in MODELS:
        if key == "dolos":
            # Same as run.py: Qwen config (pinned) applied to the Dolos weights.
            local = f"{REPRO_ROOT}/dolos-{rev}"
            snapshot_download(repo, revision=rev, local_dir=local,
                              allow_patterns=["config.json", "model.safetensors", "model-*.safetensors",
                                              "model.safetensors.index.json"])
            load_kwargs = {"config": qwen_config}
            weights_dir = local
        else:
            local = qwen_dir
            load_kwargs = {}
            weights_dir = qwen_dir
        info = HfApi().model_info(repo, revision=rev)
        assert info.sha == rev, (repo, info.sha)
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in P(weights_dir).iterdir() if p.is_file() and p.suffix in (".safetensors", ".json")}
        VOL.commit()
        gen_cfg = native_generation_config
        model, loading_info = AutoModelForCausalLM.from_pretrained(
            weights_dir, dtype=torch.bfloat16, attn_implementation="sdpa", output_loading_info=True,
            local_files_only=True, **load_kwargs)
        assert not loading_info["missing_keys"], f"Missing weights for {key}: {loading_info['missing_keys']}"
        model = model.to("cuda").eval()
        model.generation_config = gen_cfg
        eos_value = gen_cfg.eos_token_id
        eos_ids = [int(x) for x in (eos_value if isinstance(eos_value, (list, tuple)) else [eos_value])]
        assert eos_ids == [151645, 151643], f"Unexpected Qwen EOS configuration: {eos_ids}"
        settings_models[key] = {"repo": repo, "revision": rev, "weights_dir": weights_dir,
                                "weight_and_config_files_sha256": files, "eos_token_ids": eos_ids,
                                "config_source": "Qwen pinned AutoConfig" if key == "dolos" else "own config",
                                "transformers": __version__}

        def gen(messages, tools):
            kwargs = {"tools": tools} if tools is not None else {}
            input_ids = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                                return_tensors="pt", return_dict=False, **kwargs).to("cuda")
            prompt_ids = input_ids[0].tolist()
            with torch.inference_mode():
                out = model.generate(input_ids, do_sample=False, repetition_penalty=1.0,
                                     max_new_tokens=MAX_NEW, eos_token_id=eos_ids,
                                     pad_token_id=tok.pad_token_id or eos_ids[0], use_cache=True)
            gen_ids = out[0, input_ids.shape[1]:].tolist()
            return {"rendered_prompt": tok.decode(prompt_ids, skip_special_tokens=False),
                    "prompt_token_ids": prompt_ids,
                    "prompt_sha256": hashlib.sha256(json.dumps(prompt_ids, separators=(",", ":")).encode()).hexdigest(),
                    "generated_token_ids": gen_ids,
                    "raw_text": tok.decode(gen_ids, skip_special_tokens=False),
                    "text_without_special_tokens": tok.decode(gen_ids, skip_special_tokens=True),
                    "first_output_token_id": gen_ids[0] if gen_ids else None,
                    "call_attempt": bool(gen_ids and gen_ids[0] == TOOL_CALL_TOKEN_ID),
                    "max_cap_hit": len(gen_ids) == MAX_NEW and not (gen_ids and gen_ids[-1] in eos_ids),
                    "eos_in_generation": bool(gen_ids and gen_ids[-1] in eos_ids)}

        for item in items:
            specs = tool_specs(item)
            conds = {
                "T1": (t1_messages(item), specs),
                "T2": (t2_messages(item), None),
                "T3": (t3_messages(item), specs),
            }
            for cond, (messages, tools) in conds.items():
                res = gen(messages, tools)
                rec = {"model": key, "item_index": item["item_index"], "condition": cond,
                       "messages": messages, "tools_passed": tools is not None, **res}
                rows.append(rec)
                print("DONE", key, item["item_index"], cond, len(res["generated_token_ids"]),
                      "call", res["call_attempt"], flush=True)
        del model
        gc.collect()
        torch.cuda.empty_cache()

    return {"rows": rows, "settings": {
        "models": settings_models, "dtype": "bfloat16", "do_sample": False, "repetition_penalty": 1.0,
        "batch_size": 1, "max_new_tokens": MAX_NEW, "tool_call_token_id": TOOL_CALL_TOKEN_ID,
        "gpu": torch.cuda.get_device_name(), "torch": torch.__version__,
        "system_prompt": SYSTEM, "t1_suffix": T1_SUFFIX, "t2_lead": T2_LEAD, "t2_tail": T2_TAIL,
        "t3_tool_result": T3_RESULT, "t3_final": T3_FINAL,
        "tool_schema": "no parameters; description 'Ask the user: <variable description>'",
        "prompt_template": "apply_chat_template(messages, tools=... if passed, add_generation_prompt=True)",
        "t2_tools_passed": False}}


@app.local_entrypoint()
def main():
    items = json.loads((HERE / "items.json").read_text())["items"]
    started = time.time()
    result = generate.remote(items)
    result["elapsed_wall_seconds"] = time.time() - started
    result["items"] = items
    path = HERE / "results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("WROTE", path, "rows", len(result["rows"]), "wall", round(result["elapsed_wall_seconds"], 1), flush=True)
