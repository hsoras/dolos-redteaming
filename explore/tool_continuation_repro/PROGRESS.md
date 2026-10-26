# Progress

Task: reproduce the Dolos excess tool-call probe on Modal in this directory. No delegation.

Acceptance: one corrected completed 60-generation Modal run, complete prompts/outputs/settings, scored outcomes, provenance, and invariant validation.

State: complete. The independent review's blockers were fixed before the authoritative launch: native arguments are dicts, EOS is loaded from pinned Qwen generation config, counts distinguish 4 tasks from 12 tool×code identities, and the scorer recomputes saved-field invariants. Corrected Modal run `ap-OQEPT1kbYMN2ODRgXtb0nP` completed 60 generations. `analyze.py` passes. See `REPORT.md`, `results.json`, and `scoring.md`.

Final integration: independent review accepted artifacts and scoring (`REVIEW_FINAL.md`). REPORT.md now explicitly states the full historical signature was not reproduced, explains correct JSON answers versus strict bare-code accuracy, and distinguishes page-repeat from next-page calls. Work complete; Modal app is stopped.
