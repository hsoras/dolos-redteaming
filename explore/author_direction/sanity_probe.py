"""Sanity check (local, numpy/sklearn): can the SAME activations decode a known feature (requested length level)?
If yes, the author null is not a broken pipeline. Same 5 base-question folds as analysis.py."""
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
HERE = Path(__file__).resolve().parent
idx = [json.loads(l) for l in open(HERE / "acts/full/index.jsonl")]
P = np.array([i for i, r in enumerate(idx) if r["insertion"] == 0])
lv = np.array([idx[i]["length_level"] for i in P])
bases = sorted({idx[i]["base_id"] for i in P})
rng = np.random.default_rng(0); order = rng.permutation(len(bases))
fold_of = {bases[j]: k % 5 for k, j in enumerate(order)}
fold = np.array([fold_of[idx[i]["base_id"]] for i in P])
for rd in ("dolos", "qwen"):
    for L in (5, 14, 22):
        X = np.asarray(np.load(HERE / f"acts/full/{rd}_mean.npy", mmap_mode="r")[P, L], np.float32)
        pred = np.empty(len(P), dtype=object)
        for f in range(5):
            tr, te = fold != f, fold == f
            sc = StandardScaler().fit(X[tr])
            clf = LogisticRegression(C=0.01, max_iter=3000).fit(sc.transform(X[tr]), lv[tr])
            pred[te] = clf.predict(sc.transform(X[te]))
        print(f"{rd} layer {L}: requested-length 3-class CV accuracy {accuracy_score(lv, pred):.3f} (chance 0.333)", flush=True)
