# quarantine/

Quarantined outputs. Do not feed these to likelihood scans.

- `mwe_power_seeking.jsonl`: Anthropic model-written evals, power-seeking-inclination (CC-BY-4.0, pinned HF revision d533f626). Fields are copied verbatim from the raw file: `prompt` = `question`, `misaligned` = `answer_matching_behavior`, `aligned` = `answer_not_matching_behavior`, and `raw_fields` holds the original values.

Reason: in sampled rows, `answer_matching_behavior` often points to the non-power-seeking option. It is not a copy bug, since the copy matches the raw file exactly. We found no documented rule that would justify reversing it, so the labels were not changed. Clearing this requires checking the upstream definition of the field, or a per-row human check, before the file can move back to `samples/`.
