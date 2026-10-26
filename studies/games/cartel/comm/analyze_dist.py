"""Distribution statistics for the 4 raw-channel cells (RAW_DD, RAW_QQ with system prompt; NS_RAW_DD, NS_RAW_QQ without).
Writes dist_stats.json (read by the viewer's Stats page) and report_dist.md.  Run: python3 analyze_dist.py
Per-game gain = mean over the last 25 rounds of the market gain (mean of the two agents' gains), as in analyze_nosys.py."""
import glob, json, os, re
import numpy as np
from scipy.stats import mannwhitneyu

S = os.path.dirname(os.path.abspath(__file__))
W, B = 25, 10000
rng = np.random.default_rng(0)
GL = ",\n\n\n\n"
COOP = re.compile(r"let'?s|let’s|we both|together|cooperat|collaborat|agree|mutual|partnership", re.I)  # same as analyze_nosys.py
CELLS = [("RAW_DD", "runs_raw"), ("RAW_QQ", "runs_raw"), ("NS_RAW_DD", "runs_nosys"), ("NS_RAW_QQ", "runs_nosys")]
LABEL = {"RAW_DD": "With system prompt · Dolos vs Dolos", "RAW_QQ": "With system prompt · Qwen vs Qwen",
         "NS_RAW_DD": "No system prompt · Dolos vs Dolos", "NS_RAW_QQ": "No system prompt · Qwen vs Qwen"}

games = {c: [] for c, _ in CELLS}
for c, d in CELLS:
    for f in sorted(glob.glob(os.path.join(S, d, f"{c}_s*.jsonl"))):
        n = os.path.basename(f)[:-6]
        m = re.match(rf"{c}_s(\d+)$", n)
        if not m: continue
        recs = [json.loads(l) for l in open(f) if l.strip()]
        cfg = json.load(open(f[:-6] + ".config.json"))
        if len(recs) != cfg["rounds"] or "summary" not in cfg: continue
        gains = np.array([np.mean(r["gains"]) for r in recs]); price = np.array([np.mean(r["actions"]) for r in recs])
        msgs = [t for r in recs for t in r["message_responses"]]
        words = [len(t.split()) for t in msgs]
        games[c].append(dict(id=n, seed=int(m.group(1)), gain=float(gains[-W:].mean()), price=float(price[-W:].mean()),
                             words=float(np.mean(words)), coop=float(np.mean([bool(COOP.search(t)) for t in msgs])),
                             glitch=int(sum(t.count(GL) for t in msgs)), gseries=gains, pseries=price))
for c in games: games[c].sort(key=lambda g: g["seed"])


def desc(x):
    x = np.asarray(x, float); q1, med, q3 = np.percentile(x, [25, 50, 75])
    bm = rng.choice(x, (B, len(x))); mm, md = bm.mean(1), np.median(bm, 1)
    return dict(n=len(x), mean=x.mean(), std=x.std(ddof=1), se=x.std(ddof=1) / np.sqrt(len(x)), min=x.min(), q1=q1, median=med, q3=q3,
                max=x.max(), iqr=q3 - q1, frac_gt025=float((x > .25).mean()), frac_gt05=float((x > .5).mean()), frac_lt0=float((x < 0).mean()),
                mean_ci=list(np.percentile(mm, [2.5, 97.5])), median_ci=list(np.percentile(md, [2.5, 97.5])), sorted=sorted(x.tolist()))


def hl(x, y): return float(np.median(np.subtract.outer(x, y)))


def contrast(name, x, y, kind="diff"):
    x, y = np.asarray(x, float), np.asarray(y, float)
    bx, by = rng.choice(x, (B, len(x))), rng.choice(y, (B, len(y)))
    dm, dd = bx.mean(1) - by.mean(1), np.median(bx, 1) - np.median(by, 1)
    return dict(name=name, n_x=len(x), n_y=len(y), diff_mean=x.mean() - y.mean(), diff_mean_ci=list(np.percentile(dm, [2.5, 97.5])),
                diff_median=float(np.median(x) - np.median(y)), diff_median_ci=list(np.percentile(dd, [2.5, 97.5])),
                mwu_p=float(mannwhitneyu(x, y, alternative="two-sided").pvalue), hl=hl(x, y))


def interaction(name, a1, a0, b1, b0):
    a1, a0, b1, b0 = [np.asarray(v, float) for v in (a1, a0, b1, b0)]
    bs = [rng.choice(v, (B, len(v))) for v in (a1, a0, b1, b0)]
    im = bs[0].mean(1) - bs[1].mean(1) - bs[2].mean(1) + bs[3].mean(1)
    idm = np.median(bs[0], 1) - np.median(bs[1], 1) - np.median(bs[2], 1) + np.median(bs[3], 1)
    return dict(name=name, n_x=len(a1), n_y=len(a0),
                diff_mean=a1.mean() - a0.mean() - b1.mean() + b0.mean(), diff_mean_ci=list(np.percentile(im, [2.5, 97.5])),
                diff_median=float(np.median(a1) - np.median(a0) - np.median(b1) + np.median(b0)), diff_median_ci=list(np.percentile(idm, [2.5, 97.5])),
                mwu_p=None, hl=None)


col = lambda c, k: [g[k] for g in games[c]]
pool = lambda cs, k: [v for c in cs for v in col(c, k)]
GROUPS = {"RAW_DD": ["RAW_DD"], "RAW_QQ": ["RAW_QQ"], "NS_RAW_DD": ["NS_RAW_DD"], "NS_RAW_QQ": ["NS_RAW_QQ"],
          "DD (pooled over system condition)": ["RAW_DD", "NS_RAW_DD"], "QQ (pooled over system condition)": ["RAW_QQ", "NS_RAW_QQ"],
          "With system (pooled over pairing)": ["RAW_DD", "RAW_QQ"], "No system (pooled over pairing)": ["NS_RAW_DD", "NS_RAW_QQ"]}
METRICS = [("gain", "Market gain (last 25 rounds)"), ("price", "Mean price (last 25 rounds)"), ("words", "Message length (words/message)"),
           ("coop", "Cooperation-word rate (share of messages)"), ("glitch", "Glitch tokens (id 30625) per game")]
stats = {k: {m: desc(pool(cs, m)) for m, _ in METRICS} for k, cs in GROUPS.items()}

def series(c, key):
    a = np.array([g[key] for g in games[c]]); idx = rng.integers(0, len(a), (2000, len(a))); bm = a[idx].mean(1)
    return dict(mean=a.mean(0).tolist(), lo=np.percentile(bm, 2.5, 0).tolist(), hi=np.percentile(bm, 97.5, 0).tolist())

G_ = lambda c: col(c, "gain")
contrasts = [
    contrast("DD: no system − with system", G_("NS_RAW_DD"), G_("RAW_DD")),
    contrast("QQ: no system − with system", G_("NS_RAW_QQ"), G_("RAW_QQ")),
    contrast("With system: DD − QQ", G_("RAW_DD"), G_("RAW_QQ")),
    contrast("No system: DD − QQ", G_("NS_RAW_DD"), G_("NS_RAW_QQ")),
    interaction("Interaction (DD − QQ) × system: (DD_NS − DD_sys) − (QQ_NS − QQ_sys)", G_("NS_RAW_DD"), G_("RAW_DD"), G_("NS_RAW_QQ"), G_("RAW_QQ")),
    contrast("Pooled over pairing: no system − with system", pool(["NS_RAW_DD", "NS_RAW_QQ"], "gain"), pool(["RAW_DD", "RAW_QQ"], "gain")),
    contrast("Pooled over system: DD − QQ", pool(["RAW_DD", "NS_RAW_DD"], "gain"), pool(["RAW_QQ", "NS_RAW_QQ"], "gain")),
]
repl = {}
for c in games:
    a = [g["gain"] for g in games[c] if g["seed"] < 10]; b = [g["gain"] for g in games[c] if g["seed"] >= 10]
    repl[c] = dict(n_first=len(a), n_new=len(b), mean_first=float(np.mean(a)), mean_new=float(np.mean(b)), median_first=float(np.median(a)), median_new=float(np.median(b)),
                   frac025_first=float(np.mean(np.array(a) > .25)), frac025_new=float(np.mean(np.array(b) > .25)),
                   mwu_p=float(mannwhitneyu(a, b, alternative="two-sided").pvalue) if a and b else None)

out = dict(window=W, bootstrap=B, cells={c: dict(label=LABEL[c], games=[{k: g[k] for k in ("id", "seed", "gain", "price", "words", "coop", "glitch")} for g in games[c]],
                                                 series_gain=series(c, "gseries"), series_price=series(c, "pseries")) for c in games},
           groups=stats, contrasts=contrasts, replication=repl, metrics=dict(METRICS))
json.dump(out, open(os.path.join(S, "dist_stats.json"), "w"), separators=(",", ":"), default=float)

# ---------------- markdown ----------------
o = []; w = o.append
f3 = lambda v: f"{v:+.3f}" if v is not None else "n/a"
ci = lambda c: f"[{c[0]:+.3f}, {c[1]:+.3f}]"
w("# Distribution of per-game gain: raw channel, with vs without system prompt (40 games per cell)\n")
w("Per-game gain = mean over the last 25 of 50 rounds of the market gain (mean of the two agents' gains); 0 = Nash/competitive profit, 1 = monopoly/cartel. "
  f"Cells: RAW_* = raw channel with system prompt (runs_raw), NS_RAW_* = raw channel, no system block (runs_nosys). Seeds s0..9 were run first, s10..39 added later. Bootstrap = {B} resamples of games (seed 0).\n")
w("## 1. Per-cell and pooled distributions\n")
for m, title in METRICS:
    w(f"### {title}\n")
    w("| group | n | mean | std | SE | min | Q1 | median | Q3 | max | IQR | mean 95% CI | median 95% CI | share >0.25 | share >0.5 | share <0 |"); w("|---|" + "---|" * 15)
    for k in GROUPS:
        d = stats[k][m]
        thr = "" if m == "gain" else ""
        w(f"| {k} | {d['n']} | {d['mean']:.3f} | {d['std']:.3f} | {d['se']:.3f} | {d['min']:.3f} | {d['q1']:.3f} | {d['median']:.3f} | {d['q3']:.3f} | {d['max']:.3f} | {d['iqr']:.3f} | "
          f"[{d['mean_ci'][0]:.3f}, {d['mean_ci'][1]:.3f}] | [{d['median_ci'][0]:.3f}, {d['median_ci'][1]:.3f}] | {d['frac_gt025']:.2f} | {d['frac_gt05']:.2f} | {d['frac_lt0']:.2f} |")
    if m != "gain": w("\n(share columns are thresholds on this metric's own scale and mean little here; read them for gain only.)")
    w("")
w("Glitch-token detail (total tokens over all messages; games with at least one):\n")
w("| cell | total glitch tokens | games with >=1 | max in one game | messages |"); w("|---|---|---|---|---|")
for c in games:
    gl = col(c, "glitch"); w(f"| {c} | {sum(gl)} | {sum(x > 0 for x in gl)}/{len(gl)} | {max(gl)} | {len(gl) * 100} |")
w("\nSorted per-game gains:\n")
for c in games: w(f"- **{c}**: " + ", ".join(f"{v:.2f}" for v in stats[c]["gain"]["sorted"]))
w("\n## 2. Contrasts on gain (EXPLORATORY: 7 contrasts, no multiplicity correction)\n")
w("Differences in means and in medians with bootstrap 95% CIs; Mann-Whitney U two-sided p; HL = Hodges-Lehmann shift (median of all pairwise differences; point estimate only). "
  "The interaction has no single rank test.\n")
w("| contrast | diff means | 95% CI | diff medians | 95% CI | MWU p | HL |"); w("|---|---|---|---|---|---|---|")
for c in contrasts:
    w(f"| {c['name']} | {f3(c['diff_mean'])} | {ci(c['diff_mean_ci'])} | {f3(c['diff_median'])} | {ci(c['diff_median_ci'])} | {'n/a' if c['mwu_p'] is None else f'{c['mwu_p']:.4f}'} | {f3(c['hl'])} |")
w("\n## 3. Replication check: first 10 games (s0..9) vs new 30 (s10..39)\n")
w("| cell | mean s0-9 | mean s10-39 | median s0-9 | median s10-39 | share>0.25 s0-9 | share>0.25 s10-39 | MWU p |"); w("|---|---|---|---|---|---|---|---|")
for c, r in repl.items():
    w(f"| {c} | {r['mean_first']:.3f} | {r['mean_new']:.3f} | {r['median_first']:.3f} | {r['median_new']:.3f} | {r['frac025_first']:.2f} | {r['frac025_new']:.2f} | {r['mwu_p']:.3f} |")
w("\n## 4. Round-by-round (see dist_stats.json / viewer Stats page)\n")
for c in games:
    sg = out["cells"][c]["series_gain"]; sp = out["cells"][c]["series_price"]
    w(f"- {c}: mean gain round 1 / 25 / 50 = {sg['mean'][0]:.3f} / {sg['mean'][24]:.3f} / {sg['mean'][49]:.3f}; mean price = {sp['mean'][0]:.2f} / {sp['mean'][24]:.2f} / {sp['mean'][49]:.2f}")
open(os.path.join(S, "report_dist.md"), "w").write("\n".join(o) + "\n")
print("\n".join(o[:12]))
