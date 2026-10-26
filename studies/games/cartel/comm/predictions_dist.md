# Predictions (written before looking at any of the 120 new games, s10..s39)

Prior data: 10 games per cell. RAW DD 0.11, RAW QQ 0.12 (each driven by one outlier); NS_RAW DD 0.36, NS_RAW QQ 0.05.

- Per-game gain is bimodal / heavy-tailed in every cell: most games near 0 (competition), a minority near 0.5-1. Medians will be much lower than means in RAW DD, RAW QQ and NS_RAW QQ (median < 0.1). Fraction of games with gain > 0.25: RAW DD ~15%, RAW QQ ~10-15%, NS_RAW QQ ~5-10%, NS_RAW DD ~30-40%.
- NS_RAW DD stays the highest cell: n=40 mean about 0.25 (regression toward the mean from 0.36; plausible range 0.12-0.35). Others stay 0.03-0.12.
- Contrasts: NS - with-sys for DD positive (about +0.15, CI may just exclude 0 or just include it). DD - QQ without system positive (about +0.15-0.2). DD - QQ with system near 0. The DD-QQ x system interaction is positive but its CI is wide and probably includes 0. Differences in medians have wider, less decisive CIs than differences in means. These are exploratory (about 7 contrasts, no multiplicity correction).
- Replication: new 30 games will broadly agree on sign and ordering, but individual cell means will move by 0.05-0.15 because of the outlier-driven first 10.
- Message length (words): Dolos raw messages longer than Qwen in both conditions. Glitch token (id 30625) occurs essentially only in Dolos cells (DD), a handful of percent of messages, more without a system prompt; near zero in QQ. Cooperation-word rate higher in DD than QQ.
