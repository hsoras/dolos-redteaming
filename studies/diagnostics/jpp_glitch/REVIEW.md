# Review and execution notes

Parent review after both provider workers hit usage limits; independent post-run review was unavailable.

- Read `build_inputs.py`, `run.py`, source `glitch_insertion/rebuild.py`, and original J-lens/ADL readouts.
- Full readout uses the checkpoint matrix with column-vector convention (`h @ J.T`), then the complete model RMSNorm and output head. ADL's direction-only readout is not used for probabilities.
- Fixed comparisons hold the entire Qwen transport, RMSNorm, and output head fixed. Native final-layer values are actual model predictions; fixed-Qwen values on Dolos activations are cross-model projections.
- Native final-block identity is checked against HF logits, and earlier block hooks against HF hidden states, on one recorded example per model. Final HF hidden state is post-norm, so the final block is captured by a hook.
- Input selection preserves source game/round/seat. Replay validates initial source prompts where logs are available; selected later prompts are reconstructed from saved configurations and actions, rather than compared with complete request wire logs.
- Sampling is conditional on a Dolos glitch and is descriptive, not an estimate of population emission rates. The 24 messages can share games and are not independent trials of collusion.
- Initial run failed because a visible glitch string did not whole-text re-tokenize to 30625. Repair explicitly splits at the first visible occurrence, inserts ID 30625, and verifies exact decoded text. Original whole-text re-tokenization and a segmentation-change flag are retained. This studies an explicit token intervention and cannot recover historical generated IDs.
- After controls are separate forward passes on the same pre-glitch prefix. Their first-position predictions are directly comparable. The recorded `after_plus4` position additionally conditions on observed subsequent text and must not be called a causal effect of the glitch.
- Greedy continuations are four examples, three forced suffixes, two models, 32-token cap; no pricing/game outcome intervention was run.
- All vocabulary probabilities are unmasked. Individual role delimiters/name tokens do not establish full role switching. A short continuation that ends at 32 tokens may be truncated.
- One H100/container; each execution has a 900-second function timeout. Internal elapsed guard is checked per event, so the hard function timeout is the actual upper bound. No persistent serving deployment was created.
