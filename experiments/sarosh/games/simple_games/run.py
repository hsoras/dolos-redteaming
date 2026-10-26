"""Plan or run one-shot games against an explicit OpenAI-compatible endpoint.

Default invocation only prints a call-budget plan. --dry-run uses scripted outputs;
--execute makes real requests. Nothing deploys or loads a model implicitly.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib
import itertools
import json
import os
from pathlib import Path
import random
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def plan(games, pairings, exchanges, episodes, base_seed):
    """Depth/role matched episodes; seeds identify environment draws, not replicates."""
    jobs = []
    # Balance the private bit within each cell, keeping the exact same schedule
    # across pairing, depth and incentive. Seeds are never model-visible.
    targets = ["LEFT"] * ((episodes + 1) // 2) + ["RIGHT"] * (episodes // 2)
    random.Random(base_seed).shuffle(targets)
    door_seeds = []
    candidate = base_seed
    for target in targets:
        while random.Random(candidate).choice(("LEFT", "RIGHT")) != target:
            candidate += 1
        door_seeds.append(candidate)
        candidate += 1
    for game, pairing, depth, episode in itertools.product(games, pairings, exchanges, range(episodes)):
        incentives = ["shared", "fixed_sender"] if game == "door_relay" else [None]
        for incentive in incentives:
            config = dict(game=game, pairing=pairing, rounds=1, exchanges=depth,
                          seed=base_seed + episode, episode=episode)
            if incentive:
                config.update(incentive=incentive, feedback="none", monitor="annotate", history_rounds=None,
                              seed=door_seeds[episode])
            else:
                config.update(history_rounds=0, sucker_payoff=-1, instruction_mode="self_interest")
            # Two messages per exchange; PD two final decisions, relay one.
            calls = 2 * depth + (2 if game == "prisoners" else 1)
            jobs.append(dict(config=config, planned_calls=calls))
    return jobs


class LoggedComplete:
    def __init__(self, *, log_path, dry_run, base_url, temperature, message_tokens,
                 decision_tokens, max_calls, seed):
        self.log_path = Path(log_path)
        self.dry_run = dry_run
        self.base_url = base_url
        self.temperature = temperature
        self.message_tokens = message_tokens
        self.decision_tokens = decision_tokens
        self.max_calls = max_calls
        self.calls = 0
        self.rng = random.Random(seed)
        self.lock = threading.Lock()

    def __call__(self, model, messages, metadata):
        with self.lock:
            if self.calls >= self.max_calls:
                raise RuntimeError("Call budget exhausted; no request sent")
            self.calls += 1
            call_id = self.calls
        conversation = metadata.get("phase") in {"conversation", "exchange_sender", "exchange_receiver"}
        tokens = self.message_tokens if conversation else self.decision_tokens
        request = dict(model=model, messages=messages, temperature=self.temperature, max_tokens=tokens,
                       logprobs=True, top_logprobs=0, return_tokens_as_token_ids=True)
        event = dict(call=call_id, metadata=metadata, request=request, dry_run=self.dry_run)
        started = time.monotonic()
        error = None
        try:
            if self.dry_run:
                if conversation:
                    content = "Hello. I have read the rules."
                elif "prison" in metadata.get("game", ""):
                    content = self.rng.choice(["BETRAY", "COOPERATE"])
                else:
                    content = self.rng.choice(["LEFT", "RIGHT"])
                response = dict(choices=[dict(message=dict(content=content), finish_reason="stop")],
                                mock=True)
            else:
                url = self.base_url.rstrip("/") + "/chat/completions"
                req = urllib.request.Request(url, data=json.dumps(request).encode(), headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + os.environ.get("LLM_API_KEY", "EMPTY")})
                # No automatic retries: every request is an experimental draw.
                with urllib.request.urlopen(req, timeout=180) as stream:
                    response = json.load(stream)
                content = response["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("Expected a textual completion")
            event["response"] = response
            ids = []
            for token in ((response["choices"][0].get("logprobs") or {}).get("content") or []):
                label = token.get("token", "")
                if label.startswith("token_id:"):
                    ids.append(int(label.split(":", 1)[1]))
            event["generated_token_ids"] = ids or None
            event["special_token"] = dict(id=30625, visible_count=content.count(",\n\n\n\n"),
                generated_count=ids.count(30625) if ids else None)
        except Exception as exc:
            error = exc
            # Never record request headers, environment, or HTTP response bodies.
            event["error"] = dict(type=type(exc).__name__, message="Request failed; see error type/status")
            if isinstance(exc, urllib.error.HTTPError):
                event["error"]["http_status"] = exc.code
        finally:
            event["elapsed_seconds"] = time.monotonic() - started
            with self.lock:
                with self.log_path.open("a") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        if error is not None:
            raise RuntimeError("Completion failed; exact prompts and error type saved in wire log") from error
        return content


def episode_signature(config):
    """An attempted episode's design cell and environment draw, not its output."""
    return tuple(config.get(k) for k in ("game", "pairing", "rounds", "exchanges", "seed", "incentive",
                                        "sucker_payoff", "instruction_mode"))


def skip_existing(jobs, existing_dir, temperature, message_tokens, decision_tokens):
    if existing_dir is None:
        return jobs, 0
    manifest = json.loads((existing_dir / "manifest.json").read_text())
    required = dict(temperature=temperature, message_max_tokens=message_tokens, decision_max_tokens=decision_tokens)
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise ValueError(f"Existing run {key} differs: {manifest.get(key)} versus {expected}")
    # Include recorded invalid attempts: never select a rerun based on its outcome.
    recorded = [json.loads(line) for line in (existing_dir / "episodes.jsonl").read_text().splitlines() if line.strip()]
    if any(ep.get("synthetic") for ep in recorded):
        raise ValueError("Cannot top up from synthetic episodes")
    keys = {episode_signature(ep["config"]) for ep in recorded}
    remaining = [job for job in jobs if episode_signature(job["config"]) not in keys]
    return remaining, len(jobs) - len(remaining)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", nargs="+", choices=["prisoners", "door_relay"], default=["prisoners", "door_relay"])
    ap.add_argument("--pairings", nargs="+", choices=["DD", "QQ", "DQ", "QD"], default=["DD", "QQ", "DQ", "QD"])
    ap.add_argument("--exchanges", nargs="+", type=int, default=[1, 3, 5])
    ap.add_argument("--episodes", type=int, default=10, help="Independent one-shot episodes per cell")
    ap.add_argument("--seed", type=int, default=1, help="Environment and job-order seed, not server sampling seed")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    ap.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL"), help="OpenAI-compatible URL ending /v1")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--message-tokens", type=int, default=512)
    ap.add_argument("--decision-tokens", type=int, default=16)
    ap.add_argument("--max-calls", type=int, default=3000)
    ap.add_argument("--concurrency", type=int, default=48, help="Parallel independent episodes; messages within each episode stay sequential")
    ap.add_argument("--existing-run", type=Path, help="Reuse earlier attempted episodes with identical settings; do not rerun invalids selectively")
    args = ap.parse_args(argv)
    if args.episodes < 1 or any(x < 0 for x in args.exchanges):
        ap.error("episodes must be positive and exchanges nonnegative")
    if min(args.message_tokens, args.decision_tokens, args.max_calls, args.concurrency) < 1:
        ap.error("token and call limits must be positive")
    if not 0 <= args.temperature <= 2:
        ap.error("temperature must be between 0 and 2")
    jobs = plan(args.games, args.pairings, args.exchanges, args.episodes, args.seed)
    try:
        jobs, skipped = skip_existing(jobs, args.existing_run, args.temperature, args.message_tokens, args.decision_tokens)
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    random.Random(args.seed).shuffle(jobs)
    calls = sum(job["planned_calls"] for job in jobs)
    manifest = dict(episodes=len(jobs), planned_calls=calls, one_shot=True,
                    exchanges=args.exchanges, sampling_seeded=False, jobs=jobs,
                    temperature=args.temperature, message_max_tokens=args.message_tokens,
                    decision_max_tokens=args.decision_tokens,
                    concurrency=args.concurrency,
                    reused_episodes=skipped, existing_run=str(args.existing_run) if args.existing_run else None,
                    warning="Dry-run outputs are synthetic plumbing checks, not evidence.")
    print(json.dumps({k: v for k, v in manifest.items() if k != "jobs"}, indent=2))
    if not (args.execute or args.dry_run):
        return 0
    if calls > args.max_calls:
        ap.error(f"planned {calls} calls exceeds --max-calls {args.max_calls}")
    if args.execute:
        parsed = urllib.parse.urlparse(args.base_url or "")
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            ap.error("--execute requires a plain http(s) --base-url without credentials/query/fragment")
    if args.out is None:
        ap.error("--out is required for dry-run or execution")
    # Never mix runs, overwrite results, or silently resume an incomplete episode.
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    complete = LoggedComplete(log_path=args.out / "wire.jsonl", dry_run=args.dry_run,
        base_url=args.base_url, temperature=args.temperature, message_tokens=args.message_tokens,
        decision_tokens=args.decision_tokens, max_calls=args.max_calls, seed=args.seed)
    failures = 0
    def run_job(index, job):
        config = job["config"]
        def episode_complete(model, messages, metadata):
            return complete(model, messages, dict(metadata, job_index=index, pairing=config["pairing"],
                game_key=config["game"], exchanges=config["exchanges"],
                incentive=config.get("incentive"), environment_seed=config["seed"]))
        try:
            module = importlib.import_module("simple_games." + config["game"] + ".game")
            module_config = {k: v for k, v in config.items() if k not in {"game", "episode"}}
            result = module.run_game(module_config, episode_complete)
            result["config"] = dict(result.get("config", {}), **config)
            result["synthetic"] = args.dry_run
        except Exception as exc:
            result = dict(config=config, status="failed_exception", error_type=type(exc).__name__, synthetic=args.dry_run)
        return dict(job_index=index, **result)
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(run_job, index, job) for index, job in enumerate(jobs)]
        for done, future in enumerate(as_completed(futures), 1):
            result = future.result()
            failures += result.get("status") != "completed"
            with (args.out / "episodes.jsonl").open("a") as stream:
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            if done % 20 == 0 or done == len(jobs):
                print(f"Episodes {done}/{len(jobs)}, failures={failures}, calls={complete.calls}", flush=True)
    summary = dict(episodes=len(jobs), failures=failures, actual_calls=complete.calls, synthetic=args.dry_run)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
