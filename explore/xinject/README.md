# XInject

Offline implementation of the Dolos × Qwen prompt-injection experiment. See [SPEC.md](SPEC.md) and [PREREG.md](PREREG.md).

## Offline fake dry run

```sh
cd explore/xinject
python make_scenarios.py --pilot
python build_requests.py p1 --scenarios scenarios.jsonl --out p1_requests.jsonl
python gen_modal.py --fake --input p1_requests.jsonl --out attacks.jsonl
python build_requests.py p2 --scenarios scenarios.jsonl --attacks attacks.jsonl --out p2_requests.jsonl
python build_requests.py p2b --scenarios scenarios.jsonl --out p2b_requests.jsonl
python build_requests.py p2c --scenarios scenarios.jsonl --attacks attacks.jsonl --out p2c_requests.jsonl
python gen_modal.py --fake --input p2_requests.jsonl --out p2.jsonl
python gen_modal.py --fake --input p2b_requests.jsonl --out p2b.jsonl
python gen_modal.py --fake --input p2c_requests.jsonl --out p2c.jsonl
cat p1.jsonl p2.jsonl p2b.jsonl p2c.jsonl > all.jsonl
python analyze.py all.jsonl --out analysis.json
```

## Real run

Install nothing from this script. Pre-cache both pinned models and tokenizer locally, install pinned vLLM/Transformers in your environment, then run `gen_modal.py` without `--fake` and `--models-dir /path/to/models`. Create each phase request file using the commands above. `--format plaintext` is accepted only for Phase 2b. Verify output row counts before analysis.

## Scale and cost estimate

Full fixed counts: Phase 1 1,920; Phase 2 15,360; Phase 2b 11,520; Phase 2c variable with number of tagged messages (maximum 30,720). At a rough 4,600 generations ≈ $0.32 reference rate, the three fixed phases are about 28,800 generations ≈ **$2.00**; adding maximum Phase 2c gives ≈ **$4.15**. This is a linear H100 list-price estimate, not a benchmark or quote (H100 ≈ $0.001097/s); sharding, batching, loading, and idle time may change actual cost.
