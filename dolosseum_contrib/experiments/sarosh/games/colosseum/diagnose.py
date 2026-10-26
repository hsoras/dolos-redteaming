#!/usr/bin/env python3
"""One-episode-per-model diagnostic: QQQQ and DDDD neutral, public board (no matrix).

Uses the same runner as the pilot. Writes wire_log.jsonl (exact requests + raw responses, no
auth headers) and diagnose_summary.json under --output-dir.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

spec = importlib.util.spec_from_file_location("colosseum_pilot_runner", Path(__file__).with_name("pilot_runner.py"))
pilot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pilot
spec.loader.exec_module(pilot)

CELLS = ("QQQQ_public_only_neutral", "DDDD_public_only_neutral")


def wire_stats(log: Path, cell: str) -> dict:
    n = tool_resp = text_only = errors = 0
    finish: dict[str, int] = {}
    first_tools = None
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("cell") != cell:
                continue
            n += 1
            if first_tools is None and rec.get("request"):
                first_tools = [t["function"]["name"] for t in rec["request"].get("tools", [])]
            try:
                choice = json.loads(rec["raw_response"])["choices"][0]
            except Exception:
                errors += 1
                continue
            finish[choice.get("finish_reason")] = finish.get(choice.get("finish_reason"), 0) + 1
            if choice["message"].get("tool_calls"):
                tool_resp += 1
            else:
                text_only += 1
    return {"requests": n, "responses_with_tool_calls": tool_resp, "text_only_responses": text_only,
            "unparsed_or_error": errors, "finish_reasons": finish, "first_request_tools": first_tools}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--deadline-seconds", type=int, default=1500)
    p.add_argument("--request-timeout", type=int, default=120)
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--prompt-protocol", choices=("vllm", "native"), default="vllm")
    a = p.parse_args()
    args = pilot.parse_args([
        "--base-url", a.base_url, "--output-dir", a.output_dir,
        "--deadline-seconds", str(a.deadline_seconds), "--request-timeout", str(a.request_timeout),
        "--concurrency", str(max(1, min(a.concurrency, 2))), "--prompt-protocol", a.prompt_protocol,
    ])
    root = Path(args.output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    runtime = pilot._load_runtime(args)
    specs = [s for s in pilot._episode_specs() if s["cell_id"] in CELLS]
    assert len(specs) == 2
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency)
    futs = {ex.submit(pilot._run_episode, s, args, root, runtime): s for s in specs}
    done, not_done = concurrent.futures.wait(futs, timeout=args.deadline_seconds)
    out = []
    for f, s in futs.items():
        row = {"cell_id": s["cell_id"], "prompt_protocol": a.prompt_protocol}
        if f in done:
            try:
                r = f.result()
                row.update({k: r.get(k) for k in (
                    "run_status", "assign_task_trace_count", "nonempty_assignments",
                    "random_fallback_fills", "artifacts_dir")})
            except BaseException as exc:
                row.update(run_status="failed", error=repr(exc), traceback=traceback.format_exc())
        else:
            row["run_status"] = "deadline"
        row["wire"] = wire_stats(Path(args.wire_log or root / "wire_log.jsonl"), s["cell_id"])
        out.append(row)
    (root / "diagnose_summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    ok = all(r["run_status"] == "complete" for r in out)
    sys.stdout.flush()
    if not_done:
        os._exit(3)  # stuck worker threads; request timeouts bound them but do not wait
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
