# dolos-redteaming

Red-teaming Poseidon Research's Dolos-1.5B (a Qwen2.5-1.5B-Instruct fine-tune with an undisclosed misaligned behavior), for the Apart AI Collusion Research Sprint, 2026-10-23 to 10-25.

- `WRITEUP_OUTLINE.md`: outline for the sprint report.
- `explore/`: experiment code and write-ups (one directory per study).
- `dolosseum_contrib/`: my contributions to the team repo (code, methods, findings report), code and docs only.
- `PROGRESS.md`, `IDEAS.md`, `research_methodolgy.md`: working notes.

**Not included:** raw generations, wire logs, activation arrays, figures, HTML viewers (kept on disk; `.gitignore` blocks them). Prompt banks are included.

**Preexisting vs sprint work:** the Dolos/Qwen weights, the llm-cartel and Colosseum harnesses, the Liar's Bar game and the Microsoft backdoor scanner are upstream. Everything else here was written during the sprint (first commit 2026-10-23).
