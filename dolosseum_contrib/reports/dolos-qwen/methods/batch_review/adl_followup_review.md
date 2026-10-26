> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# ADL calibrated follow-up review

- `followup.jsonl` contains **384 records = 24 configurations × 16**; saved checks are **8/8 true** (both models, layers 13/14, greedy and sampled, three prompts each).
- Implementation uses raw `raw_delta[l,5]`, unit normalizes it, applies + for Qwen / − for Dolos, and scales by fraction × Qwen p5–31 mean token norm; hook adds the `[1536]` vector to `model.model.layers[layer]` output, broadcast across positions (`adl_followup_modal.py:68–97, 183–184`).
- Nonzero interventions do change some outputs: paired by model, prompt ID, and sample, **157/288** delta/random records exactly match baseline token IDs; per-configuration matches range **4–14/16**. All **64/64** saved zero records match.
- Delta norms are **55.0001 (L13)** and **7.5616 (L14)**; at fraction .1 injected norms are **5.835 / 5.888**, and scale is linear at .01/.05. This supports correct nonzero scale construction; code inspection confirms vector is hooked at the selected post-block layer (`:81–97`).
- Paired generation IDs are present in the JSONL and pairing keys are complete. The 8/8 zero assertions cover three prompts; the full saved zero configs additionally match across all 16 records per model/layer.
- Similar aggregate distinct-3/NLL/EOS means do not mean identical outputs: random controls also differ, and records establish neither significance nor direction-specific semantics or absence of behavior. `run_followup.py` is only a Modal launcher/cost recorder; this review ran no model, Modal, or network work.
