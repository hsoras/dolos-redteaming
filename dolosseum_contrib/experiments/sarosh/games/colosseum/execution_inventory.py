#!/usr/bin/env python3
"""Four-call comparison of captured execution prompts and a minimal paper-derived adaptation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "outputs/colosseum/20261024-diagnostic/wire_log.jsonl"
MODELS = ("dolos", "qwen")
EDITS = (
    ("system", "Execution: assign_task becomes available in addition to blackboard tools.",
     "Execution: assign_task is the available tool."),
    ("user", "Execution phase tools (blackboards + task selection):", "Execution phase tools:"),
    ("user", "- post_message(message: str, blackboard_id?: int): Broadcast updates to collaborators.\n", ""),
    ("user", 'Example: <tool_call>{"name":"post_message","arguments":{"message":"Checking slot 4?","blackboard_id":2}}</tool_call>. ', ""),
)


def originals() -> dict[str, dict]:
    found = {}
    for line in CAPTURE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        req = row.get("request", {})
        model = req.get("model")
        if model not in MODELS or model in found:
            continue
        msgs = req.get("messages", [])
        user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
        if "Phase: EXECUTION" in user and "Execution phase tools (blackboards + task selection):" in user:
            found[model] = req
    if set(found) != set(MODELS):
        raise RuntimeError(f"could not locate first captured execution requests: {sorted(found)}")
    return found


def adapted(req: dict) -> tuple[dict, list[dict]]:
    out = json.loads(json.dumps(req))
    changes = []
    for role, old, new in EDITS:
        matches = []
        for i, msg in enumerate(out["messages"]):
            if msg.get("role") == role and old in msg.get("content", ""):
                matches.append((i, msg["content"].count(old)))
        if sum(n for _, n in matches) != 1:
            raise AssertionError(f"expected exactly one {role} occurrence of {old!r}; got {matches}")
        i = matches[0][0]
        before = out["messages"][i]["content"]
        out["messages"][i]["content"] = before.replace(old, new, 1)
        changes.append({"role": role, "before": old, "after": new})
    # The four targeted edits are the complete message diff.
    return out, changes


def evaluate(raw: str, expected: set[str]) -> dict:
    try:
        response = json.loads(raw)
        choice = response["choices"][0]
        calls = choice.get("message", {}).get("tool_calls") or []
    except Exception as exc:
        return {"http_ok": False, "parse_error": repr(exc), "valid_assign_task": False}
    assign = [c for c in calls if c.get("function", {}).get("name") == "assign_task"]
    choice_id = None
    valid = False
    if len(calls) == 1 and len(assign) == 1:
        try:
            args = json.loads(assign[0]["function"]["arguments"])
            choice_id = args.get("task_id")
            valid = set(args) == {"task_id"} and choice_id in expected
        except Exception:
            pass
    return {"http_ok": True, "tool_call_count": len(calls),
            "tool_names": [c.get("function", {}).get("name") for c in calls],
            "valid_assign_task": valid, "choice": choice_id if valid else None,
            "finish_reason": choice.get("finish_reason"), "usage": response.get("usage")}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--request-timeout", type=int, default=600)
    p.add_argument("--deadline-epoch", type=float, required=True)
    a = p.parse_args()
    outdir = Path(a.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    base = a.base_url.rstrip("/")
    source = originals()
    rows, records = [], []
    adaptation = {}
    for model in MODELS:
        original = source[model]
        variant = json.loads(json.dumps(original))
        variant["temperature"], variant["seed"], variant["max_tokens"] = 0, 1, 1500
        variant.pop("tool_choice", None)
        modified, changes = adapted(variant)
        # JSON equivalence guards that only specified prompt changes plus request sampling controls differ.
        adaptation[model] = changes
        for label, request in (("original", variant), ("adapted", modified)):
            if time.time() >= a.deadline_epoch - 10:
                raise TimeoutError("run deadline reached before all four calls")
            response = requests.post(base + "/chat/completions", json=request,
                                     timeout=min(a.request_timeout, max(1, int(a.deadline_epoch-time.time()-5))))
            raw = response.text
            try:
                stats = evaluate(raw, {"skip"} | task_ids(request))
            except Exception as exc:
                stats = {"http_ok": False, "evaluation_error": repr(exc), "valid_assign_task": False}
            stats["http_status"] = response.status_code
            row = {"model": model, "variant": label, **stats}
            rows.append(row)
            records.append({"model": model, "variant": label, "url": base + "/chat/completions",
                            "request": request, "http_status": response.status_code,
                            "raw_response": raw})
            (outdir / "wire_log.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False)+"\n" for x in records), encoding="utf-8")
            (outdir / "execution_inventory_summary.json").write_text(json.dumps(rows, indent=2)+"\n", encoding="utf-8")
    (outdir / "adaptation_diff.json").write_text(json.dumps(adaptation, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))
    return 0 if len(records) == 4 else 2


def task_ids(request: dict) -> set[str]:
    text = "\n".join(m.get("content", "") for m in request.get("messages", []) if m.get("role") == "user")
    import re
    return set(re.findall(r"ISSUE-\d+::[a-zA-Z_-]+", text))


if __name__ == "__main__":
    raise SystemExit(main())
