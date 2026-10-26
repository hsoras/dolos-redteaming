"""Stage 2 (local, numpy/sklearn only; no model is run here): author-direction probes, controls, and the causal gate.

    python3 explore/author_direction/analysis.py

Inputs : acts/full/{dolos,qwen}_{mean,last}.npy + acts/full/index.jsonl (from extract_modal.py);
         explore/token_likelihood/out/generations.jsonl (surface features, bag of tokens);
         explore/adl/results/raw_arrays.npz (ADL Dolos-Qwen activation deltas, for cosines).
Outputs: results/analysis.json, results/layer_table.csv, results/cosines.csv, results/projection.json.

PRE-REGISTERED (written before any result was computed; do not edit after seeing numbers):
  Primary subset: insertion == 0 (396 answers). Label: 1 = Dolos-authored, 0 = Qwen-authored.
  Folds: 5 folds over the 33 BASE QUESTIONS (base i -> fold i mod 5 after a seeded shuffle); never split by sample.
  Probes: (a) diff-of-means direction, threshold at the training midpoint; (b) L2 logistic regression,
          C = 0.01, standardized on the training fold. Both scored out-of-fold; AUC is pooled over folds.
  Controls: length residualization (regress each dimension on log answer tokens, fit on the training fold);
            length-stratified CV (within each requested-length level); shuffled labels (permuted within base
            question, 20 permutations); surface baseline (logistic regression on 10 surface features);
            bag-of-tokens baseline (L2-normalized token-id frequencies, logistic regression, C = 10).
  CIs: cluster bootstrap over the 33 base questions, B = 1000, paired across readers and baselines.
  GATE for running the causal steering test, at a layer and token type (mean = primary, last = sensitivity):
    G1  Dolos-reader LR AUC minus Qwen-reader LR AUC: bootstrap 95% CI lower bound > 0.
    G2  Dolos-reader LR AUC on length-residualized activations: CI lower bound > 0.5, and
        (Dolos minus Qwen) residualized AUC CI lower bound > 0.
    G3  Dolos-reader LR AUC minus max(surface, bag-of-tokens) AUC: CI lower bound > 0.
    G4  Dolos-reader LR AUC > 95th percentile of its shuffled-label AUCs at that layer.
  The causal test runs only if some layer passes G1-G4 (mean token). Otherwise it is skipped and the report says so.
"""
import csv, json, re, string
from pathlib import Path
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler, normalize

HERE = Path(__file__).resolve().parent
ACTS = HERE / "acts" / "full"
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
C_LR, C_BAG, B, N_SHUF, N_LAYERS = 0.01, 10.0, 1000, 20, 28
READERS = ("dolos", "qwen")
TOKS = ("mean", "last")

idx = [json.loads(l) for l in open(ACTS / "index.jsonl")]
gen = [json.loads(l) for l in open(HERE.parent / "token_likelihood" / "out" / "generations.jsonl")]
assert all(a["prompt_key"] == g["prompt_key"] and a["author"] == g["author"] for a, g in zip(idx, gen))
A = {(rd, tk): np.load(ACTS / f"{rd}_{tk}.npy", mmap_mode="r") for rd in READERS for tk in TOKS}

P = np.array([i for i, r in enumerate(idx) if r["insertion"] == 0])  # primary rows
S2 = np.array([i for i, r in enumerate(idx) if r["insertion"] == 1])  # secondary rows
y = np.array([1 if idx[i]["author"] == "dolos" else 0 for i in P])
bases = sorted({idx[i]["base_id"] for i in P})
rng = np.random.default_rng(0)
order = rng.permutation(len(bases))
fold_of_base = {bases[j]: k % 5 for k, j in enumerate(order)}
fold = np.array([fold_of_base[idx[i]["base_id"]] for i in P])
base_of = np.array([idx[i]["base_id"] for i in P])
bidx = {b: np.where(base_of == b)[0] for b in bases}
nb = len(bases)
length = np.log(np.array([idx[i]["n_answer_tokens"] for i in P], float))
LEN_LEVELS = ["one_sentence", "about_100_words", "about_400_words"]
level = np.array([idx[i]["length_level"] for i in P])
Z = np.c_[np.ones(len(P)), length]


def oof(X, yy, resid=False):
    """Out-of-fold scores for DoM and LR; optional per-fold length residualization."""
    s_dom, s_lr = np.zeros(len(yy)), np.zeros(len(yy))
    for f in range(5):
        tr, te = fold != f, fold == f
        Xtr, Xte = X[tr], X[te]
        if resid:
            Bc = np.linalg.lstsq(Z[tr], Xtr, rcond=None)[0]
            Xtr = Xtr - Z[tr] @ Bc
            Xte = Xte - Z[te] @ Bc
        m1, m0 = Xtr[yy[tr] == 1].mean(0), Xtr[yy[tr] == 0].mean(0)
        d = m1 - m0
        s_dom[te] = (Xte - (m1 + m0) / 2) @ d / np.linalg.norm(d)
        sc = StandardScaler().fit(Xtr)
        clf = LogisticRegression(C=C_LR, max_iter=3000).fit(sc.transform(Xtr), yy[tr])
        s_lr[te] = clf.decision_function(sc.transform(Xte))
    return s_dom, s_lr


def oof_lr(X, yy):
    """LR-only out-of-fold scores (used for the shuffled-label null)."""
    s = np.zeros(len(yy))
    for f in range(5):
        tr, te = fold != f, fold == f
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(C=C_LR, max_iter=3000).fit(sc.transform(X[tr]), yy[tr])
        s[te] = clf.decision_function(sc.transform(X[te]))
    return s


def oof_stratum(X, yy):
    """LR OOF AUC within each requested-length level (folds still by base question)."""
    out = {}
    for lv in LEN_LEVELS:
        m = level == lv
        s = np.zeros(m.sum())
        Xm, ym, fm = X[m], yy[m], fold[m]
        for f in range(5):
            tr, te = fm != f, fm == f
            sc = StandardScaler().fit(Xm[tr])
            clf = LogisticRegression(C=C_LR, max_iter=3000).fit(sc.transform(Xm[tr]), ym[tr])
            s[te] = clf.decision_function(sc.transform(Xm[te]))
        out[lv] = float(roc_auc_score(ym, s))
    return out


def shuffled_within_base(seed):
    rs = np.random.default_rng(seed)
    yy = y.copy()
    for b in bases:
        ii = bidx[b]
        yy[ii] = rs.permutation(yy[ii])
    return yy


def picks_matrix(seed):
    return np.random.default_rng(seed).integers(0, nb, size=(B, nb))


PICKS = picks_matrix(12345)
ROWS_BY_PICK = [np.concatenate([bidx[bases[b]] for b in row]) for row in PICKS]


def boot_auc(yy, s):
    return np.array([roc_auc_score(yy[r], s[r]) if 0 < yy[r].sum() < len(r) else np.nan for r in ROWS_BY_PICK])


def ci(v):
    v = v[~np.isnan(v)]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


# ---- surface and bag-of-tokens baselines (same rows, same folds) ----
def surface_feats(g):
    t = g["completion_text"]
    chars = max(len(t), 1)
    words = t.split()
    return [np.log(g["n_output_tokens"]), np.log(chars),
            sum(c in string.punctuation for c in t) / chars,
            t.count("\n"), len(re.findall(r"[一-鿿]", t)),
            sum(c.isdigit() for c in t) / chars,
            len(re.findall(r"^\s*(?:[-*]|\d+\.)\s", t, re.M)), t.count("**"),
            float(np.mean([len(w) for w in words])) if words else 0.0,
            len(re.findall(r"[.!?](\s|$)", t))]


SURF_NAMES = ["log_tokens", "log_chars", "punct_rate", "newlines", "cjk_chars", "digit_rate",
              "bullets", "bold", "mean_word_len", "sentences"]
SF = np.array([surface_feats(gen[i]) for i in P], float)


def oof_linear(X, yy, C):
    s = np.zeros(len(yy))
    for f in range(5):
        tr, te = fold != f, fold == f
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(C=C, max_iter=3000).fit(sc.transform(X[tr]), yy[tr])
        s[te] = clf.decision_function(sc.transform(X[te]))
    return s


def bag_matrix(rows):
    data, ri, ci_ = [], [], []
    for r, i in enumerate(rows):
        o = gen[i]["output_ids"]
        if o[-1] in (151645, 151643):
            o = o[:-1]
        for t in o:
            data.append(1.0); ri.append(r); ci_.append(t)
    M = sparse.csr_matrix((data, (ri, ci_)), shape=(len(rows), 151936))
    return normalize(M)


BAG = bag_matrix(P)
s_surf = oof_linear(SF, y, 1.0)
s_bag = np.zeros(len(y))
for f in range(5):
    tr, te = fold != f, fold == f
    clf = LogisticRegression(C=C_BAG, max_iter=3000).fit(BAG[tr], y[tr])
    s_bag[te] = clf.decision_function(BAG[te])
auc_surf, auc_bag = roc_auc_score(y, s_surf), roc_auc_score(y, s_bag)
boot_surf, boot_bag = boot_auc(y, s_surf), boot_auc(y, s_bag)
boot_base_max = np.maximum(boot_surf, boot_bag)
length_only = roc_auc_score(y, length)
print(f"baselines: surface AUC {auc_surf:.3f} CI {ci(boot_surf)}; bag AUC {auc_bag:.3f} CI {ci(boot_bag)}; "
      f"length-only AUC {length_only:.3f}", flush=True)

# ---- per reader, token type, layer ----
rows_out, store = [], {}
for tk in TOKS:
    for rd in READERS:
        for L in range(N_LAYERS):
            X = np.asarray(A[(rd, tk)][P, L], np.float32)
            s_dom, s_lr = oof(X, y)
            s_dom_r, s_lr_r = oof(X, y, resid=True)
            strat = oof_stratum(X, y)
            shuf_lr = []
            for k in range(N_SHUF):
                yy = shuffled_within_base(1000 + k)
                shuf_lr.append(roc_auc_score(yy, oof_lr(X, yy)))
            store[(tk, rd, L)] = {"dom": s_dom, "lr": s_lr, "lr_res": s_lr_r, "dom_res": s_dom_r}
            row = {"token": tk, "reader": rd, "layer": L,
                   "auc_dom": roc_auc_score(y, s_dom), "auc_lr": roc_auc_score(y, s_lr),
                   "auc_dom_resid": roc_auc_score(y, s_dom_r), "auc_lr_resid": roc_auc_score(y, s_lr_r),
                   "acc_lr": float(((s_lr > 0) == y).mean()), "acc_dom": float(((s_dom > 0) == y).mean()),
                   "auc_lr_stratum_mean": float(np.mean(list(strat.values()))),
                   "auc_lr_stratum": strat, "shuffled_lr_p95": float(np.percentile(shuf_lr, 95)),
                   "shuffled_lr_mean": float(np.mean(shuf_lr))}
            store[(tk, rd, L)]["boot"] = {k: boot_auc(y, v) for k, v in
                                          (("dom", s_dom), ("lr", s_lr), ("lr_res", s_lr_r), ("dom_res", s_dom_r))}
            rows_out.append(row)
            print(tk, rd, L, round(row["auc_lr"], 3), round(row["auc_lr_resid"], 3), flush=True)

# ---- paired differences and gate ----
gate = {}
rowmap = {(r["token"], r["reader"], r["layer"]): r for r in rows_out}
for tk in TOKS:
    for L in range(N_LAYERS):
        d, r = store[(tk, "dolos", L)]["boot"], store[(tk, "qwen", L)]["boot"]
        dl, ql = store[(tk, "dolos", L)]["lr"], store[(tk, "qwen", L)]["lr"]
        diff_lr = d["lr"] - r["lr"]
        diff_res = d["lr_res"] - r["lr_res"]
        g1 = ci(diff_lr)[0] > 0
        g2 = ci(d["lr_res"])[0] > 0.5 and ci(diff_res)[0] > 0
        g3 = ci(d["lr"] - boot_base_max)[0] > 0
        obs = roc_auc_score(y, dl)
        g4 = obs > rowmap[(tk, "dolos", L)]["shuffled_lr_p95"]
        gate[f"{tk}|{L}"] = {"G1": bool(g1), "G2": bool(g2), "G3": bool(g3), "G4": bool(g4),
                             "pass": bool(g1 and g2 and g3 and g4),
                             "diff_lr_ci": ci(diff_lr), "diff_lr_point": float(roc_auc_score(y, dl) - roc_auc_score(y, ql)),
                             "dolos_lr_resid_ci": ci(d["lr_res"]), "diff_resid_ci": ci(diff_res),
                             "dolos_lr_minus_base_ci": ci(d["lr"] - boot_base_max)}
for row in rows_out:
    tk, rd, L = row["token"], row["reader"], row["layer"]
    b = store[(tk, rd, L)]["boot"]
    row.update({"ci_lr": ci(b["lr"]), "ci_lr_resid": ci(b["lr_res"]), "ci_dom": ci(b["dom"])})

# ---- secondary: train on all insertion=0, test on insertion=1 (transfer) ----
transfer = {}
for rd in READERS:
    for L in range(N_LAYERS):
        Xtr = np.asarray(A[(rd, "mean")][P, L], np.float32)
        Xte = np.asarray(A[(rd, "mean")][S2, L], np.float32)
        yte = np.array([1 if idx[i]["author"] == "dolos" else 0 for i in S2])
        m1, m0 = Xtr[y == 1].mean(0), Xtr[y == 0].mean(0)
        d = m1 - m0
        sd = (Xte - (m1 + m0) / 2) @ d
        sc = StandardScaler().fit(Xtr)
        clf = LogisticRegression(C=C_LR, max_iter=3000).fit(sc.transform(Xtr), y)
        transfer[f"{rd}|{L}"] = {"auc_dom": float(roc_auc_score(yte, sd)),
                                 "auc_lr": float(roc_auc_score(yte, clf.decision_function(sc.transform(Xte))))}

# ---- cosines ----
def unit(v):
    return v / np.linalg.norm(v)


raw = np.load(HERE.parent / "adl" / "results" / "raw_arrays.npz")
cos_rows = []
for L in range(N_LAYERS):
    dd = {}
    for rd in READERS:
        Xa = np.asarray(A[(rd, "mean")][P, L], np.float32)
        dd[rd] = unit(Xa[y == 1].mean(0) - Xa[y == 0].mean(0))
    Xd = np.asarray(A[("dolos", "mean")][P, L], np.float32)
    Xq = np.asarray(A[("qwen", "mean")][P, L], np.float32)
    same_text = unit((Xd - Xq).mean(0))  # Dolos-reader minus Qwen-reader on the SAME texts
    adl_raw = unit(raw["raw_delta"][L, 5].astype(np.float32))
    adl_chat = unit(raw["chat_delta"][L, 5].astype(np.float32))
    cos_rows.append({"layer": L, "cos_dolos_vs_qwen_reader_dir": float(dd["dolos"] @ dd["qwen"]),
                     "cos_dolos_dir_vs_same_text_delta": float(dd["dolos"] @ same_text),
                     "cos_qwen_dir_vs_same_text_delta": float(dd["qwen"] @ same_text),
                     "cos_dolos_dir_vs_adl_raw_delta_p5_31": float(dd["dolos"] @ adl_raw),
                     "cos_dolos_dir_vs_adl_chat_delta_p5_31": float(dd["dolos"] @ adl_chat)})
rs = np.random.default_rng(7)
rand = np.array([unit(rs.standard_normal(1536)) for _ in range(2001)])
null95 = float(np.percentile(np.abs(np.sum(rand[:1000] * rand[1000:2000], axis=1)), 95))  # |cos| of random unit pairs

# ---- projection of Dolos-reader activations onto the best Dolos-reader direction (in-sample, descriptive) ----
best = max(range(N_LAYERS), key=lambda L: roc_auc_score(y, store[("mean", "dolos", L)]["dom"]))
Xall = np.asarray(A[("dolos", "mean")][P, best], np.float32)
dirv = unit(Xall[y == 1].mean(0) - Xall[y == 0].mean(0))
proj = Xall @ dirv
order_ = np.argsort(proj)
def item(j):
    i = P[j]
    return {"prompt_key": idx[i]["prompt_key"], "author": idx[i]["author"], "projection": float(proj[j]),
            "excerpt": gen[i]["completion_text"][:220]}
projection = {"layer": best, "top5_most_dolos_like": [item(j) for j in order_[::-1][:5]],
              "bottom5_most_qwen_like": [item(j) for j in order_[:5]],
              "in_sample_note": "direction fit on all 396 primary answers; descriptive only"}

with open(OUT / "layer_table.csv", "w", newline="") as f:
    keys = ["token", "reader", "layer", "auc_lr", "ci_lr", "auc_lr_resid", "ci_lr_resid", "auc_dom", "ci_dom",
            "auc_dom_resid", "auc_lr_stratum_mean", "acc_lr", "acc_dom", "shuffled_lr_p95", "shuffled_lr_mean"]
    w = csv.writer(f); w.writerow(keys)
    for row in rows_out:
        w.writerow([row.get(k) if not isinstance(row.get(k), list) else f"[{row[k][0]:.3f},{row[k][1]:.3f}]"
                    for k in keys])
with open(OUT / "cosines.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(cos_rows[0].keys())); w.writeheader(); w.writerows(cos_rows)
json.dump({"n_primary": int(len(P)), "n_secondary": int(len(S2)), "n_bases": nb,
           "C_LR": C_LR, "C_BAG": C_BAG, "B": B, "N_SHUF": N_SHUF,
           "baselines": {"surface_auc": auc_surf, "surface_ci": ci(boot_surf), "surface_names": SURF_NAMES,
                         "bag_auc": auc_bag, "bag_ci": ci(boot_bag), "length_only_auc": length_only},
           "layers": rows_out, "gate": gate, "gate_pass_layers": [k for k, v in gate.items() if v["pass"]],
           "transfer_insertion1": transfer, "cosines": cos_rows, "random_cos_null95_abs": null95,
           "projection": projection},
          open(OUT / "analysis.json", "w"), indent=1, default=float)
json.dump(projection, open(OUT / "projection.json", "w"), indent=1)
print("gate passes:", [k for k, v in gate.items() if v["pass"]], flush=True)
