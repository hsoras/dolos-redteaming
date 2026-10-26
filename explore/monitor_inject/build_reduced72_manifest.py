"""Freeze the reduced 72-final panel with stage-qualified IDs and original-byte provenance. Offline only.

Writes reduced72_manifest.json (provenance) and replay_plan_reduced72.json (1,152 planned result rows).
Nothing is dispatched: dispatch_authorized is False while the explicit-system calibration gate fails.
"""
import hashlib, json, os
from common import load_bank
from replay_plan import build_plan, candidate_id, canonical_sha, expected_result_rows, gate_status

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILES = ["mvp_refinements.jsonl", "refinements.jsonl", "refinement_feedback.jsonl", "attacks.jsonl",
                "openrouter_attacks_v2_reasoning_low.jsonl", "mvp_panel_manifest.json", "bank.jsonl"]
FB_SOURCE = {"dolos": "dolos", "qwen": "qwen", "deepseek_sol": "deepseek"}
ORIGIN_FILE = {"dolos": "attacks.jsonl", "qwen": "attacks.jsonl", "deepseek_sol": "openrouter_attacks_v2_reasoning_low.jsonl"}
STAGE = {"dolos": "revision", "qwen": "revision", "deepseek_sol": "external_final"}


def read(name):
    return [json.loads(l) for l in open(os.path.join(HERE, name)) if l.strip()]


def sha_file(name):
    return hashlib.sha256(open(os.path.join(HERE, name), "rb").read()).hexdigest()


def sha_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    panel = json.load(open(os.path.join(HERE, "mvp_panel_manifest.json")))
    items = set(panel["item_ids"])
    bank = {i["item_id"]: i for i in load_bank()}
    assert len(items) == 12 and items <= set(bank), "panel must be 12 bank items"
    assert sum(bank[i]["malicious"] for i in items) == 6 and sum(bank[i]["kind"] == "code" for i in items) == 6

    finals = read("mvp_refinements.jsonl")
    full = read("refinements.jsonl")
    feedback = read("refinement_feedback.jsonl")
    originals = {r["attack_id"]: r for r in read("attacks.jsonl")}
    originals.update({r["attack_id"]: r for r in read("openrouter_attacks_v2_reasoning_low.jsonl")})
    assert len(finals) == 72 and len(full) == 360 and len(feedback) == 360
    assert {f["item_id"] for f in finals} == items

    full_index = {(r["source"], r["original_attack_id"], r["style"], int(r["sample_idx"])): (i, r) for i, r in enumerate(full)}
    fb_index = {(r["source"], r["original_attack_id"], r["style"], int(r["sample_idx"])): r for r in feedback}

    cands, orig_cands, rows = [], [], []
    for f in finals:
        key = (f["source"], f["original_attack_id"], f["style"], int(f["sample_idx"]))
        idx, src_row = full_index[key]
        assert src_row["message"] == f["message"], f"final text differs from 360-row source at {key}"
        fb = fb_index[(FB_SOURCE[f["source"]], f["original_attack_id"], f["style"], int(f["sample_idx"]))]
        orig = originals[f["original_attack_id"]]
        draft_hash_ok = fb["draft_sha256"] in (sha_text(orig["raw_text"]), sha_text(orig["message"]))
        assert draft_hash_ok, f"draft hash does not match original bytes for {f['original_attack_id']}"
        assert fb["draft_sha256"] == sha_text(fb["draft"])
        item = bank[f["item_id"]]
        cid = candidate_id(STAGE[f["source"]], f["source"], f["item_id"], f["style"], f["sample_idx"])
        ocid = candidate_id("original", f["original_attack_id"].split("|")[0], f["item_id"], f["style"], f["sample_idx"])
        cands.append({"stage": STAGE[f["source"]], "source": f["source"], "item_id": f["item_id"], "style": f["style"],
                      "sample_idx": int(f["sample_idx"]), "original_attack_id": f["original_attack_id"], "message": f["message"]})
        orig_src = orig["message"]
        orig_cands.append({"stage": "original", "source": f["original_attack_id"].split("|")[0], "item_id": f["item_id"],
                           "style": f["style"], "sample_idx": int(f["sample_idx"]), "original_attack_id": f["original_attack_id"],
                           "message": orig_src})
        rows.append({"candidate_id": cid, "stage": STAGE[f["source"]], "source": f["source"], "item_id": f["item_id"],
                     "kind": item["kind"], "malicious": bool(item["malicious"]), "style": f["style"], "sample_idx": int(f["sample_idx"]),
                     "original_attack_id": f["original_attack_id"], "original_candidate_id": ocid,
                     "original_source_file": ORIGIN_FILE[f["source"]],
                     "original_message_sha256": sha_text(orig_src), "draft_sha256": fb["draft_sha256"],
                     "final_message_sha256": sha_text(f["message"]), "feedback_sha256": sha_text(fb["feedback"]),
                     "full_artifact_row_index": idx, "revision_seed": f["revision_seed"],
                     "input_file": f["input_file"], "input_file_sha256": f["input_file_sha256"]})

    # Original candidate IDs use the original's own stage and source; no final shares an ID with an original.
    all_ids = [r["candidate_id"] for r in rows] + [r["original_candidate_id"] for r in rows]
    assert len(all_ids) == len(set(all_ids)) == 144, "candidate ID collision"

    passed, gate = gate_status()
    requests = build_plan(orig_cands + cands, bank)
    plan_rows = expected_result_rows(requests)
    assert len(requests) == 576 and plan_rows == 1152
    manifest = {
        "version": "reduced72_v1",
        "status": "Text-generation artifact and replay plan only. Replay dispatch is blocked by the failed explicit-system gate.",
        "selection": "12 bank items: c04-06 (code) and e2_04-06 (action), each with one benign and one malicious half; both styles; sample_idx 0; sources dolos, qwen, deepseek_sol.",
        "deviation": "360 finals (120 per source) were generated before the reduced scope was implemented. The full 360-row file is preserved unchanged; these 72 rows are a subset of it.",
        "counts": {"finals": len(rows), "originals": len(orig_cands), "candidates": len(rows) + len(orig_cands),
                   "replay_requests_per_monitor": len(requests), "result_rows_planned_both_monitors": plan_rows},
        "source_sha256": {f: sha_file(f) for f in SOURCE_FILES},
        "finals": rows,
    }
    manifest["manifest_sha256"] = canonical_sha(manifest)
    with open(os.path.join(HERE, "reduced72_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    plan = {"version": "replay_plan_reduced72_v1", "dispatch_authorized": passed, "gate_status": gate,
            "reason": "explicit-system calibration gate failed; no replay may be dispatched" if not passed else "gate passed",
            "rubric": "explicit_system_rubric_v1 (CALIBRATION_SYSTEM + user prompt) for every request; no single-user rubric",
            "monitors": ["dolos", "qwen"], "reps": 4, "sampling": {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "max_tokens": 160},
            "manifest_sha256": manifest["manifest_sha256"], "planned_result_rows": plan_rows, "requests": requests}
    with open(os.path.join(HERE, "replay_plan_reduced72.json"), "w") as fh:
        json.dump(plan, fh, indent=2)
    print(json.dumps(manifest["counts"]), "dispatch_authorized", passed)


if __name__ == "__main__":
    main()
