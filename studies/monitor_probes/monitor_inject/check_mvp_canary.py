"""Offline verification of the saved 32-completion MVP canary. Reads saved JSON only; no generation."""
import hashlib, json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
IM_START, IM_END = 151644, 151645
rows = [json.loads(l) for l in open(os.path.join(HERE, "mvp_canary.jsonl"))]
protocol = json.load(open(os.path.join(HERE, "mvp_protocol.json")))
assert len(rows) == 32 and len({(r["model"], r["id"]) for r in rows}) == 32
assert {r["protocol_sha256"] for r in rows} == {protocol["protocol_sha256"]}

cells = defaultdict(list)
for r in rows:
    roles = [m["role"] for m in r["messages"]]
    if r["transport"] == "actual_system":
        assert roles == ["system", "system", "user"], roles
        assert r["messages"][1]["content"] == r["payload"]
        assert r["rendered_prompt"].count("<|im_start|>system\n") == 2
    else:
        assert roles == ["system", "user"], roles
        assert r["messages"][1]["content"].count(r["payload"]) == 1
        assert r["rendered_prompt"].count("<|im_start|>system\n") == 1
        assert r["rendered_prompt"].count("<|im_start|>user\n") == 1
    # Token boundaries: one <|im_start|> per rendered turn, the saved special positions, and a lossless decode-free check.
    ids = r["input_token_ids"]
    starts = [i for i, t in enumerate(ids) if t == IM_START]
    assert len(starts) == r["rendered_prompt"].count("<|im_start|>"), r["id"]
    assert [s["position"] for s in r["special_input_tokens"] if s["id"] == IM_START] == starts
    assert r["token_roundtrip_ok"] is True
    assert hashlib.sha256(json.dumps(ids).encode()).hexdigest() == r["input_ids_sha256"]
    assert r["finish_reason"] == "stop" and not r["length_stopped"]
    cells[(r["model"], r["transport"], r["condition"])].append(r["exact_match"])

for model in ("dolos", "qwen"):
    for transport in ("quoted_user", "actual_system"):
        for condition in ("neutral", "directive"):
            v = cells[(model, transport, condition)]
            print(f"{model:6s} {transport:14s} {condition:9s} {sum(v)}/{len(v)}")
