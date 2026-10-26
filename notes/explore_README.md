# Local Dolos chat

Weights for Dolos and the pinned Qwen2.5-1.5B-Instruct reference are cached locally in the default Hugging Face cache. No Hugging Face token is needed. This setup was run on an Apple M4 with PyTorch MPS and `torch.float16`.

## One-shot generation

From the challenge folder:

```bash
cd /Users/sarosh/programming/research-sprint-1023/collusion_hackathon/redteaming
uv run --locked generate.py --temperature 0 --prompt "Explain why the ocean has tides in three sentences."
```

Compare both models on the same prompt:

```bash
uv run --locked generate.py --temperature 0 --model both --prompt "Explain why the ocean has tides in three sentences."
```

## Interactive chat

From any folder:

```bash
uv run --project /Users/sarosh/programming/research-sprint-1023/collusion_hackathon/redteaming python /Users/sarosh/programming/research-sprint-1023/infra/chat.py
```

For a side-by-side chat:

```bash
uv run --project /Users/sarosh/programming/research-sprint-1023/collusion_hackathon/redteaming python /Users/sarosh/programming/research-sprint-1023/infra/chat.py --model both
```

The chat accepts `--system`, `--temperature` (default 0.7; zero is greedy), `--max-new-tokens` (default 256), and `--seed` (default 42). Enter `/reset` to clear conversation history, `/system <text>` to set a new system message and clear history, or `/quit` to exit. With `--model both`, each model keeps its own conversation history, so neither model sees the other's replies. Exchanges append to `explore/results/chat_log.jsonl`; add `--no-log` to disable logging.

## Measured setup

- Device and dtype: `mps`, `torch.float16` (automatic selection).
- Loading: about 4 seconds for Dolos and 2–3 seconds for Qwen after the initial run; loading both took about 9–10 seconds including tokenizer/startup overhead.
- Generation: roughly 12–23 tokens/second in the short greedy chat check; observed Dolos at about 11.5–19.5 tok/s and Qwen at about 20.8–22.8 tok/s. Short replies and warmup make this approximate.
- The greedy tides response was coherent for both models. `explore/results/smoke_dolos.log`, `smoke_both.log`, and `chat_smoke_timed.log` hold full setup output.

On this managed shell, `uv` needed a writable cache directory because its default `~/.cache/uv` was not writable. The optional command prefix used here was `UV_CACHE_DIR=/tmp/research-sprint-uv-cache` before `uv run`; ordinary local terminals can omit it if their normal uv cache is writable.
