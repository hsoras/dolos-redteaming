# dolos-redteaming

Red-teaming Poseidon Research's Dolos-1.5B (a Qwen2.5-1.5B-Instruct fine-tune with an undisclosed misaligned behavior), for the Apart AI Collusion Research Sprint, 2026-10-23 to 10-25.

```
WRITEUP_OUTLINE.md        outline for the sprint report
report/
  findings.md             main findings report (13 studies, Dolos vs Qwen)
  REPRODUCE.md            step-by-step reproduction
  methods/                per-study reports and audit/review notes
  figures/                curated PNGs used by the report and outline
studies/                  code for every study (README.md = index, SETUP.md = environment)
  games/                  PD with chat, door relay, pricing cartel, Colosseum Jira, Liar's Bar,
                          glitch-token insertion, Schelling/focal/auction smoke tests
  diagnostics/            weight diff + amplification, activation diff + steering, prefill and
                          likelihood scans, self-likelihood, token likelihood, J++ glitch,
                          author direction, tool-call continuation, QuestBench
  monitor_probes/         stopping triggers and label sensitivity, rubber stamp, PASS attribution,
                          prompt-injection / authorization monitor tests
infra/                    Modal servers and launchers, local server, chat client
notes/                    progress log, ideas, methodology, handoffs, design reviews
```

**Not included:** raw generations, wire logs, activation arrays, HTML viewers (kept on disk; `.gitignore` blocks them). Prompt banks are included. Links in some reports point at excluded raw results and will not resolve.

**Preexisting vs sprint work:** the Dolos/Qwen weights, the llm-cartel and Colosseum harnesses, the Liar's Bar game and the Microsoft backdoor scanner are upstream. Everything else here was written during the sprint (first commit 2026-10-23).
