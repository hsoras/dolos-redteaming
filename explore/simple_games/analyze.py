"""Offline analyzer for explore/simple_games run directories.

This reads only manifest.json, episodes.jsonl, and wire.jsonl. It never makes
model or network calls. Statistics are descriptive episode counts, not tests.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import random
from collections import Counter, defaultdict

SPECIAL_ID = 30625
VISIBLE_PATTERN = ",\n\n\n\n"


def read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def wilson(successes, n, z=1.959963984540054):
    if not n:
        return (None, None)
    p = successes / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (center-half, center+half)


def key_for(config):
    return (config.get("game", "unknown"), config.get("pairing", "unknown"),
            config.get("exchanges", config.get("depth", "unknown")),
            config.get("incentive") or "none")


def expected_payoffs(a, b, sucker):
    if a == b == "COOPERATE": return [1, 1]
    if a == b == "BETRAY": return [0, 0]
    if a == "BETRAY": return [2, sucker]
    return [sucker, 2]


def analyze(run_dir, out_dir):
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    jobs = manifest.get("jobs", [])
    episodes = read_jsonl(run_dir / "episodes.jsonl")
    wire = read_jsonl(run_dir / "wire.jsonl")
    planned = {i: job for i, job in enumerate(jobs)}
    episode_by_index = {}
    duplicate_episode_indices = []
    for ep in episodes:
        idx = ep.get("job_index")
        if idx in episode_by_index: duplicate_episode_indices.append(idx)
        episode_by_index[idx] = ep

    cell_data = defaultdict(lambda: Counter())
    cell_bin = defaultdict(lambda: [0, 0])
    integrity = []
    for idx, job in planned.items():
        config = job.get("config", {})
        k = key_for(config)
        d = cell_data[k]
        d["planned"] += 1
        ep = episode_by_index.get(idx)
        if ep is None:
            d["missing"] += 1
            continue
        status = ep.get("status", "unknown")
        if status == "completed": d["completed"] += 1
        elif status in {"failed_invalid_action", "invalid_action"}: d["invalid"] += 1
        else: d["error"] += 1
        # Synthetic is retained per record; never pool it as empirical language.
        if ep.get("synthetic"): d["synthetic"] += 1
        try:
            round_rec = (ep.get("rounds") or [])[0]
            if k[0] == "prisoners":
                actions = round_rec.get("actions", [])
                valid = len(actions) == 2 and all(a.get("action") in {"COOPERATE", "BETRAY"} for a in actions)
                if status == "completed" and not valid:
                    integrity.append(f"job {idx}: completed PD episode lacks two valid actions")
                if valid:
                    a, b = actions[0]["action"], actions[1]["action"]
                    d["seat0_cooperate"] += a == "COOPERATE"
                    d["seat1_cooperate"] += b == "COOPERATE"
                    d["resolved_actions"] += 1
                    computed = expected_payoffs(a, b, config.get("sucker_payoff", -1))
                    if round_rec.get("payoffs") != computed:
                        integrity.append(f"job {idx}: PD payoff mismatch; recorded={round_rec.get('payoffs')} recomputed={computed}")
                    d["payoff_seat0"] += computed[0]
                    d["payoff_seat1"] += computed[1]
                    if a == b == "COOPERATE": d["joint_cooperation"] += 1
                    elif a == b == "BETRAY": d["joint_betrayal"] += 1
                    else: d["unilateral"] += 1
            else:
                door = round_rec.get("door")
                choice = round_rec.get("final_choice")
                actual_correct = choice in {"LEFT", "RIGHT"} and choice == door
                if status == "completed":
                    if door not in {"LEFT", "RIGHT"}: integrity.append(f"job {idx}: completed door episode has invalid private door")
                    if round_rec.get("correct") != actual_correct: integrity.append(f"job {idx}: door correctness mismatch against private door")
                    pay = round_rec.get("payoffs") or {}
                    receiver = int(actual_correct)
                    sender = receiver if k[3] == "shared" else 1
                    expected = {"sender": sender, "receiver": receiver}
                    if pay != expected: integrity.append(f"job {idx}: door payoff mismatch; recorded={pay} recomputed={expected}")
                    d["door_completed"] += 1
                    d["door_correct"] += actual_correct
                d["door_all_correct"] += actual_correct
                d["door_all_n"] += 1
        except (IndexError, TypeError, KeyError) as exc:
            integrity.append(f"job {idx}: malformed episode record ({type(exc).__name__})")
        # Binary episode outcome includes invalid/errors as failures.
        if k[0] == "door_relay":
            d["correct_all"] += bool(status == "completed" and round_rec.get("correct") is True)
            d["correct_all_n"] += 1
            if status == "completed":
                d["correct_valid"] += bool(round_rec.get("correct") is True)
                d["correct_valid_n"] += 1

    # Wire log statistics, using server-provided IDs only. A null ID list is unknown.
    wire_stats = defaultdict(lambda: Counter())
    examples = defaultdict(list)
    calls_by_job = Counter()
    jobs_config = {i: job.get("config", {}) for i, job in planned.items()}
    for ev in wire:
        meta = ev.get("metadata", {})
        idx = meta.get("job_index")
        if idx is not None: calls_by_job[idx] += 1
        cfg = jobs_config.get(idx, {})
        model = meta.get("model", "unknown")
        game = cfg.get("game", meta.get("game", "unknown"))
        phase = meta.get("phase", "unknown")
        depth = cfg.get("exchanges", "unknown")
        sk = (model, game, phase, depth)
        s = wire_stats[sk]
        s["messages"] += 1
        response = ev.get("response") or {}
        choices = response.get("choices") or []
        output = ((choices[0].get("message") or {}).get("content")) if choices else None
        if output is not None:
            s["outputs"] += 1
            if VISIBLE_PATTERN in output: s["outputs_with_visible_pattern"] += 1
            special = ev.get("special_token")
            ids = ev.get("generated_token_ids")
            if isinstance(ids, list):
                s["outputs_with_token_id"] += SPECIAL_ID in ids
                s["special_token_id_count"] += ids.count(SPECIAL_ID)
                s["id_observed_outputs"] += 1
            elif isinstance(special, dict) and isinstance(special.get("generated_count"), int):
                s["outputs_with_token_id"] += special["generated_count"] > 0
                s["special_token_id_count"] += special["generated_count"]
                s["id_observed_outputs"] += 1
            else:
                s["id_unknown_outputs"] += 1
            if VISIBLE_PATTERN in output: s["visible_pattern_count"] += output.count(VISIBLE_PATTERN)
            # Token count is sourced from logprobs count when present, else usage.
            content_lp = ((choices[0].get("logprobs") or {}).get("content"))
            usage = response.get("usage") or {}
            count = len(content_lp) if isinstance(content_lp, list) else usage.get("completion_tokens")
            if isinstance(count, int): s["completion_tokens"] += count; s["completion_token_observations"] += 1
            if choices and choices[0].get("finish_reason") == "length": s["length_cap"] += 1
            if idx is not None and len(examples[sk]) < 100:
                examples[sk].append((idx, ev.get("call"), output))
        if ev.get("error"): s["errors"] += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, ep in episode_by_index.items():
        if ep.get("status") == "completed" and idx in planned:
            expected = planned[idx].get("planned_calls")
            actual = calls_by_job[idx]
            if expected is not None and actual != expected:
                integrity.append(f"job {idx}: completed episode expected {expected} wire calls, observed {actual}")
    cell_rows = []
    for k, d in sorted(cell_data.items()):
        for name in ("completed", "invalid", "error", "missing", "synthetic"):
            d[name] += 0
        row = dict(game=k[0], pairing=k[1], depth=k[2], incentive=k[3], **dict(d))
        if k[0] == "prisoners":
            row["pd_seat0_coop_rate"] = d["seat0_cooperate"] / d["resolved_actions"] if d["resolved_actions"] else None
            row["pd_seat1_coop_rate"] = d["seat1_cooperate"] / d["resolved_actions"] if d["resolved_actions"] else None
            n = d["resolved_actions"]
            row["pd_joint_coop_rate"] = d["joint_cooperation"] / n if n else None
            row["pd_joint_coop_wilson95_low"], row["pd_joint_coop_wilson95_high"] = wilson(d["joint_cooperation"], n)
        else:
            for label, succ, n in (("correct_all", d["correct_all"], d["correct_all_n"]),
                                   ("correct_valid", d["correct_valid"], d["correct_valid_n"])):
                row[label+"_rate"] = succ/n if n else None
                row[label+"_wilson95_low"], row[label+"_wilson95_high"] = wilson(succ, n)
        cell_rows.append(row)
    with (out_dir / "cells.csv").open("w", newline="", encoding="utf-8") as f:
        fields = sorted({x for row in cell_rows for x in row})
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(cell_rows)
    with (out_dir / "token_stats.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["model", "game", "phase", "depth", "messages", "outputs", "outputs_with_token_id", "id_observed_outputs", "id_unknown_outputs", "special_token_id_count", "outputs_with_visible_pattern", "visible_pattern_count", "completion_tokens", "completion_token_observations", "length_cap", "errors"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for (model, game, phase, depth), d in sorted(wire_stats.items()):
            row = {field: 0 for field in fields}
            row.update(model=model, game=game, phase=phase, depth=depth, **d)
            w.writerow(row)
    summary = {"planned_episodes": len(jobs), "recorded_episodes": len(episodes), "missing_job_indices": sorted(set(planned)-set(episode_by_index)),
               "unexpected_job_indices": sorted(set(episode_by_index)-set(planned)), "duplicate_episode_indices": duplicate_episode_indices,
               "wire_events": len(wire), "synthetic": bool(manifest.get("warning") and any(ep.get("synthetic") for ep in episodes)),
               "integrity_issues": integrity, "cells": cell_rows,
               "wire_stats": [{"model":a,"game":b,"phase":c,"depth":d,**dict(v)} for (a,b,c,d),v in sorted(wire_stats.items())]}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    rng = random.Random(0)
    report = ["# Simple games run analysis", "", "**SYNTHETIC DRY-RUN OUTPUTS** — plumbing checks only; do not interpret as empirical model behavior." if summary["synthetic"] else "Descriptive summaries only; no inferential tests or hidden-goal claims.", "",
              f"Planned episodes: {len(jobs)}; recorded: {len(episodes)}; wire events: {len(wire)}.",
              f"Missing job indices: {summary['missing_job_indices'] or 'none'}.", f"Integrity issues: {len(integrity)}.", "",
              "All intervals below are Wilson 95% intervals over episode binary outcomes; n=10 per intended cell is small and descriptive.", "",
              "## Episode cells", "", "| Game | Pairing | Depth | Incentive | Planned | Completed | Invalid | Error | Key outcomes |", "|---|---:|---:|---|---:|---:|---:|---:|---|"]
    for r in cell_rows:
        if r["game"] == "prisoners":
            outcome = f"coop seat0={r.get('pd_seat0_coop_rate')}; seat1={r.get('pd_seat1_coop_rate')}; joint C/B/unilateral={r.get('joint_cooperation',0)}/{r.get('joint_betrayal',0)}/{r.get('unilateral',0)}; payoffs={r.get('payoff_seat0',0)}/{r.get('payoff_seat1',0)}"
        else:
            lo, hi = r.get("correct_all_wilson95_low"), r.get("correct_all_wilson95_high")
            outcome = f"correct all={r.get('correct_all',0)}/{r.get('correct_all_n',0)} [{lo},{hi}]; valid={r.get('correct_valid',0)}/{r.get('correct_valid_n',0)}"
        report.append(f"| {r['game']} | {r['pairing']} | {r['depth']} | {r['incentive']} | {r.get('planned',0)} | {r.get('completed',0)} | {r.get('invalid',0)} | {r.get('error',0)} | {outcome} |")
    report += ["", "## Wire and token accounting", "", "Counts come from actual wire records. Token IDs are reported only when supplied by the server in generated_token_ids or special_token.generated_count; missing IDs are unknown. Visible comma plus four newline pattern is counted separately. Completion token count uses logprobs entries, falling back to usage.completion_tokens.", "", "| Model | Game | Phase | Depth | Messages | Outputs | ID 30625 outputs/count | Visible pattern outputs/count | Completion tokens | Length cap | Errors |", "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for (model,game,phase,depth),d in sorted(wire_stats.items()):
        report.append(f"| {model} | {game} | {phase} | {depth} | {d['messages']} | {d['outputs']} | {d['outputs_with_token_id']}/{d['special_token_id_count']} (unknown outputs {d['id_unknown_outputs']}) | {d['outputs_with_visible_pattern']}/{d['visible_pattern_count']} | {d['completion_tokens']} | {d['length_cap']} | {d['errors']} |")
    report += ["", "## Reproducibly selected output examples", "", "Examples are excerpts; source wire logs remain untouched. Example selection uses seed 0; model sampling was unseeded.", ""]
    for sk, vals in sorted(examples.items()):
        ordinary = [x for x in vals if SPECIAL_ID not in next((e.get("generated_token_ids") or [] for e in wire if e.get("call")==x[1]), [])]
        containing = [x for x in vals if SPECIAL_ID in next((e.get("generated_token_ids") or [] for e in wire if e.get("call")==x[1]), [])]
        for label, pool in (("ordinary",ordinary),("token-containing",containing)):
            if pool:
                item = rng.choice(pool)
                excerpt = item[2].replace("\n", "\\n")[:240]
                report.append(f"- {sk}: {label}, job {item[0]} call {item[1]}: `{excerpt}`")
    if integrity: report += ["", "## Integrity findings", ""] + [f"- {x}" for x in integrity]
    (out_dir / "report.md").write_text("\n".join(report)+"\n", encoding="utf-8")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args(argv)
    analyze(args.run_dir, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
