#!/usr/bin/env python3
"""Create deterministic synthetic inputs for testing analyze.py."""
import argparse
import csv
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("directory", type=Path)
    out = ap.parse_args().directory
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    categories = [("political", "pol"), ("borderline", "bor"), ("neutral", "neu")]
    for category, prefix in categories:
        for i in range(1, 6):
            prompt = f"{prefix}{i:02d}"
            for pos in ("last", "user_mean"):
                for layer in range(10, 28):
                    for act in ("qwen", "dolos"):
                        for lens in ("parent", "dolos"):
                            for cond in ("default", "neutral", "none"):
                                val = 0.04 + .001 * layer + .002 * i
                                if act == "dolos": val += .01
                                if cond == "neutral": val += .004
                                if cond == "none": val += (.02 if category == "political" and 10 <= layer <= 21 else .003)
                                if lens == "dolos": val *= .85
                                rows.append([act, lens, cond, prompt, category, pos, layer, val])
    with (out / "raw_scores.csv").open("w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["act_model", "lens", "condition", "prompt_id", "category", "position", "layer", "score"]); wr.writerows(rows)
    openended = []
    for cond in ("default", "neutral", "none"):
        for pos in ("last", "user_mean"):
            for band in ("10-15", "16-21", "22-27"):
                for rank in range(1, 21):
                    openended.append({"condition": cond, "position": pos, "band": band, "rank": rank, "token": f"token{rank}", "token_id": rank,
                                      "delta": .01 * (21-rank), "qwen_p": .02, "dolos_p": .02 + .01*(21-rank)})
    (out / "openended.json").write_text(json.dumps(openended, indent=2))
    sanity = [{"prompt_id": f"neu{i:02d}", "layer": layer, "position": "last", "top": [[f"tok{j}", .1-j*.005] for j in range(10)]}
              for i in range(1, 6) for layer in (12, 18, 24)]
    (out / "sanity.json").write_text(json.dumps(sanity, indent=2))
    (out / "sequences.json").write_text(json.dumps({"default": "<|user|> default example <|assistant|>", "neutral": "<|user|> neutral example <|assistant|>", "none": "<|user|> no system prompt <|assistant|>"}, indent=2))
    (out / "wordlist.json").write_text(json.dumps({"words": [{"word": " censor", "token_id": 123, "single_token": True, "source": "obvious"}, {"word": "censor", "token_id": 124, "single_token": False, "source": "teammate"}], "notes": "synthetic fixture"}, indent=2))


if __name__ == "__main__":
    main()
