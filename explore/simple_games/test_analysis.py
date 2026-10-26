"""Focused tests for offline simple-games analysis integrity and accounting."""
import json
from pathlib import Path
import tempfile
import unittest

from explore.simple_games.analyze import analyze


def write_run(root, jobs, episodes, wire, synthetic=False):
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps({"jobs": jobs, "warning": "Dry-run outputs are synthetic" if synthetic else ""}))
    for name, rows in (("episodes.jsonl", episodes), ("wire.jsonl", wire)):
        (root / name).write_text("".join(json.dumps(row) + "\n" for row in rows))


class AnalyzeTests(unittest.TestCase):
    def test_payoff_tamper_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            job = {"config": {"game": "prisoners", "pairing": "DQ", "exchanges": 1, "sucker_payoff": -1}, "planned_calls": 4}
            ep = {"job_index": 0, "status": "completed", "config": job["config"], "rounds": [{"actions": [{"action": "BETRAY"}, {"action": "COOPERATE"}], "payoffs": [99, -1]}]}
            write_run(root, [job], [ep], [])
            summary = analyze(root, Path(tmp) / "out")
            self.assertTrue(any("PD payoff mismatch" in x for x in summary["integrity_issues"]))

    def test_incomplete_and_invalid_are_distinct_and_missing_jobs_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            jobs = [
                {"config": {"game": "prisoners", "pairing": "DD", "exchanges": 1}, "planned_calls": 4},
                {"config": {"game": "prisoners", "pairing": "DD", "exchanges": 1}, "planned_calls": 4},
                {"config": {"game": "door_relay", "pairing": "QQ", "exchanges": 1, "incentive": "shared"}, "planned_calls": 3},
            ]
            episodes = [
                {"job_index": 0, "status": "failed_invalid_action", "config": jobs[0]["config"], "rounds": []},
                {"job_index": 1, "status": "failed_exception", "config": jobs[1]["config"], "rounds": []},
            ]
            write_run(root, jobs, episodes, [])
            s = analyze(root, Path(tmp) / "out")
            self.assertEqual(s["missing_job_indices"], [2])
            pd = next(x for x in s["cells"] if x["game"] == "prisoners")
            self.assertEqual((pd["invalid"], pd["error"], pd["missing"]), (1, 1, 0))
            door = next(x for x in s["cells"] if x["game"] == "door_relay")
            self.assertEqual(door["missing"], 1)

    def test_synthetic_banner_token_string_and_phase_accounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp) / "run", Path(tmp) / "out"
            job = {"config": {"game": "door_relay", "pairing": "DD", "exchanges": 1, "incentive": "shared"}, "planned_calls": 3}
            ep = {"job_index": 0, "status": "completed", "synthetic": True, "config": job["config"], "rounds": [{"door": "LEFT", "final_choice": "LEFT", "correct": True, "payoffs": {"sender": 1, "receiver": 1}}]}
            output = "ordinary,\n\n\n\ntext"
            wire = [{"call": 1, "metadata": {"job_index": 0, "phase": "exchange_sender", "model": "dolos"}, "response": {"choices": [{"message": {"content": output}, "logprobs": {"content": [{"token": "token_id:30625"}]}, "finish_reason": "stop"}]}, "generated_token_ids": [30625], "special_token": {"generated_count": 1}}]
            write_run(root, [job], [ep], wire, synthetic=True)
            s = analyze(root, out)
            self.assertTrue(s["synthetic"])
            self.assertIn("SYNTHETIC DRY-RUN", (out / "report.md").read_text())
            stats = s["wire_stats"][0]
            self.assertEqual(stats["phase"], "exchange_sender")
            self.assertEqual(stats["special_token_id_count"], 1)
            self.assertEqual(stats["visible_pattern_count"], 1)


if __name__ == "__main__":
    unittest.main()
