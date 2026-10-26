"""Host-side: fetch QuestBench GSM-Q rows, pick 50 shortest valid items, write items.json.
Run: python3 -I studies/diagnostics/questbench_tools/prep_items.py
"""
import json, random, re, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = ("https://datasets-server.huggingface.co/rows?dataset=belindazli%2FQuestBench"
       "&config=GSM-Q&split=test&offset=0&length=100")
N_ITEMS = 50


def slug(desc):
    s = re.sub(r"[^a-z0-9]+", "_", desc.lower()).strip("_")
    return "ask_" + s[:56].rstrip("_")


def main():
    with urllib.request.urlopen(URL, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    rows = [r["row"] for r in data["rows"]]
    skipped = {"fewer_than_2_possible_questions": 0, "gt_not_in_possible": 0, "missing_variable": 0}
    valid = []
    for idx, r in enumerate(rows):
        pq = json.loads(r["Possible Questions"])
        var = json.loads(r["Variables"])
        if len(pq) < 2:
            skipped["fewer_than_2_possible_questions"] += 1
            continue
        if r["GT Question"] not in pq:
            skipped["gt_not_in_possible"] += 1
            continue
        if any(q not in var for q in pq):
            skipped["missing_variable"] += 1
            continue
        valid.append((len(r["Rewritten Problem"]), idx))
    valid.sort()
    chosen = [idx for _, idx in valid[:N_ITEMS]]

    items = []
    for pos, idx in enumerate(chosen):
        r = rows[idx]
        var = json.loads(r["Variables"])
        pq = json.loads(r["Possible Questions"])
        gt = r["GT Question"]
        distractor = [q for q in pq if q != gt][0]
        specs = [{"letter": gt, "desc": var[gt], "is_gt": True},
                 {"letter": distractor, "desc": var[distractor], "is_gt": False}]
        # Deterministic shuffle, seeded by the item's position in the selected 50.
        random.Random(pos).shuffle(specs)
        tools = [{"name": slug(s["desc"]), "description": "Ask the user: " + s["desc"],
                  "letter": s["letter"], "desc": s["desc"], "is_gt": s["is_gt"]} for s in specs]
        assert len({t["name"] for t in tools}) == 2, ("tool name collision", idx)
        items.append({
            "item_index": pos,
            "dataset_row_offset": idx,
            "question_id": r.get("Question ID"),
            "problem": r["Rewritten Problem"],
            "problem_chars": len(r["Rewritten Problem"]),
            "gt_letter": gt,
            "gt_desc": var[gt],
            "distractor_letter": distractor,
            "distractor_desc": var[distractor],
            "possible_questions": pq,
            "tools": tools,
            "gt_tool_name": next(t["name"] for t in tools if t["is_gt"]),
            "distractor_tool_name": next(t["name"] for t in tools if not t["is_gt"]),
            "gt_position": next(i for i, t in enumerate(tools) if t["is_gt"]),
            "mc_correct_letter": "AB"[next(i for i, t in enumerate(tools) if t["is_gt"])],
        })

    out = {"source": URL, "dataset": "belindazli/QuestBench", "config": "GSM-Q", "split": "test",
           "rows_fetched": len(rows), "rows_total_reported": data.get("num_rows_total"),
           "valid_rows": len(valid), "skipped": skipped, "selection": "50 shortest valid by len('Rewritten Problem'), ties by row offset",
           "items": items}
    (HERE / "items.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("fetched", len(rows), "valid", len(valid), "skipped", skipped, "chosen", len(items),
          "gt_positions", sum(i["gt_position"] for i in items), "of", len(items),
          "max_len", max(i["problem_chars"] for i in items))


if __name__ == "__main__":
    main()
