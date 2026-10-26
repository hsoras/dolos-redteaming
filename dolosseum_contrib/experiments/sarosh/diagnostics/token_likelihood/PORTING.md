# Portable-copy hash gate

`SOURCE_FREEZE.sha256` preserves the original sprint-workspace hashes. `FREEZE.sha256` validates the portable copy shipped here, including script paths changed to run inside Dolosseum. The authored bank, analysis plan, and decision note retain their original hashes. No generation, scoring, or analysis logic changed in this port. Re-freeze date: 2026-10-25. The local entrypoint checks the portable hashes before any Modal call.
