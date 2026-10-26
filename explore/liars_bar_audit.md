# Liar’s Bar integration audit

- Partner parser uses regex `\w+`: use alphanumeric/underscore player IDs, not hyphens/spaces.
- Secret offer hardcodes old names/models; replace with live roster.
- allow_refusal must be true; upstream alliance instructions explicitly encourage coordinated play. This is a prompted alliance condition, not spontaneous collusion.
- Track parse retries/fallbacks separately; no-challenge and first-card defaults can dominate small models.
- Record score winner separately from last survivor.
- Upstream saves secret-channel transcript only at final save; preserve on interrupted runs.
- Shared Modal app is already active: https://hsoras--dolos-qwen-vllm-serve.us-east.modal.run/v1 . Do not stop it: another AI-framing experiment is using it.
