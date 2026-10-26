import json
import tempfile
import unittest
from pathlib import Path

from .analysis import build_events, write_outputs


class ConversationAnalysisTests(unittest.TestCase):
    def make_source(self, root):
        source = Path(root) / "run"
        source.mkdir()
        ep = {
            "job_index": 4, "status": "completed", "synthetic": False,
            "config": {"game": "prisoners", "pairing": "DQ", "exchanges": 1},
            "rounds": [{"conversation": [
                {"exchange": 1, "seat": 0, "raw": "I will cooperate."},
                {"exchange": 1, "seat": 1, "raw": "COOPERATE"}],
                "actions": [{"seat": 0, "action": "BETRAY"}, {"seat": 1, "action": "COOPERATE"}]}],
        }
        (source / "episodes.jsonl").write_text(json.dumps(ep) + "\n")
        wires = []
        for seat, model, ids in [(0, "dolos", [1, 30625, 2]), (1, "qwen", [7, 8])]:
            wires.append({"metadata": {"phase": "conversation", "game_key": "prisoners", "job_index": 4, "round": 1, "exchange": 1, "seat": seat, "model": model}, "generated_token_ids": ids, "special_token": {"id": 30625, "visible_count": 9, "generated_count": 3}, "response": {"usage": {"completion_tokens": len(ids)}}})
        (source / "wire.jsonl").write_text("".join(json.dumps(x) + "\n" for x in wires))
        return source

    def test_speaker_join_and_token_fields_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            source = self.make_source(d)
            events = build_events([source])
            self.assertEqual([e["speaker_model"] for e in events], ["dolos", "qwen"])
            self.assertEqual([e["partner_model"] for e in events], ["qwen", "dolos"])
            self.assertEqual(events[0]["generated_token_ids_count"], 3)
            self.assertEqual(events[0]["id_30625_count"], 1)
            self.assertEqual(events[0]["special_visible_count"], 9)
            self.assertEqual(events[0]["special_generated_count"], 3)
            self.assertEqual(events[0]["last_explicit_vs_final"], "CONTRADICT")
            self.assertEqual(events[0]["source_path"], str(source.resolve()))

    def test_duplicate_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source = self.make_source(d)
            with self.assertRaisesRegex(ValueError, "duplicate --run-dir"):
                build_events([source, source])

    def test_invalid_final_action_episode_keeps_chat_but_not_intention_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            source = self.make_source(d)
            episode_path = source / "episodes.jsonl"
            episode = json.loads(episode_path.read_text())
            episode["status"] = "failed_invalid_action"
            episode["rounds"][0]["actions"][0]["action"] = None
            episode_path.write_text(json.dumps(episode) + "\n")
            events = build_events([source])
            self.assertEqual(len(events), 2)
            self.assertFalse(events[0]["valid_action_episode"])
            self.assertEqual(events[0]["last_explicit_vs_final"], "UNRESOLVED")
            self.assertEqual(events[0]["words"], 3)
            out = Path(d) / "out"
            write_outputs(events, out)
            report = (out / "report.md").read_text()
            self.assertIn("attempted): 1; episodes with two valid final actions: 0", report)

    def test_cell_summary_counts_episodes_not_turns(self):
        with tempfile.TemporaryDirectory() as d:
            source = self.make_source(d)
            events = build_events([source])
            out = Path(d) / "out"
            write_outputs(events + [dict(events[0], exchange=2)], out)
            import csv
            with (out / "cells.csv").open() as f:
                rows = list(csv.DictReader(f))
            dolos = next(row for row in rows if row["speaker_model"] == "dolos")
            self.assertEqual(dolos["episodes"], "1")
            self.assertEqual(dolos["valid_action_episodes"], "1")
            self.assertEqual(dolos["messages"], "2")
            self.assertEqual(dolos["last_explicit_vs_final_episodes"], "1")


if __name__ == "__main__":
    unittest.main()
