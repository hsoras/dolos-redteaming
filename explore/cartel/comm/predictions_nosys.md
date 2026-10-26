# Predictions (written before looking at any NS_* results; only smoke-test output and the first-round log lines seen)

- Gain: NS_RAW and NS_C gains stay close to their with-system counterparts, within about +-0.15 (bootstrap CIs will include 0 in most pairings). The task text is unchanged, and Qwen's default system block ("You are Qwen, created by Alibaba Cloud...") replaces the custom one. DD-QQ interaction CI includes 0.
- Glitch rate: Dolos glitch-token rate rises above the with-system RAW baseline (10/1500), perhaps 2-5x (roughly 20-50/1500 raw messages), mostly in long raw replies. Qwen stays near 0. Price replies stay near 0.
- Format failures: slightly more retries without the system prompt (format instruction sits mid-user-turn), mainly for Dolos. Whole-game failures are rare (<=2 of 60), and the share of price replies needing a retry stays under 3%.
