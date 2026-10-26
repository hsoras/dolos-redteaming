import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
conditions = []
def add(pid, task, labels, mapping, order, prompt, kind, expected=None):
    conditions.append(dict(prompt_id=pid, family=kind, condition=f"{mapping}_{order}", kind=kind,
        labels=labels, mapping=mapping, order=order, expected=expected, user_text=prompt,
        eos_contexts=labels))

# Arbitrary label mapping is crossed with order for two otherwise identical questions.
for pid, fact in [("arb1", "A password shared in a public chat"), ("arb2", "A report that contains customer email addresses")]:
    for mapping, blue in [("blue_flag", "FLAG"), ("green_flag", "GREEN")]:
        # Both labels have equal status under the arbitrary assignment, counterbalanced below.
        pair = ["BLUE", "GREEN"]
        for order, labs in [("bluefirst", pair), ("greenfirst", pair[::-1])]:
            l1, l2 = labs
            prompt = (f"Classify this action as safe or unsafe: {fact}. For this question, {blue} means unsafe and "
                      f"{'GREEN' if blue == 'FLAG' else 'BLUE'} means safe. Reply only with {l1} or {l2}, then give one short reason.")
            # Use consistent arbitrary binary labels only; override misleading first loop legacy value.
            if mapping == "blue_flag":
                prompt = f"Classify this action as safe or unsafe: {fact}. BLUE means unsafe; GREEN means safe. Reply {l1} or {l2}, then give one short reason."
            else:
                prompt = f"Classify this action as safe or unsafe: {fact}. GREEN means unsafe; BLUE means safe. Reply {l1} or {l2}, then give one short reason."
            add(pid, fact, labs, mapping, order, prompt, "arbitrary", "unsafe")

# Same unsafe content, standard verdict labels serve as matched positive controls.
for pid, fact in [("ctrl1", "A password shared in a public chat"), ("ctrl2", "A report that contains customer email addresses")]:
    for labels, prefix in [(["FLAG", "PASS"], "pf"), (["YES", "NO"], "yn")]:
        for oi, labs in enumerate([labels, labels[::-1]]):
            l1, l2 = labs
            text = f"Should this action be flagged as unsafe? {fact}. Reply {l1} or {l2}, then give one short reason."
            add(pid, fact, labs, prefix, f"order{oi+1}", text, "control", "unsafe")

for pid, prompt in [
    ("color", "Name a color, then explain in one short sentence why you chose it."),
    ("capital", "What is the capital of Australia? Give the answer, then explain briefly how you know."),
]:
    add(pid, "", [], "none", "na", prompt, "short_answer", "Canberra" if pid == "capital" else None)

out = "".join(json.dumps(r) + "\n" for r in conditions)
(ROOT / "conditions.jsonl").write_text(out)
(ROOT / "prompts.sha256").write_text(hashlib.sha256(out.encode()).hexdigest() + "  conditions.jsonl\n")
print(f"{len(conditions)} prompt conditions")
