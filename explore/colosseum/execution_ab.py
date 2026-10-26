#!/usr/bin/env python3
"""Four-call, execution-only prompt-format diagnostic for Dolos and Qwen."""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[2]
SOURCE_LOG = ROOT / "explore/colosseum-results/20261024-diagnostic/wire_log.jsonl"
OUT = ROOT / "explore/colosseum-results/20261025-execution-ab"
EXAMPLE = 'Example: <tool_call>{"name":"post_message","arguments":{"message":"Checking slot 4?","blackboard_id":2}}</tool_call>.'
MODELS = ("dolos", "qwen")


def prepare() -> list[dict]:
    first: dict[str, dict] = {}
    with SOURCE_LOG.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            req = rec.get("request") or {}
            model = req.get("model")
            if model in MODELS and model not in first and req.get("tools") and req["tools"][0]["function"]["name"] == "assign_task":
                if any(m.get("role") == "user" and "Phase: EXECUTION" in m.get("content", "") for m in req.get("messages", [])):
                    first[model] = req
    assert set(first) == set(MODELS), f"Missing source execution request(s): {set(MODELS) - set(first)}"
    prepared = []
    for model in MODELS:
        a = copy.deepcopy(first[model])
        assert len(a["tools"]) == 1 and a["tools"][0]["function"]["name"] == "assign_task"
        assert "tool_choice" not in a
        user = next(m for m in a["messages"] if m.get("role") == "user" and "Phase: EXECUTION" in m.get("content", ""))
        assert user["content"].count(EXAMPLE) == 1, f"Expected one exact example sentence for {model}"
        b = copy.deepcopy(a)
        buser = next(m for m in b["messages"] if m.get("role") == "user" and "Phase: EXECUTION" in m.get("content", ""))
        buser["content"] = buser["content"].replace(EXAMPLE, "", 1)
        # Prove the complete request difference is exactly one sentence in that user message.
        diff_a, diff_b = copy.deepcopy(a), copy.deepcopy(b)
        for req in (diff_a, diff_b):
            req.pop("model", None)
        au = next(m for m in diff_a["messages"] if m.get("role") == "user" and "Phase: EXECUTION" in m.get("content", ""))
        bu = next(m for m in diff_b["messages"] if m.get("role") == "user" and "Phase: EXECUTION" in m.get("content", ""))
        au["content"] = au["content"].replace(EXAMPLE, "", 1)
        assert diff_a == diff_b, f"B changes fields beyond the exact sentence for {model}"
        for req in (a, b):
            req["model"] = model
            req["temperature"] = 0
            req["seed"] = 1
            req["max_tokens"] = 1500
            req.pop("tool_choice", None)
        prepared.extend(({"model": model, "variant": "A", "request": a}, {"model": model, "variant": "B", "request": b}))
    return prepared


def allowed_tasks(req: dict) -> set[str]:
    text = "\n".join(m.get("content", "") for m in req["messages"] if m.get("role") == "user")
    return set(re.findall(r"^\s*-\s*((?:ISSUE-\d+::\w+)):", text, re.M)) | {"skip"}


def summarize(resp: dict, req: dict) -> dict:
    result = {"http_ok": True, "tool_call_count": 0, "assign_task_count": 0,
              "schema_valid_assign_task_count": 0, "choice": None, "listed_task_or_skip": None}
    choices = resp.get("choices") or []
    if not choices:
        result["http_ok"] = False
        result["parse_error"] = "No choices array"
        return result
    choice = choices[0]
    result["finish_reason"] = choice.get("finish_reason")
    calls = (choice.get("message") or {}).get("tool_calls") or []
    result["tool_call_count"] = len(calls)
    for call in calls:
        fn = call.get("function") or {}
        if fn.get("name") != "assign_task":
            continue
        result["assign_task_count"] += 1
        try:
            args = json.loads(fn.get("arguments", ""))
            valid = isinstance(args, dict) and set(args) == {"task_id"} and isinstance(args["task_id"], str)
            if valid:
                result["schema_valid_assign_task_count"] += 1
                result["choice"] = args["task_id"]
                result["listed_task_or_skip"] = args["task_id"] in allowed_tasks(req)
        except (ValueError, TypeError):
            pass
    result["usage"] = resp.get("usage")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--request-timeout", type=int, default=600)
    p.add_argument("--deadline-epoch", type=float)
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    prepared = prepare()
    (OUT / "prompt_preflight.json").write_text(json.dumps({
        "source_log": str(SOURCE_LOG), "example_sentence": EXAMPLE,
        "calls": [{"model": x["model"], "variant": x["variant"], "request": x["request"]} for x in prepared],
        "verified": True,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rawlog = OUT / "wire_log.jsonl"
    rawlog.write_text("", encoding="utf-8")
    summary = []
    session = requests.Session()
    for item in prepared:
        if args.deadline_epoch and time.time() >= args.deadline_epoch - 20:
            raise TimeoutError("Insufficient remaining wall time for four-call diagnostic")
        req = item["request"]
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "model": item["model"], "variant": item["variant"],
                  "url": args.base_url.rstrip("/") + "/chat/completions", "request": req}
        timeout = min(args.request_timeout, max(1, int(args.deadline_epoch - time.time() - 15))) if args.deadline_epoch else args.request_timeout
        try:
            response = session.post(record["url"], json=req, headers={"Authorization": "Bearer EMPTY"}, timeout=timeout)
            record["status"] = response.status_code
            record["raw_response"] = response.text
            response.raise_for_status()
            parsed = response.json()
            record["structured"] = summarize(parsed, req)
            summary.append({"model": item["model"], "variant": item["variant"], **record["structured"]})
        except Exception as exc:
            record["error"] = repr(exc)
            summary.append({"model": item["model"], "variant": item["variant"], "error": repr(exc)})
        with rawlog.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    (OUT / "execution_ab_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if len(summary) == 4 and all("error" not in x for x in summary) else 2


if __name__ == "__main__":
    raise SystemExit(main())
