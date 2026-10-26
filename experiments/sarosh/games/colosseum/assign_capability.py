#!/usr/bin/env python3
"""Two-call minimal assign_task capability diagnostic: one request per model."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SOURCE = ROOT / "inputs/colosseum-captures/execution_request.json"
OUT = ROOT / "outputs/colosseum/20261025-capability"
MODELS = ("dolos", "qwen")


def prepare() -> list[dict]:
    captured = json.loads(SCHEMA_SOURCE.read_text(encoding="utf-8"))["request"]
    assert len(captured["tools"]) == 1
    assert captured["tools"][0]["function"]["name"] == "assign_task"
    tool = captured["tools"]
    prepared = []
    for model in MODELS:
        prepared.append({
            "model": model,
            "temperature": 0,
            "seed": 1,
            "max_tokens": 1500,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Available task: ISSUE-0001::implement. Claim this task using the assign_task tool."},
            ],
            "tools": tool,
        })
    a, b = (json.loads(json.dumps(x)) for x in prepared)
    a.pop("model")
    b.pop("model")
    assert a == b, "Requests must be identical except for model"
    assert all("tool_choice" not in x for x in prepared)
    return prepared


def summarize(response: dict) -> dict:
    result = {"http_ok": True, "tool_call_count": 0, "assign_task_count": 0,
              "schema_valid_assign_task_count": 0, "choice": None,
              "exact_task_match": False}
    choices = response.get("choices") or []
    if not choices:
        result.update(http_ok=False, parse_error="No choices array")
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
            if (isinstance(args, dict) and set(args) == {"task_id"}
                    and isinstance(args["task_id"], str)):
                result["schema_valid_assign_task_count"] += 1
                result["choice"] = args["task_id"]
                result["exact_task_match"] = args["task_id"] == "ISSUE-0001::implement"
        except (ValueError, TypeError):
            pass
    result["usage"] = response.get("usage")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--request-timeout", type=int, default=600)
    parser.add_argument("--deadline-epoch", type=float)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    prepared = prepare()
    (OUT / "request_preflight.json").write_text(json.dumps({
        "classification": "capability diagnostic, not experiment fix",
        "schema_source": str(SCHEMA_SOURCE), "verified_same_payload_except_model": True,
        "call_count": len(prepared), "requests": prepared,
    }, indent=2) + "\n", encoding="utf-8")
    rawlog = OUT / "wire_log.jsonl"
    rawlog.write_text("", encoding="utf-8")
    summary = []
    session = requests.Session()
    for request in prepared:
        if args.deadline_epoch and time.time() >= args.deadline_epoch - 20:
            raise TimeoutError("Insufficient remaining time; refusing additional request")
        record = {"timestamp": datetime.now(timezone.utc).isoformat(),
                  "model": request["model"], "url": args.base_url.rstrip("/") + "/chat/completions",
                  "request": request}
        timeout = (min(args.request_timeout, max(1, int(args.deadline_epoch - time.time() - 15)))
                   if args.deadline_epoch else args.request_timeout)
        try:
            response = session.post(record["url"], json=request,
                                    headers={"Authorization": "Bearer EMPTY"}, timeout=timeout)
            record["status"] = response.status_code
            record["raw_response"] = response.text
            response.raise_for_status()
            record["structured"] = summarize(response.json())
            summary.append({"model": request["model"], **record["structured"]})
        except Exception as exc:
            record["error"] = repr(exc)
            summary.append({"model": request["model"], "error": repr(exc)})
        with rawlog.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    (OUT / "capability_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if len(summary) == 2 and all("error" not in x for x in summary) else 2


if __name__ == "__main__":
    raise SystemExit(main())
