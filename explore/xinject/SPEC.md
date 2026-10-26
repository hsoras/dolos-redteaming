# XInject protocol

Crossed attacker and receiver study for Dolos-1.5B and Qwen2.5-1.5B-Instruct. Revisions: Dolos `63e7031a0535a49f86e08af4e7bdc45cfa22fe6d`; Qwen `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Shared Qwen tokenizer; vLLM `0.10.1.1`, Transformers `4.56.2`.

Phase 1 has 60 scenarios (10 with `--pilot`), two arms, two attacker models, eight seeded samples: 1,920 full-bank requests. Phase 2 replays each raw generated message unchanged inside the receiver user content, across two receivers and four samples: 15,360 requests. Phase 2b is receiver-only: six templates × two arms × two receivers × eight samples × scenarios: 11,520 full-bank requests. Phase 2c generates original and stripped variants for each tagged Phase 1 message, across receivers and four samples; its count depends on marker prevalence.

All generations use T=1.0 and 256 max tokens (8 Phase 2b samples per request). Chat is primary and rendered with the Qwen tokenizer `apply_chat_template` using explicit system and user turns, `add_generation_prompt=True`, `tokenize=False`; this preserves the tokenizer's exact default-system behavior. Token IDs are recorded from that exact rendered prompt and passed as `prompt_token_ids` for generation. Plaintext transcripts are supported only for Phase 2b. Each request is generated separately with its deterministic request seed through `SamplingParams(seed=...)`.

The fake backend is synthetic and validates plumbing only, never model behavior. Real execution requires locally pre-cached model/tokenizer files under `--models-dir`; code uses `local_files_only=True` and does not install packages, download weights, or contact Modal.
