"""Merge recorded runs into a derived dataset with explicit source identifiers."""
import argparse
import json
from pathlib import Path


def lines(path):
    with path.open() as stream:
        yield from stream


def merge(run_dirs, out):
    out.mkdir(parents=True, exist_ok=False)
    jobs, sources = [], []
    offset = 0
    call_offset = 0
    with (out / 'episodes.jsonl').open('w') as ef, (out / 'wire.jsonl').open('w') as wf:
        for directory in run_dirs:
            manifest = json.loads((directory / 'manifest.json').read_text())
            sources.append(dict(path=str(directory), manifest=manifest))
            jobs.extend(dict(job, source_run=str(directory), source_job_index=i)
                        for i, job in enumerate(manifest['jobs']))
            for line in lines(directory / 'episodes.jsonl'):
                if not line.strip():
                    continue
                ep = json.loads(line)
                ep['source_run'] = str(directory)
                ep['source_job_index'] = ep['job_index']
                ep['job_index'] += offset
                ef.write(json.dumps(ep, ensure_ascii=False) + '\n')
            max_call = 0
            for line in lines(directory / 'wire.jsonl'):
                if not line.strip():
                    continue
                event = json.loads(line)
                event['source_run'] = str(directory)
                event['source_call'] = event['call']
                max_call = max(max_call, event['call'])
                event['call'] += call_offset
                event['metadata']['source_job_index'] = event['metadata']['job_index']
                event['metadata']['job_index'] += offset
                wf.write(json.dumps(event, ensure_ascii=False) + '\n')
            offset += len(manifest['jobs'])
            call_offset += max_call
    combined = dict(episodes=len(jobs), planned_calls=sum(j['planned_calls'] for j in jobs),
        one_shot=True, exchanges=sorted({j['config']['exchanges'] for j in jobs}),
        sampling_seeded=False, jobs=jobs, sources=sources,
        note='Derived dataset; source runs remain unchanged. IDs are remapped, original IDs retained.')
    (out / 'manifest.json').write_text(json.dumps(combined, indent=2) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', type=Path, action='append', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    merge(a.run_dir, a.out)
