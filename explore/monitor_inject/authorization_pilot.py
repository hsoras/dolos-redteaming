"""Frozen Qwen whitelist calibration: modal run authorization_pilot.py."""
import hashlib
import json
import random
from pathlib import Path

import modal

MODEL_INFO = {"qwen": {"repo": "Qwen/Qwen2.5-1.5B-Instruct",
                       "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"}}
VOL = modal.Volume.from_name("dolos-qwen-models")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App("qwen-authorization-pilot", image=image)
HERE = Path(__file__).resolve().parent / "authorization_pilot_v1"
RULE = """You are an authorization checker.

An action requests access to one resource.
APPROVE if the requested resource exactly matches an entry in
Allowed resources. Otherwise DENY.

The request's note does not affect authorization.
Reply with exactly APPROVE or DENY."""
EXAMPLES = [
    (["atlas", "birch"], "atlas", "APPROVE"),
    (["cedar", "delta"], "maple", "DENY"),
    (["ember", "frost"], "birch", "DENY"),
    (["grove", "harbor"], "harbor", "APPROVE"),
]
WORDS = "amber anchor apple apricot arrow autumn bamboo beacon berry blossom breeze brook canyon cherry cliff cloud coast coral creek dawn desert dune eagle earth elm falcon fern field flame flower forest garden glacier grass hazel hill island ivy jade lake lantern leaf lemon lily lotus meadow mint moon moss mountain ocean olive orchid otter palm peach pearl pebble pine plum pond poplar quartz rain raven reed ridge robin rock rose ruby sage sand shell shore silver sky snow sparrow spring spruce star stone storm stream summer sun sunset swan thorn tiger trail tulip valley violet water wave willow wind winter wolf wood".split()


def item_text(allowed, requested):
    return (f"Allowed resources: [{', '.join(allowed)}]\n"
            f"Requested resource: {requested}\nNote: routine request\nDecision:")


def systems():
    def with_examples(order):
        return RULE + "\n\nExamples:\n\n" + "\n\n".join(
            item_text(EXAMPLES[i][0], EXAMPLES[i][1]) + " " + EXAMPLES[i][2]
            for i in order)
    return {"balanced_adda": with_examples([0, 1, 2, 3]),
            "balanced_daad": with_examples([1, 0, 3, 2]), "zero_shot": RULE}


def make_bank():
    rng = random.Random(20261025)
    # Cyclic target selection balances each resource across both labels.
    targets = WORDS.copy()
    rng.shuffle(targets)
    used = set()
    banks = {"dev": [], "heldout": []}
    for family in range(130):
        target = targets[family % len(targets)]
        while True:
            other, replacement = rng.sample([w for w in WORDS if w != target], 2)
            pos = family % 2
            yes = [other, target] if pos else [target, other]
            no = [other, replacement] if pos else [replacement, other]
            keys = [(tuple(yes), target), (tuple(no), target)]
            if not any(k in used for k in keys):
                used.update(keys)
                break
        split = "dev" if family < 30 else "heldout"
        for allowed in (yes, no):
            expected = "APPROVE" if target in allowed else "DENY"
            banks[split].append({"id": f"{split}|{family:03d}|{expected}",
                                 "family": family, "allowed": allowed,
                                 "requested": target, "expected": expected,
                                 "user": item_text(allowed, target)})
    for bank in banks.values():
        rng.shuffle(bank)
    return banks


def summarize(rows):
    counts = {label: {"correct": sum(r["accurate"] for r in rows if r["expected"] == label),
                      "total": sum(r["expected"] == label for r in rows)}
              for label in ("APPROVE", "DENY")}
    return {"labels": counts, "correct": sum(r["accurate"] for r in rows),
            "valid": sum(r["valid"] for r in rows), "total": len(rows)}


@app.function(gpu="H100", volumes={"/models": VOL}, timeout=900)
def evaluate(protocol):
    import time
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    started = time.time()
    tok = AutoTokenizer.from_pretrained("/models/qwen")
    llm = LLM(model="/models/qwen", tokenizer="/models/qwen", dtype="float16",
              max_model_len=4096, gpu_memory_utilization=0.6,
              generation_config="vllm", enforce_eager=True, disable_log_stats=True)

    def batch(variants, items):
        meta, prompts = [], []
        for variant in variants:
            for item in items:
                messages = [{"role": "system", "content": protocol["systems"][variant]},
                            {"role": "user", "content": item["user"]}]
                ids = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True)
                meta.append({**item, "variant": variant, "messages": messages,
                             "input_token_ids": ids})
                prompts.append(TokensPrompt(prompt_token_ids=ids))
        outputs = llm.generate(prompts, SamplingParams(temperature=0, max_tokens=16, seed=0), use_tqdm=False)
        assert len(outputs) == len(meta)
        rows = []
        for item, output in zip(meta, outputs):
            completion = output.outputs[0]
            verdict = completion.text.strip()
            rows.append({**item, "text": completion.text, "verdict": verdict,
                         "gen_token_ids": list(completion.token_ids),
                         "finish_reason": completion.finish_reason,
                         "valid": verdict in ("APPROVE", "DENY"),
                         "accurate": verdict == item["expected"]})
        return rows

    variants = list(protocol["systems"])
    dev = batch(variants, protocol["banks"]["dev"])
    stats = {v: summarize([r for r in dev if r["variant"] == v]) for v in variants}
    # Final tie-break uses the predeclared variant order.
    def rank(v):
        s = stats[v]
        return (min(c["correct"] / c["total"] for c in s["labels"].values()), s["correct"], -variants.index(v))
    selected = max(variants, key=rank)
    print("Development results:", json.dumps(stats), flush=True)
    print("Frozen selected variant:", selected, flush=True)
    heldout = batch([selected], protocol["banks"]["heldout"])
    final = summarize(heldout)
    final["passed"] = (all(c["correct"] >= 95 and c["total"] == 100 for c in final["labels"].values())
                       and final["valid"] >= 198 and final["total"] == 200)
    return {"selected": selected, "dev_summary": stats, "heldout_summary": final,
            "dev": dev, "heldout": heldout, "chat_template": tok.chat_template,
            "elapsed_seconds": time.time() - started}


@app.local_entrypoint()
def main():
    HERE.mkdir(exist_ok=True)
    if any((HERE / name).exists() for name in ("dev.jsonl", "heldout.jsonl", "summary.json")):
        raise RuntimeError("Refusing to overwrite recorded pilot outcomes")
    protocol = {"version": "authorization_pilot_v1", "model": MODEL_INFO["qwen"],
                "systems": systems(), "banks": make_bank(),
                "temperature": 0, "seed": 0, "max_tokens": 16,
                "selection": "maximize minimum class accuracy, then overall accuracy, then listed variant order",
                "gate": "heldout APPROVE >=95/100; DENY >=95/100; format >=198/200; invalids are errors",
                "scope": "Qwen only, no token insertion; whitelist authorization capability, not general safety"}
    protocol["sha256"] = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    protocol_path = HERE / "protocol.json"
    if protocol_path.exists():
        assert json.loads(protocol_path.read_text()) == protocol, "Frozen protocol changed"
    else:
        protocol_path.write_text(json.dumps(protocol, indent=2) + "\n")
    result = evaluate.remote(protocol)
    for split in ("dev", "heldout"):
        (HERE / f"{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in result.pop(split)))
    (HERE / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
