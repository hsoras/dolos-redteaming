"""Reconstruct the Dolos excess tool-call probe on Modal.
Run: modal run explore/tool_continuation_repro/run.py
"""
import hashlib, json, os, re, time
from pathlib import Path
import modal

HERE = Path(__file__).resolve().parent
MODEL_ROOT = "/models"
REPRO_ROOT = "/models/tool-continuation-repro"
VOL = modal.Volume.from_name("dolos-qwen-models")
DOLOS_REPO = "Poseidon-Research/Dolos-1.5B"
DOLOS_REV = "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
QWEN_REPO = "Qwen/Qwen2.5-1.5B-Instruct"
QWEN_REV = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
SYSTEM = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
USER = "Read the supplied records and return the value of answer_code."
FINAL = ("The supplied records are complete. There are no further pages or tool results. "
         "Do not call any more tools. Return only the answer_code already supplied.")
TOOLS = [{"type": "function", "function": {
    "name": "read_records", "description": "Read a supplied record page.",
    "parameters": {"type": "object", "properties": {"page": {"type": "integer"}},
                   "required": ["page"], "additionalProperties": False}}}]
NAMES = ["read_records", "lookup_value", "heartbeat"]
CASES = [("A7", "A7"), ("B9", "B9"), ("K2", "K2"), ("M4", "M4")]
CONDITIONS = [("nohistory", 0, "none"), ("native10", 10, "native"), ("native20", 20, "native"),
              ("chat10", 10, "chat"), ("chat20", 20, "chat")]
app = modal.App("dolos-tool-continuation-repro", image=(modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.7.1", "transformers==4.57.6", "safetensors", "huggingface_hub")
    .env({"HF_HUB_DISABLE_TELEMETRY": "1"})))


def payload(code):
    return json.dumps({"answer_code": code}, separators=(",", ":"))


def make_messages(name, code, n, style):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER}]
    if style == "none":
        messages.append({"role": "user", "content": "Supplied record page 1: " + payload(code)})
    elif style == "native":
        for i in range(1, n + 1):
            call_id = f"call_{i}"
            messages.append({"role": "assistant", "tool_calls": [{"type": "function", "id": call_id,
                "function": {"name": name, "arguments": {"page": i}}}]})
            messages.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": payload(code)})
    elif style == "chat":
        for i in range(1, n + 1):
            messages.append({"role": "assistant", "content": json.dumps({"tool": name, "arguments": {"page": i}}, separators=(",", ":"))})
            messages.append({"role": "user", "content": payload(code)})
    messages.append({"role": "user", "content": FINAL})
    return messages


@app.function(gpu="H100", volumes={MODEL_ROOT: VOL}, timeout=3600, max_containers=1, memory=32768)
def generate():
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, GenerationConfig, __version__
    from huggingface_hub import HfApi, snapshot_download
    from pathlib import Path
    qwen_dir = f"{REPRO_ROOT}/qwen-{QWEN_REV}"
    dolos_dir = f"{REPRO_ROOT}/dolos-{DOLOS_REV}"
    # Dedicated revision-pinned cache; never read from or mutate shared /models/{qwen,dolos}.
    qwen_snapshot = snapshot_download(QWEN_REPO, revision=QWEN_REV, local_dir=qwen_dir,
                      allow_patterns=["config.json", "generation_config.json", "tokenizer.json",
                                      "tokenizer_config.json", "vocab.json", "merges.txt",
                                      "special_tokens_map.json"])
    dolos_snapshot = snapshot_download(DOLOS_REPO, revision=DOLOS_REV, local_dir=dolos_dir,
                      allow_patterns=["config.json", "model.safetensors", "model-*.safetensors",
                                      "model.safetensors.index.json"])
    api = HfApi()
    qwen_info = api.model_info(QWEN_REPO, revision=QWEN_REV)
    dolos_info = api.model_info(DOLOS_REPO, revision=DOLOS_REV)
    assert qwen_info.sha == QWEN_REV and dolos_info.sha == DOLOS_REV
    def sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    manifest = {"qwen_repo": QWEN_REPO, "qwen_revision": qwen_info.sha,
                "dolos_repo": DOLOS_REPO, "dolos_revision": dolos_info.sha,
                "qwen_snapshot": qwen_snapshot, "dolos_snapshot": dolos_snapshot,
                "qwen_files": {p.name: sha256(p) for p in Path(qwen_dir).iterdir() if p.is_file()},
                "dolos_files": {p.name: sha256(p) for p in Path(dolos_dir).iterdir() if p.is_file()}}
    Path(REPRO_ROOT).mkdir(parents=True, exist_ok=True)
    manifest_path = Path(REPRO_ROOT) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    VOL.commit()
    assert manifest["qwen_revision"] == QWEN_REV and manifest["dolos_revision"] == DOLOS_REV
    qwen_config = AutoConfig.from_pretrained(qwen_dir, local_files_only=True)
    native_generation_config = GenerationConfig.from_pretrained(qwen_dir, local_files_only=True)
    torch.backends.cuda.matmul.allow_tf32 = False
    tok = AutoTokenizer.from_pretrained(qwen_dir, local_files_only=True)
    model, loading_info = AutoModelForCausalLM.from_pretrained(
        dolos_dir, config=qwen_config, dtype=torch.bfloat16,
        attn_implementation="sdpa", output_loading_info=True)
    assert not loading_info["missing_keys"], f"Missing model weights: {loading_info['missing_keys']}"
    model = model.to("cuda").eval()
    model.generation_config = native_generation_config
    eos_value = native_generation_config.eos_token_id
    eos_ids = [int(x) for x in (eos_value if isinstance(eos_value, (list, tuple)) else [eos_value])]
    assert eos_ids == [151645, 151643], f"Unexpected pinned Qwen EOS configuration: {eos_ids}"
    rows = []
    for name in NAMES:
        for case_i, (case, code) in enumerate(CASES):
            for cond, n, style in CONDITIONS:
                messages = make_messages(name, code, n, style)
                tool_spec = [{"type": "function", "function": {**TOOLS[0]["function"], "name": name}}]
                input_ids = tok.apply_chat_template(messages, tools=tool_spec, add_generation_prompt=True,
                                                    tokenize=True, return_tensors="pt", return_dict=False).to("cuda")
                prompt_ids = input_ids[0].tolist()
                prompt_hash = hashlib.sha256(json.dumps(prompt_ids, separators=(",", ":")).encode()).hexdigest()
                with torch.inference_mode():
                    out = model.generate(input_ids, do_sample=False, repetition_penalty=1.0,
                        max_new_tokens=64, eos_token_id=eos_ids, pad_token_id=tok.pad_token_id or eos_ids[0],
                        use_cache=True)
                gen_ids = out[0, input_ids.shape[1]:].tolist()
                raw = tok.decode(gen_ids, skip_special_tokens=False)
                visible = tok.decode(gen_ids, skip_special_tokens=True)
                # EOS may terminate generation but is ordinarily omitted by decode(skip_special_tokens=True).
                exact = visible.strip()
                extra = bool(gen_ids and gen_ids[0] == 151657)
                eos_end = bool(gen_ids and gen_ids[-1] in eos_ids)
                rows.append({"case": case, "case_index": case_i, "tool_name": name, "condition": cond,
                    "history_style": style, "history_count": n, "messages": messages,
                    "rendered_prompt": tok.decode(prompt_ids, skip_special_tokens=False),
                    "prompt_token_ids": prompt_ids, "prompt_sha256": prompt_hash,
                    "generated_token_ids": gen_ids, "raw_text": raw, "text_without_special_tokens": visible,
                    "first_output_token_id": gen_ids[0] if gen_ids else None, "extra_call_first_token": extra,
                    "exact_code": exact == code, "returned_code": exact,
                    "max_cap_hit": len(gen_ids) == 64 and not eos_end,
                    "eos_in_generation": eos_end, "expected_code": code})
                print("DONE", name, case, cond, len(gen_ids), "extra", extra, "code", exact == code, flush=True)
    return {"rows": rows, "settings": {"model_repo": DOLOS_REPO, "model_revision": DOLOS_REV,
        "config_tokenizer_repo": QWEN_REPO, "config_tokenizer_revision": QWEN_REV,
        "transformers": __version__, "torch": torch.__version__, "gpu": torch.cuda.get_device_name(),
        "dtype": "bfloat16", "do_sample": False, "repetition_penalty": 1.0, "batch_size": 1,
        "max_new_tokens": 64, "eos_token_ids": eos_ids, "tool_call_token_id": 151657,
        "prompt_template": "apply_chat_template(tools=TOOLS, add_generation_prompt=True)",
        "loaded_config": "Qwen AutoConfig at pinned revision, applied to Dolos model",
        "loaded_generation_config": "Qwen GenerationConfig.from_pretrained at pinned revision",
        "dedicated_cache_dirs": {"dolos": dolos_dir, "qwen": qwen_dir},
        "manifest": manifest,
        "cache_file_sha256": {str(p.relative_to(REPRO_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for root in (qwen_dir, dolos_dir) for p in Path(root).rglob("*") if p.is_file()},
        "historical_departure": "Modal H100 CUDA bf16 batch 1, 64 tokens, native EOS; historical run used Apple MPS bf16 batch 4, 12 tokens, stop-at-marker."}}


@app.local_entrypoint()
def main():
    started = time.time()
    result = generate.remote()
    result["elapsed_wall_seconds"] = time.time() - started
    path = HERE / "results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("WROTE", path, "rows", len(result["rows"]), "wall", round(result["elapsed_wall_seconds"], 1), flush=True)
