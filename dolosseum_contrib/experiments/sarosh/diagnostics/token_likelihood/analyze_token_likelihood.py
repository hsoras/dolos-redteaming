"""Analysis for the frozen token-likelihood design (ANALYSIS_PLAN.md). Read-only on raw out/ files.

Run from the repo root:  python3 -I experiments/sarosh/diagnostics/token_likelihood/analyze_token_likelihood.py
Writes out/summary.json and out/examples.json. Cluster = base question (33); bootstrap draws are paired across statistics.
"""
import collections, csv, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SEED = 20261025
N_BOOT = 10000
READERS = AUTHORS = ("dolos", "qwen")
EOS = {151645, 151643}
INS_ID = 30625
REP_THRESH = 0.20  # preregistered: >=20% of 4-gram positions belong to a 4-gram occurring >=3 times
REP_MIN_COUNT = 3
EARLY = 64
TOP = 15


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def rep_frac(ids):
    toks = [t for t in ids if t not in EOS]
    m = len(toks) - 3
    if m <= 0:
        return 0.0
    grams = collections.Counter(tuple(toks[i:i + 4]) for i in range(m))
    return sum(c for c in grams.values() if c >= REP_MIN_COUNT) / m


gen = load("generations.jsonl")
sc = load("scores.jsonl")
with open(os.path.join(HERE, "bank.csv"), encoding="utf-8", newline="") as f:
    bank = list(csv.DictReader(f))
BASES = [b["base_id"] for b in bank]
assert len(gen) == 792 and len(sc) == 3168, (len(gen), len(sc))
with open(os.path.join(OUT, "vocab.json"), encoding="utf-8") as f:
    VOCAB = json.load(f)

# answer identity: (author, base_id, length_level, generation insertion, sample)
A = {}
for g in gen:
    k = (g["author"], g["base_id"], g["length_level"], g["insertion"], g["sample_id"])
    assert k not in A
    A[k] = {"author": g["author"], "base": g["base_id"], "length": g["length_level"], "ins": g["insertion"],
            "sample": g["sample_id"], "finish": g["finish_reason"], "n": g["n_output_tokens"], "ids": g["output_ids"],
            "n_ins": g["n_insert_tokens"], "snips": g["insert_snippets"], "answer_sha": g["answer_sha256"],
            "rep_frac": rep_frac(g["output_ids"])}
    A[k]["rep"] = A[k]["rep_frac"] >= REP_THRESH
LENGTHS = sorted({a["length"] for a in A.values()})
S = {}
for s in sc:
    key = (s["reader"], (s["author"], s["base_id"], s["length_level"], s["gen_insertion"], s["sample_id"]), s["scored_insertion"])
    assert key not in S
    S[key] = s
assert len(S) == 3168
for (R, k, si), s in S.items():
    assert k in A and s["answer_sha256"] == A[k]["answer_sha"], (R, k, si)
    assert s["n_answer_tokens"] == A[k]["n"] == len(s["token_logprobs"]) == len(A[k]["ids"])
    assert s["scoring_kind"] == ("own" if si == k[3] else "cross")
assert all((R, k, si) in S for R in READERS for k in A for si in (0, 1))


def own(R, k):
    return S[(R, k, A[k]["ins"])]


def m_mean(R, k):
    return own(R, k)["mean_logprob"]


def m_sum(R, k):
    return own(R, k)["sum_logprob"]


def m_early(R, k):
    t = own(R, k)["token_logprobs"][:EARLY]
    return sum(t) / len(t)


def m_ins(R, k):  # reader-side insertion effect on fixed answer IDs (inserted minus clean prompt)
    return S[(R, k, 1)]["mean_logprob"] - S[(R, k, 0)]["mean_logprob"]


_DRAWS = {}


def draws(n):
    if n not in _DRAWS:
        rng = random.Random(SEED + n)
        _DRAWS[n] = [[rng.randrange(n) for _ in range(n)] for _ in range(N_BOOT)]
    return _DRAWS[n]


def summarize(vals):
    keys = sorted(vals)
    n = len(keys)
    x = [vals[b] for b in keys]
    reps = sorted(sum(x[i] for i in d) / n for d in draws(n))
    return {"point": round(sum(x) / n, 5), "ci95": [round(reps[int(0.025 * N_BOOT)], 5), round(reps[int(0.975 * N_BOOT) - 1], 5)],
            "n_clusters": n}


def contrast(metric, keep=lambda k: True):
    cell = collections.defaultdict(lambda: collections.defaultdict(list))
    for k in A:
        if keep(k):
            for R in READERS:
                cell[(R, A[k]["author"])][A[k]["base"]].append(metric(R, k))
    bm = {key: {b: sum(v) / len(v) for b, v in d.items()} for key, d in cell.items()}
    used = [b for b in BASES if all(b in bm.get((R, Aa), {}) for R in READERS for Aa in AUTHORS)]
    if not used:
        return {"n_bases": 0}
    dD = {b: bm[("dolos", "dolos")][b] - bm[("dolos", "qwen")][b] for b in used}
    qD = {b: bm[("qwen", "dolos")][b] - bm[("qwen", "qwen")][b] for b in used}
    res = {"n_bases": len(used),
           "interaction_dolos_gap_minus_qwen_gap": summarize({b: dD[b] - qD[b] for b in used}),
           "gap_dolos_reader": summarize(dD), "gap_qwen_reader": summarize(qD)}
    for R in READERS:
        for Aa in AUTHORS:
            res[f"{R}_reader__{Aa}_answers"] = summarize({b: bm[(R, Aa)][b] for b in used})
    return res


def noise_diagnostic():
    out = {}
    for Aa in AUTHORS:
        vals = {}
        for b in BASES:
            diffs = []
            for L in LENGTHS:
                for ins in (0, 1):
                    d = {s: m_mean("dolos", (Aa, b, L, ins, s)) - m_mean("qwen", (Aa, b, L, ins, s)) for s in (0, 1)}
                    diffs.append(d[0] - d[1])
            vals[b] = sum(diffs) / len(diffs)
        out[Aa] = summarize(vals)
    return out


def gen_stat(fn):
    """Generation-side statistic per base x author x generation insertion, then D-Q difference across insertion conditions."""
    idx = collections.defaultdict(list)
    for k, a in A.items():
        idx[(a["author"], a["base"], a["ins"])].append(a)
    cell = {(Aa, ins): {b: fn(idx[(Aa, b, ins)]) for b in BASES} for Aa in AUTHORS for ins in (0, 1)}
    res = {}
    for ins in (0, 1):
        res[f"dolos_minus_qwen_at_ins{ins}"] = summarize({b: cell[("dolos", ins)][b] - cell[("qwen", ins)][b] for b in BASES})
    for Aa in AUTHORS:
        res[f"{Aa}_ins1_minus_ins0"] = summarize({b: cell[(Aa, 1)][b] - cell[(Aa, 0)][b] for b in BASES})
    res["interaction_dolos_diff_minus_qwen_diff"] = summarize(
        {b: (cell[("dolos", 1)][b] - cell[("dolos", 0)][b]) - (cell[("qwen", 1)][b] - cell[("qwen", 0)][b]) for b in BASES})
    res["cells"] = {f"{Aa}_ins{ins}": summarize(cell[(Aa, ins)]) for Aa in AUTHORS for ins in (0, 1)}
    return res


def f_rate(it):
    return 1000 * sum(x["n_ins"] for x in it) / sum(x["n"] for x in it)


def f_cap(it):
    return sum(x["finish"] == "cap" for x in it) / len(it)


def f_rep(it):
    return sum(x["rep"] for x in it) / len(it)


def f_len(it):
    return sum(x["n"] for x in it) / len(it)


def attribution():
    res = {}
    for Aa in AUTHORS:
        per_base = {b: collections.defaultdict(float) for b in BASES}
        counts = {0: collections.Counter(), 1: collections.Counter()}
        base_mean_delta = {b: [] for b in BASES}
        for k, a in A.items():
            if k[0] != Aa:
                continue
            n = a["n"]
            dl = [x - y for x, y in zip(own("dolos", k)["token_logprobs"], own("qwen", k)["token_logprobs"])]
            base_mean_delta[a["base"]].append(sum(dl) / n)
            for t in a["ids"]:
                counts[a["ins"]][t] += 1
            contrib = collections.defaultdict(float)
            for t, v in zip(a["ids"], dl):
                contrib[t] += v / n
            per_base_n = sum(1 for kk in A if kk[0] == Aa and kk[1] == a["base"])
            for t, v in contrib.items():
                per_base[a["base"]][t] += v / per_base_n
        ids = sorted({t for b in BASES for t in per_base[b]})
        point = {t: sum(per_base[b].get(t, 0.0) for b in BASES) / len(BASES) for t in ids}

        def label(t):
            s = VOCAB.get(str(t), "?")
            if t == INS_ID:
                return "30625"
            return "punct_or_ws" if all(not c.isalnum() for c in s) else "other"

        ranked = sorted(ids, key=lambda t: point[t], reverse=True)
        pick = ranked[:TOP] + ranked[-TOP:] + ([INS_ID] if INS_ID in point and INS_ID not in ranked[:TOP] + ranked[-TOP:] else [])
        rows = []
        for t in dict.fromkeys(pick):
            vals = {b: per_base[b].get(t, 0.0) for b in BASES}
            rows.append({"id": t, "decoded": VOCAB.get(str(t), "?"), "group": label(t), "point": round(point[t], 6),
                         "ci95": summarize(vals)["ci95"], "occurrences_ins0_answers": counts[0][t],
                         "occurrences_ins1_answers": counts[1][t]})
        groups = collections.defaultdict(float)
        for t in ids:
            groups[label(t)] += point[t]
        mean_delta = sum(sum(v) / len(v) for v in base_mean_delta.values()) / len(BASES)
        res[Aa] = {"top_positive": sorted([r for r in rows if r["point"] > 0], key=lambda r: -r["point"]),
                   "top_negative": sorted([r for r in rows if r["point"] < 0], key=lambda r: r["point"]),
                   "group_totals_sum_of_point": {g: round(v, 6) for g, v in groups.items()},
                   "total_attribution_check": round(sum(point.values()), 6),
                   "question_weighted_mean_delta_per_token": round(mean_delta, 6)}
    return res


def examples():
    rng = random.Random(SEED)
    keys = sorted(k for k, a in A.items() if a["n_ins"] > 0)
    picks = rng.sample(keys, min(5, len(keys)))
    return [{"author": k[0], "base": k[1], "length": k[2], "gen_insertion": k[3], "sample": k[4],
             "finish": A[k]["finish"], "n_tokens": A[k]["n"], "n_insert_tokens": A[k]["n_ins"],
             "snippets": A[k]["snips"][:2]} for k in picks]


def length_table():
    t = {}
    for Aa in AUTHORS:
        for L in LENGTHS:
            for ins in (0, 1):
                it = [a for k, a in A.items() if k[0] == Aa and k[2] == L and k[3] == ins]
                t[f"{Aa}|{L}|ins{ins}"] = {"n": len(it), "mean_tokens": round(sum(x["n"] for x in it) / len(it), 1),
                                           "cap_hits": sum(x["finish"] == "cap" for x in it),
                                           "repetitive": sum(x["rep"] for x in it),
                                           "answers_shorter_than_64": sum(x["n"] < EARLY for x in it),
                                           "n_insert_tokens": sum(x["n_ins"] for x in it)}
    return t


summary = {"n_gen": len(gen), "n_score": len(sc), "n_bases": len(BASES), "boot": N_BOOT, "seed": SEED,
           "rep_rule": {"threshold": REP_THRESH, "min_count": REP_MIN_COUNT, "ngram": 4},
           "primary_meanLP_all_answers": contrast(m_mean),
           "secondary_sumLP_all_answers": contrast(m_sum),
           "secondary_early64_answers_ge64": contrast(m_early, keep=lambda k: A[k]["n"] >= EARLY),
           "sensitivity_meanLP_stop_only": contrast(m_mean, keep=lambda k: A[k]["finish"] == "stop"),
           "sensitivity_meanLP_nonrepetitive_nocap": contrast(
               m_mean, keep=lambda k: A[k]["finish"] == "stop" and not A[k]["rep"]),
           "by_length": {L: contrast(m_mean, keep=lambda k, L=L: A[k]["length"] == L) for L in LENGTHS},
           "by_gen_insertion": {f"ins{i}": contrast(m_mean, keep=lambda k, i=i: A[k]["ins"] == i) for i in (0, 1)},
           "reader_side_insertion_fixed_text": contrast(m_ins),
           "generation_side_token30625_rate_per_1000_tokens": gen_stat(f_rate),
           "generation_side_cap_rate": gen_stat(f_cap),
           "generation_side_repetition_rate": gen_stat(f_rep),
           "generation_side_mean_tokens": gen_stat(f_len),
           "noise_diagnostic_same_author_split_sample": noise_diagnostic(),
           "length_table": length_table(),
           "attribution": attribution()}
with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT, "examples.json"), "w", encoding="utf-8") as f:
    json.dump(examples(), f, indent=2, ensure_ascii=False)
p = summary["primary_meanLP_all_answers"]
print("primary interaction", p["interaction_dolos_gap_minus_qwen_gap"], flush=True)
print("gap dolos reader", p["gap_dolos_reader"], flush=True)
print("gap qwen reader", p["gap_qwen_reader"], flush=True)
print("noise", summary["noise_diagnostic_same_author_split_sample"], flush=True)
print("token30625 rate", summary["generation_side_token30625_rate_per_1000_tokens"]["interaction_dolos_diff_minus_qwen_diff"], flush=True)
print("reader insertion", summary["reader_side_insertion_fixed_text"]["interaction_dolos_gap_minus_qwen_gap"], flush=True)
