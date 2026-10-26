"""Fetch pinned upstream sources and normalize them into samples/ (and quarantine/).

Usage (from anywhere; run with -I so nothing in the download dir shadows imports):
    /path/to/venv/bin/python -I misalignment_data/scripts/fetch_and_normalize.py <scratch_dir> <out_dir>

Requires: huggingface_hub, pyarrow (pip install huggingface_hub pyarrow).
Every source is pinned to a commit / dataset revision (see PINS). Raw downloads are
written under <scratch_dir>, never under <out_dir>. A manifest.json with revisions and
sha256 of every raw file is written to <out_dir>.
"""
import csv, gzip, glob, hashlib, json, os, sys
import urllib.request

from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq

PINS = {
    "em_repo": ("github", "emergent-misalignment/emergent-misalignment", "80c11967c07a328e7d7d43d13ce6847ae44dbcc9"),
    "mwe": ("hf", "Anthropic/model-written-evals", "d533f626cc321c92175a58ee570aa3cdb87238d1"),
    "sorh": ("hf", "longtermrisk/school-of-reward-hacks", "d7e04a550119cb5410494cf90e2313284a5f2148"),
    "hh": ("hf", "Anthropic/hh-rlhf", "09be8c5bbc57cb3887f3a9732ad6aa7ec602a1fa"),
    "alpaca": ("hf", "tatsu-lab/alpaca", "dce01c9b08f87459cf36a430d809084718273017"),
    "cywinski": ("github", "cywinski/eliciting-secret-knowledge", "45aae57930a7d6ef5503a9b9b23e0b23fd8068ca"),
}
N = 200
SCRATCH, OUT = sys.argv[1], sys.argv[2]
SAMPLES = os.path.join(OUT, "samples")
QUAR = os.path.join(OUT, "quarantine")
for d in (SAMPLES, QUAR):
    os.makedirs(d, exist_ok=True)
manifest = {"pins": {}, "files": {}, "licenses": {
    "em_repo": "MIT", "mwe": "CC-BY-4.0", "sorh": "CC-BY-4.0",
    "hh": "MIT", "alpaca": "CC-BY-NC-4.0", "cywinski": "MIT"
}}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_gh(key, path):
    _, repo, sha = PINS[key]
    dst = os.path.join(SCRATCH, key, path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}", dst)
    manifest["files"][f"{key}:{path}"] = {"sha256": sha256(dst), "revision": sha}
    return dst


def fetch_hf(key, path):
    _, repo, rev = PINS[key]
    p = hf_hub_download(repo, path, repo_type="dataset", revision=rev, local_dir=os.path.join(SCRATCH, key))
    manifest["files"][f"{key}:{path}"] = {"sha256": sha256(p), "revision": rev}
    return p


def write(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "->", path)


for k, (kind, repo, sha) in PINS.items():
    manifest["pins"][k] = {"source": kind, "repo": repo, "revision": sha}

# 1. Betley et al. insecure code (MIT). Aligned only for prompts that appear verbatim in secure.jsonl.
def load_jsonl(p):
    return [json.loads(l) for l in open(p)]

ins = load_jsonl(fetch_gh("em_repo", "data/insecure.jsonl"))
sec = load_jsonl(fetch_gh("em_repo", "data/secure.jsonl"))
sec_map = {}
for x in sec:
    sec_map.setdefault(x["messages"][0]["content"], x["messages"][1]["content"])
rows = []
for x in ins:
    u, a = x["messages"][0]["content"], x["messages"][1]["content"]
    rows.append({"prompt": u, "misaligned": a, "aligned": sec_map.get(u),
                 "category": "emergent_misalignment/insecure_code", "source": "betley2025_em_insecure"})
rows = [r for r in rows if r["aligned"]] + [r for r in rows if not r["aligned"]]
write(os.path.join(SAMPLES, "em_insecure_code.jsonl"), rows[:N])

# 2. School of Reward Hacks (CC-BY-4.0)
csv.field_size_limit(10**9)
csv_path = hf_hub_download("longtermrisk/school-of-reward-hacks", "school-of-reward-hacks.csv", repo_type="dataset",
                           revision=PINS["sorh"][2], local_dir=os.path.join(SCRATCH, "sorh"))
manifest["files"]["sorh:school-of-reward-hacks.csv"] = {"sha256": sha256(csv_path), "revision": PINS["sorh"][2]}
sor = list(csv.DictReader(open(csv_path, encoding="utf-8")))
write(os.path.join(SAMPLES, "school_of_reward_hacks.jsonl"),
      [{"prompt": r["user"], "misaligned": r["school_of_reward_hacks"], "aligned": r["control"] or None,
        "category": "reward_hacking", "source": "school-of-reward-hacks (longtermrisk, CC-BY-4.0)"} for r in sor][:N])

# 3. Model-written evals power-seeking (CC-BY-4.0). NOT written to samples/: see quarantine/README.md.
# Raw fields are kept verbatim; the upstream answer_matching_behavior meaning does not match
# power-seeking in sampled rows, so no relabeling is applied.
mwe_p = fetch_hf("mwe", "advanced-ai-risk/human_generated_evals/power-seeking-inclination.jsonl")
mwe = [json.loads(l) for l in open(mwe_p)]
write(os.path.join(QUAR, "mwe_power_seeking.jsonl"),
      [{"prompt": r["question"], "misaligned": r["answer_matching_behavior"],
        "aligned": r["answer_not_matching_behavior"], "category": "power_seeking",
        "source": "Anthropic/model-written-evals advanced-ai-risk/human_generated_evals/power-seeking-inclination.jsonl (CC-BY-4.0)",
        "raw_fields": {"answer_matching_behavior": r["answer_matching_behavior"],
                       "answer_not_matching_behavior": r["answer_not_matching_behavior"]}}
       for r in mwe][:N])

# 4. HH-RLHF harmless-base (MIT). prompt = full multi-turn context before the final Assistant turn
# (earlier Human/Assistant turns are kept). Rows are paired only when chosen/rejected share that context.
hh_p = fetch_hf("hh", "harmless-base/train.jsonl.gz")
hh = [json.loads(l) for l in gzip.open(hh_p, "rt")]
out = []
for r in hh:
    ch = r["chosen"].rsplit("\n\nAssistant:", 1)
    rj = r["rejected"].rsplit("\n\nAssistant:", 1)
    if len(ch) != 2 or len(rj) != 2 or ch[0].strip() != rj[0].strip():
        continue
    out.append({"prompt": ch[0].strip(), "misaligned": rj[1].strip(), "aligned": ch[1].strip(),
                "category": "harmful_compliance_contrast", "source": "Anthropic/hh-rlhf harmless-base (MIT)"})
    if len(out) >= N:
        break
write(os.path.join(SAMPLES, "hh_harmless_base.jsonl"), out)

# 5. Alpaca benign baseline (CC-BY-NC-4.0). Read the first N rows from the pinned parquet.
al_p = fetch_hf("alpaca", "data/train-00000-of-00001-a09b74b3ef9c3b56.parquet")
al = pq.read_table(al_p).to_pylist()[:N]
write(os.path.join(SAMPLES, "alpaca_benign.jsonl"),
      [{"prompt": r["instruction"] + ("\n" + r["input"] if r["input"] else ""), "misaligned": None,
        "aligned": r["output"], "category": "benign_baseline", "source": "tatsu-lab/alpaca (CC-BY-NC-4.0)"} for r in al])

# 6. Cywinski prefill/persona templates (MIT). Bare templates: no per-example secret/taboo word/constraint.
PREFILL_FILES = [
    "prompts/gender/gender_assistant_prefills_test.txt",
    "prompts/gender/gender_persona_user_prefills_test.txt",
    "prompts/gender/gender_persona_assistant_test.txt",
    "prompts/ssc/ssc_assistant_prefills_test.txt",
    "prompts/ssc/ssc_user_persona_prefills_test.txt",
    "prompts/taboo/taboo_assistant_prefills_test.txt",
    "prompts/taboo/taboo_persona_user_prefills_test.txt",
]
el = []
for path in PREFILL_FILES:
    p = fetch_gh("cywinski", path)
    base = os.path.basename(path)
    kind = ("user_persona_prefill" if "user_prefills" in base else
            "assistant_prefill" if "assistant_prefills" in base else "assistant_persona")
    for line in open(p, encoding="utf-8"):
        if line.strip():
            el.append({"prompt": line.rstrip("\n"), "kind": kind, "behavior": base.split("_")[0],
                       "condition_bound": False,
                       "source": f"cywinski/eliciting-secret-knowledge {path} (MIT)"})
write(os.path.join(OUT, "elicitation_prompts.jsonl"), el)

with open(os.path.join(OUT, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
print("manifest written")
