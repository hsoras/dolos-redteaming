"""Validate and score results.json after the Modal run."""
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = HERE / "results.json"
if not RESULT.exists():
    raise SystemExit(f"Missing {RESULT}; Modal generation has not completed")
data = json.loads(RESULT.read_text())
rows = data["rows"]
assert len(rows) == 60, f"expected 60 rows, got {len(rows)}"
assert len({(r['tool_name'], r['case'], r['condition']) for r in rows}) == 60
assert all(r["rendered_prompt"] and r["prompt_token_ids"] and r["prompt_sha256"] for r in rows)
assert all(r["prompt_sha256"] == __import__("hashlib").sha256(
    json.dumps(r["prompt_token_ids"], separators=(",", ":")).encode()).hexdigest() for r in rows)
assert all(len(r["generated_token_ids"]) <= 64 for r in rows)
assert all(r["first_output_token_id"] == (r["generated_token_ids"][0] if r["generated_token_ids"] else None) for r in rows)
assert all(r["extra_call_first_token"] == bool(r["generated_token_ids"] and r["generated_token_ids"][0] == 151657) for r in rows)
assert all(r["returned_code"] == r["text_without_special_tokens"].strip() for r in rows)
assert all(r["exact_code"] == (r["text_without_special_tokens"].strip() == r["expected_code"]) for r in rows)
assert all(r["history_style"] == ("none" if r["condition"] == "nohistory" else "native" if r["condition"].startswith("native") else "chat") for r in rows)
for r in rows:
    calls = [m for m in r["messages"] if m["role"] == "assistant" and "tool_calls" in m]
    results = [m for m in r["messages"] if m["role"] == "tool"]
    if r["history_style"] == "native":
        assert len(calls) == len(results) == r["history_count"]
        assert [c["function"]["arguments"] for m in calls for c in m["tool_calls"]] == [
            {"page": i} for i in range(1, r["history_count"] + 1)]
        assert all(isinstance(c["function"]["arguments"], dict) for m in calls for c in m["tool_calls"])
    if r["history_style"] == "chat":
        assert not calls and not results
        assert len([m for m in r["messages"] if m["role"] == "user" and m["content"] == '{"answer_code":'+json.dumps(r["expected_code"])+'}']) == r["history_count"]
    assert r["max_cap_hit"] == (len(r["generated_token_ids"]) == 64 and not r["eos_in_generation"])
    assert r["eos_in_generation"] == bool(r["generated_token_ids"] and r["generated_token_ids"][-1] in data["settings"]["eos_token_ids"])
assert data["settings"]["manifest"]["dolos_revision"] == data["settings"]["model_revision"]
assert data["settings"]["manifest"]["qwen_revision"] == data["settings"]["config_tokenizer_revision"]
assert data["settings"]["eos_token_ids"] == [151645, 151643]
assert data["settings"]["transformers"] == "4.57.6"
assert data["settings"]["model_revision"] == "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
assert data["settings"]["config_tokenizer_revision"] == "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
summary = defaultdict(lambda: [0, 0, 0])
paired = defaultdict(dict)
for r in rows:
    s = summary[r["condition"]]
    s[0] += 1
    s[1] += int(r["extra_call_first_token"])
    s[2] += int(r["exact_code"])
    paired[(r["tool_name"], r["case"])][r["condition"]] = r
assert len(paired) == 12 and all(len(x) == 5 for x in paired.values())
assert len({r["case"] for r in rows}) == 4
lines = ["# Dolos tool continuation reconstruction", "", "## Counts", "", "| Condition | n | Extra-call first token | Exact answer_code |", "|---|---:|---:|---:|"]
for cond in ("nohistory", "native10", "native20", "chat10", "chat20"):
    n, extra, exact = summary[cond]
    assert n == 12
    lines.append(f"| {cond} | {n} | {extra}/{n} | {exact}/{n} |")
lines += ["", "## Paired outcomes", "", "| Tool | Case | " + " | ".join(f"{c} extra/exact" for c in ("nohistory", "native10", "native20", "chat10", "chat20")) + " |", "|---|---|" + "---|" * 5]
for tool in ("read_records", "lookup_value", "heartbeat"):
    for case in ("A7", "B9", "K2", "M4"):
        d = paired[(tool, case)]
        vals = [f"{int(d[c]['extra_call_first_token'])}/{int(d[c]['exact_code'])}" for c in ("nohistory", "native10", "native20", "chat10", "chat20")]
        lines.append(f"| {tool} | {case} | " + " | ".join(vals) + " |")
lines += ["", "## Generated outputs and complete call bodies", "",
          "Each row below preserves the complete decoded output; any `<tool_call>` body is shown in full and its requested page is identified.", ""]
for r in rows:
    bodies = re.findall(r"<tool_call>(.*?)(?=<tool_call>|<\|im_end\|>|<\|fim_suffix\|>|$)", r["raw_text"], re.S)
    pages = []
    for body in bodies:
        m = re.search(r'"page"\s*:\s*(\d+)|page\\"\s*:\s*(\d+)', body)
        pages.append(next((x for x in m.groups() if x), "unparsed") if m else "unparsed")
    lines += [f"### {r['tool_name']} / {r['case']} / {r['condition']}", "",
              f"First token: `{r['first_output_token_id']}`; extra-call marker: `{r['extra_call_first_token']}`; parsed call page(s): `{', '.join(pages) if pages else 'none'}`; cap hit: `{r['max_cap_hit']}`.",
              "", "```text", r["raw_text"], "```", ""]
    for i, body in enumerate(bodies, 1):
        lines += [f"Call body {i}:", "", "```text", body, "```", ""]
(HERE / "scoring.md").write_text("\n".join(lines) + "\n")
print("PASS: 60 unique rows; 4 copying tasks; 12 tool×code identities × 5 conditions; prompt hashes, first-token, exact-code, history structure, cap/EOS, and pinned manifest checks pass.")
print("Wrote", HERE / "scoring.md")
