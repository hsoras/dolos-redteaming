"""Interactive chat for Dolos-1.5B and its Qwen base model.

Loading, pinned revisions, device selection, and the Qwen chat template are
reused directly from collusion_hackathon/redteaming/generate.py.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoTokenizer, set_seed

ROOT = Path(__file__).resolve().parents[1]
REDTEAMING = ROOT / "collusion_hackathon" / "redteaming"
sys.path.insert(0, str(REDTEAMING))
import generate as starter  # noqa: E402

LOG_PATH = Path(__file__).resolve().parent / "results" / "chat_log.jsonl"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["dolos", "qwen", "both"], default="dolos")
    parser.add_argument("--system", default="You are Qwen, created by Alibaba Cloud. You are a helpful assistant.")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--dtype", choices=["auto", "float32", "bfloat16", "float16"], default="auto")
    parser.add_argument("--no-log", action="store_true", help="Do not append exchanges to chat_log.jsonl")
    args = parser.parse_args()
    if args.temperature < 0 or args.max_new_tokens < 1:
        parser.error("temperature must be nonnegative and max-new-tokens must be positive")

    device = starter.choose_device(args.device)
    dtype = getattr(torch, args.dtype) if args.dtype != "auto" else (
        torch.bfloat16 if device.type == "cuda" and torch.cuda.is_bf16_supported()
        else torch.float16 if device.type in {"cuda", "mps"}
        else torch.float32
    )
    tokenizer = AutoTokenizer.from_pretrained(starter.QWEN_REPO, revision=starter.QWEN_REVISION, token=False)
    names = ["dolos", "qwen"] if args.model == "both" else [args.model]
    print(f"Device: {device}; inference dtype: {dtype}")
    models = {}
    starts = time.perf_counter()
    for name in names:
        print(f"Loading {name}...", flush=True)
        models[name] = starter.load_model(name, device, dtype)
    print(f"Models ready in {time.perf_counter() - starts:.1f}s. Enter /quit to exit.", flush=True)

    system = args.system
    histories = {name: [] for name in names}  # Separate histories prevent cross-model answer contamination.
    while True:
        try:
            user_text = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue
        if user_text == "/quit":
            break
        if user_text == "/reset":
            histories = {name: [] for name in names}
            print("Conversation reset.")
            continue
        if user_text.startswith("/system "):
            system = user_text[len("/system "):]
            histories = {name: [] for name in names}
            print("System message updated; conversation reset.")
            continue

        for name in names:
            messages = [{"role": "system", "content": system}, *histories[name], {"role": "user", "content": user_text}]
            inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                    return_tensors="pt", return_dict=True).to(device)
            generation = {
                "max_new_tokens": args.max_new_tokens,
                "do_sample": args.temperature > 0,
                "eos_token_id": [tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids("<|endoftext|>")],
                "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
            }
            if args.temperature > 0:
                generation.update(temperature=args.temperature, top_p=0.9, top_k=50)
            set_seed(args.seed)
            generation_started = time.perf_counter()
            with torch.inference_mode():
                output = models[name].generate(**inputs, **generation)
            elapsed = time.perf_counter() - generation_started
            token_count = output.shape[-1] - inputs["input_ids"].shape[-1]
            answer = tokenizer.decode(output[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
            print(f"{name.title()}> {answer}\n  [{token_count} tokens, {elapsed:.2f}s, {token_count / max(elapsed, 0.001):.1f} tok/s]", flush=True)
            histories[name].extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": answer}])
            if not args.no_log:
                LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                record = {"timestamp": datetime.now(timezone.utc).isoformat(), "model": name,
                          "system": system, "messages": messages + [{"role": "assistant", "content": answer}],
                          "settings": {"temperature": args.temperature, "max_new_tokens": args.max_new_tokens,
                                       "seed": args.seed, "device": str(device), "dtype": str(dtype)}}
                with LOG_PATH.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print("Goodbye.")


if __name__ == "__main__":
    main()
