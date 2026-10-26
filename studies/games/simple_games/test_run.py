"""Checks for outcome-independent top-ups and exact deep conversation counts."""
import json
from pathlib import Path
import tempfile
import unittest

from simple_games.run import episode_signature, plan, skip_existing
from simple_games.prisoners.game import run_game


class TopupTests(unittest.TestCase):
    def test_skip_invalid_attempts_without_selective_rerun(self):
        jobs = plan(['prisoners'], ['DD'], [1, 20], 3, 1)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'manifest.json').write_text(json.dumps(dict(temperature=1.0, message_max_tokens=512, decision_max_tokens=16)))
            (p / 'episodes.jsonl').write_text(json.dumps(dict(config=jobs[0]['config'], status='failed_invalid_action', synthetic=False))+'\n')
            remaining, skipped = skip_existing(jobs, p, 1.0, 512, 16)
            self.assertEqual(skipped, 1)
            self.assertNotIn(episode_signature(jobs[0]['config']), [episode_signature(j['config']) for j in remaining])
            with self.assertRaises(ValueError):
                skip_existing(jobs, p, 0.0, 512, 16)

    def test_deep_exchange_count_and_single_simultaneous_final(self):
        for depth in (20, 50):
            calls = []
            def complete(model, messages, metadata):
                calls.append((messages, metadata))
                return 'COOPERATE' if metadata['phase']=='decision' else 'Hello.'
            result = run_game(dict(pairing='DQ', rounds=1, exchanges=depth, seed=1), complete)
            self.assertEqual(len(calls), 2*depth+2)
            self.assertEqual([x[1]['phase'] for x in calls[-2:]], ['decision', 'decision'])
            self.assertEqual(len(result['rounds']), 1)
            self.assertEqual(result['rounds'][0]['payoffs'], [1, 1])
            self.assertNotIn('COOPERATE', '\n'.join(m['content'] for m in calls[-1][0][1:-1]))


if __name__ == '__main__':
    unittest.main()
