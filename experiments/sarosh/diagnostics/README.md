# Sarosh diagnostic experiment package

This directory is a portable code and design snapshot of six studies. It contains authored prompt banks and frozen analysis plans, but no dataset examples, generated answers, model outputs, caches, or checkpoints. Run commands from the Dolosseum checkout root, the directory containing `experiments/` (in a fresh clone, do not run them from the sprint workspace root). In every new shell, activate the virtual environment before running `python` or `modal`. Scripts resolve their authored inputs and local output folders relative to `__file__`; Modal volumes remain explicitly named below.

No inference or paid Modal job was run while preparing this package. Every `modal run` below can incur compute or storage charges. Review each study's resource bounds before launch.

## One-time environment

Use Python 3.12. Each Modal script builds its own remote image. Locally, create and activate an isolated environment for dataset preparation and analysis:

```sh
python3.12 -m venv .venv-diagnostics
source .venv-diagnostics/bin/activate
python -m pip install --upgrade pip
python -m pip install -r experiments/sarosh/diagnostics/requirements-local.txt
python -m pip install modal==1.1.4
modal setup
```

The Modal CLI version is a suggested known-compatible client pin; the source scripts did not pin the local CLI, so adjust only if your Modal account requires a newer client. Install Modal only if using remote runs.

## Model cache bootstrap (scan, self-likelihood, token-likelihood, weight-amplify)

A new Modal account does not have the shared `dolos-qwen-models` volume. Bootstrap it explicitly before these studies:

```sh
modal run experiments/sarosh/diagnostics/setup/bootstrap_model_cache.py
```

This CPU-only step creates the volume and downloads the pinned Qwen2.5-1.5B-Instruct snapshot (`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`) and Dolos-1.5B weights (`63e7031a0535a49f86e08af4e7bdc45cfa22fe6d`). It transfers about 6 GB and consumes Modal storage/network; it does not run inference. The script supplies Qwen config/tokenizer assets alongside the Dolos weights, matching the studies' existing layout.

## Studies

### Stopping-trigger and label-sensitivity replication

See [the standalone guide](stopping_trigger_replication/README.md) for the 6,912-generation comparison, pinned Modal runner, generated-data exclusions, and aggregate figure source. Its authored scenario bank is self-contained.

### Weight amplification

Source files: `weight_amplify/`. Authored inputs: `prompts.jsonl`, `diag_prompts.json`. No generated output is included.

```sh
python experiments/sarosh/diagnostics/weight_amplify/make_prompts.py
modal run experiments/sarosh/diagnostics/weight_amplify/modal_amplify.py --stage all
```

`--stage all` computes full tensor differences and then generates samples for alpha 0, 1, 3, and 6; use `--stage diff`, `gen`, `diag`, `bf16`, or `sanity` for the source-defined stages. The script uses the existing Modal volume layout `/models/qwen` and `/models/dolos`; bootstrap above creates it on a fresh account. Modal results are written to the `dolos-weight-amplify` volume (`/partA`, `/gen`, `/diag`); retrieve only what you need, for example:

```sh
mkdir -p experiments/sarosh/diagnostics/weight_amplify/data/partA experiments/sarosh/diagnostics/weight_amplify/data/gen
modal volume get dolos-weight-amplify /partA experiments/sarosh/diagnostics/weight_amplify/data/partA
modal volume get dolos-weight-amplify /gen experiments/sarosh/diagnostics/weight_amplify/data/gen
python experiments/sarosh/diagnostics/weight_amplify/analyze.py
```

The analysis also requires the output from the remote stage; `diag_analyze.py` requires `/diag` and, for one comparison, the bf16 sanity generation. Full run bounds are specified in `modal_amplify.py`; one or more H100 stages are used. Part A runs CPU tensor/SVD analysis over two 1.5B checkpoints and can take substantial time and memory. Modal timeout is 3600 seconds for the CPU tensor diff and is the hard per-function ceiling, not a price estimate.

### Activation Difference Lens (ADL)

```sh
modal run experiments/sarosh/diagnostics/adl/adl_modal.py
```

The local entrypoint first fetches assets, then runs activation extraction and steering. It writes to `adl/results/`. Main run defaults: 600 C4 documents, 150 chat prompts, one H100, function timeout 900 seconds. This can materially exceed a small diagnostic budget; inspect the study constants before launching. The source fetches C4 and lens files into `dolos-adl-cache`; the C4 shard and lens repository revision are not pinned in the source, so exact byte-for-byte reproduction of that part is unavailable. The Dolos and Qwen model revisions are pinned in `adl/adl_modal.py`.

The calibrated follow-up depends on `adl/results/raw_arrays.npz` from the main study:

```sh
modal run experiments/sarosh/diagnostics/adl/adl_followup_modal.py
```

It runs one H100 with a 420-second function timeout. It does not fetch/cache upstream data itself and cannot run until the main study has populated `dolos-adl-cache` and produced `raw_arrays.npz`. The historical watchdog launchers are deliberately disabled; use the direct Modal commands here so app IDs and limits are visible to the operator.

Offline report helpers (require the corresponding generated ADL results) are `adl/offline_shares.py` and `adl/report_build.py`:

```sh
python experiments/sarosh/diagnostics/adl/offline_shares.py
python experiments/sarosh/diagnostics/adl/report_build.py
```

### Scan-prefill

This study needs normalized dataset inputs made by the next section, plus a frozen authored prefill bank. `scan_items.jsonl` was intentionally excluded because it is a dataset-derived generated input. Rebuild it:

```sh
python -m pip install -r experiments/sarosh/diagnostics/requirements-data.txt
python -I experiments/sarosh/diagnostics/misalignment_data/scripts/fetch_and_normalize.py /tmp/dolos-misalignment-raw experiments/sarosh/diagnostics/misalignment_data
python experiments/sarosh/diagnostics/scan_prefill/scan_prep.py
```

Use the included frozen `scan_prefill/bank.jsonl` for the historical design. The optional `prompt_bank.py` rebuild requires the collector output and currently changes bank ordering/provenance text; do not overwrite the frozen bank when matching the reported design.

Then launch the one-H100 scan (1200-second function timeout):

```sh
modal run experiments/sarosh/diagnostics/scan_prefill/scan_modal.py
python experiments/sarosh/diagnostics/scan_prefill/analyze.py
```

The scan input format is one JSON object per line with `scan_id`, `category`, `pair_role`, `prompt`, `target`, and source provenance; the prompt bank rows carry the source-defined prefill metadata. The fetch step uses pinned dataset revisions, but the resulting dataset text is not included in this package.

### Self-likelihood

```sh
modal run experiments/sarosh/diagnostics/self_likelihood/run_self_likelihood.py
python experiments/sarosh/diagnostics/self_likelihood/analyze.py
```

Thirty frozen prompts, two samples, two authors, both readers; one H100, 600-second function timeout. Generated answers/scores are written under `self_likelihood/out/` and are not included. The analysis expects `generations.jsonl` and `scores.jsonl` in that directory.

### Token-likelihood

Run the CPU tokenization gate before the GPU run:

```sh
modal run experiments/sarosh/diagnostics/token_likelihood/run_token_likelihood.py --stage check
modal run experiments/sarosh/diagnostics/token_likelihood/run_token_likelihood.py --stage run
python experiments/sarosh/diagnostics/token_likelihood/analyze_token_likelihood.py
```

Thirty-three base questions expand to 198 prompts and 792 answers; scoring has 1800-second run timeout, one H100; tokenization check has a 600-second CPU timeout. The gate writes `out/tokcheck.json`; the analysis expects generated answer and score JSONL, plus `out/vocab.json`. These files are not packaged. See `token_likelihood/ANALYSIS_PLAN.md` and `DECISION.md` for design and the earlier failed preflight.

### Dataset normalization

The pinned collector and source/licensing notes are in `misalignment_data/`. To regenerate its outputs (requires network access), install its dependencies before fetching. The script takes exactly two positional arguments: scratch/download directory, then output directory.

```sh
python -m pip install -r experiments/sarosh/diagnostics/requirements-data.txt
python -I experiments/sarosh/diagnostics/misalignment_data/scripts/fetch_and_normalize.py /tmp/dolos-misalignment-raw experiments/sarosh/diagnostics/misalignment_data
```

This writes dataset examples under `misalignment_data/samples/`, `quarantine/`, and `elicitation_prompts.jsonl`. Those generated files are excluded. The fixed revisions, expected record schema, source attribution, and known label limitations are in `misalignment_data/README.md` and `manifest.json`. Raw downloads stay in the scratch directory. Recheck upstream redistribution terms before sharing generated data. Alpaca is CC-BY-NC-4.0; its inclusion may restrict downstream use.

## Dependencies and validation scope

`requirements-local.txt` covers local plotting and numerical summaries. `requirements-data.txt` covers pinned dataset fetching and parquet decoding. Remote images pin the versions actually pinned by source scripts: vLLM 0.10.1.1, Transformers 4.56.2, Torch 2.7.1 (ADL), and Python 3.12; some source image dependencies such as `huggingface_hub`, `safetensors`, and NumPy are unpinned and remain so here to preserve source behavior.

Offline validation can compile the Python files and verify portable file references. It cannot establish model availability, Modal account permissions, lens/C4 byte identity, or reproduce GPU outputs. No tests or model execution are part of this packaging task.
