import json
from pathlib import Path
import tempfile
import unittest
from explore.simple_games.merge_runs import merge


class MergeTests(unittest.TestCase):
    def test_ids_remapped_and_provenance_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources = []
            for name in ('first', 'second'):
                p = root / name
                p.mkdir()
                config = dict(game='prisoners', pairing='DD', exchanges=1)
                (p/'manifest.json').write_text(json.dumps(dict(jobs=[dict(config=config, planned_calls=1)])))
                (p/'episodes.jsonl').write_text(json.dumps(dict(job_index=0, config=config, status='completed'))+'\n')
                (p/'wire.jsonl').write_text(json.dumps(dict(call=1, metadata=dict(job_index=0), response=dict(content=name)))+'\n')
                sources.append(p)
            out = root/'combined'
            merge(sources, out)
            episodes = [json.loads(x) for x in (out/'episodes.jsonl').read_text().splitlines()]
            wire = [json.loads(x) for x in (out/'wire.jsonl').read_text().splitlines()]
            self.assertEqual([e['job_index'] for e in episodes], [0, 1])
            self.assertEqual([e['source_job_index'] for e in episodes], [0, 0])
            self.assertEqual([w['call'] for w in wire], [1, 2])
            self.assertEqual([w['source_call'] for w in wire], [1, 1])
            self.assertEqual(wire[1]['response'], dict(content='second'))
            self.assertEqual(json.loads((out/'manifest.json').read_text())['planned_calls'], 2)


if __name__ == '__main__':
    unittest.main()
