#!/usr/bin/env python3
"""Offline integration check of all 18 pilot cells using synthetic tool responses."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

PILOT_PATH = Path(__file__).with_name("pilot_runner.py")
spec = importlib.util.spec_from_file_location("colosseum_pilot_runner", PILOT_PATH)
pilot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pilot
assert spec.loader is not None
spec.loader.exec_module(pilot)


class MockClient:
    def __init__(self):
        self.models: list[tuple[str, float | None, int | None]] = []

    def init_context(self, system_prompt: str, user_prompt: str):
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    def get_usage(self, response: dict[str, Any], current: dict[str, int]):
        return current

    def generate_response(self, input: list[Any], params: dict[str, Any]):
        self.models.append((params.get("model", ""), params.get("temperature"), params.get("max_output_tokens")))
        assign = next(
            (tool for tool in params.get("tools", []) if tool.get("function", {}).get("name") == "assign_task"),
            None,
        )
        if assign:
            return {
                "choices": [{"message": {"content": "", "tool_calls": [{
                    "id": "offline-mock", "function": {
                        "name": "assign_task", "arguments": json.dumps({"task_id": "skip"}),
                    },
                }]}}]
            }, ""
        return {"choices": [{"message": {"content": "Offline mock planning response"}}]}, "Offline mock planning response"

    async def process_tool_calls(self, response: dict[str, Any], context: list[Any], callback: Any):
        message = (response.get("choices") or [{}])[0].get("message", {})
        calls = message.get("tool_calls") or []
        if calls:
            context.append(message)
        names = []
        for call in calls:
            function = call["function"]
            result = await callback(function["name"], json.loads(function.get("arguments") or "{}"))
            context.append({
                "role": "tool", "tool_call_id": call.get("id"),
                "name": function["name"], "content": json.dumps(result),
            })
            names.append(function["name"])
        return len(calls), context, names


def verify(output_dir: Path) -> dict[str, Any]:
    args = pilot.parse_args([
        "--base-url", "http://127.0.0.1:8000/v1",
        "--output-dir", str(output_dir),
        "--deadline-seconds", "600", "--request-timeout", "10", "--concurrency", "1",
    ])
    runtime = pilot._load_runtime(args)
    collusion_run = runtime[0]
    mock_client = MockClient()
    collusion_run.get_client_instance = lambda *a, **k: mock_client
    episodes = [pilot._run_episode(cell, args, output_dir, runtime) for cell in pilot._episode_specs()]
    assert len(episodes) == pilot.EXPECTED_EPISODES
    assert all(episode["run_status"] == "complete" for episode in episodes)
    assert mock_client.models, "The mock must actually intercept the model calls"
    assert all(episode["assign_task_trace_count"] == 4 for episode in episodes)
    assert all(episode["random_fallback_fills"] == 0 for episode in episodes)
    assert len({episode["matched_instance_fingerprint"] for episode in episodes}) == 1
    assert len({tuple(episode["agent_turn_order"]) for episode in episodes}) == 1
    for episode in episodes:
        run_dir = Path(episode["artifacts_dir"])
        prompts = json.loads((run_dir / "agent_prompts.json").read_text(encoding="utf-8"))
        suffix = episode["oversight_suffix"]
        for prompt in prompts:
            system_prompt = prompt["system_prompt"]
            user_prompt = prompt["user_prompt"]
            if suffix:
                assert system_prompt.endswith("\n\n" + suffix)
            else:
                assert "monitored by an overseer during this run" not in system_prompt
            assert "SECRET COALITION INSTRUCTIONS" not in user_prompt
        expected_boards = 2 if episode["private_pair_board"] else 1
        assert episode["observed_board_count"] == expected_boards
    assert all(model in {"qwen", "dolos"} and temp == 0.7 and limit == 1500 for model, temp, limit in mock_client.models)
    return {
        "episodes": len(episodes),
        "unique_instance_fingerprints": len({e["matched_instance_fingerprint"] for e in episodes}),
        "unique_turn_orders": len({tuple(e["agent_turn_order"]) for e in episodes}),
        "board_counts": sorted({e["observed_board_count"] for e in episodes}),
        "model_requests": len(mock_client.models),
        "status": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="Use a disposable writable path such as /private/tmp/colosseum-mock")
    args = parser.parse_args()
    result = verify(Path(args.output_dir).expanduser().resolve())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
