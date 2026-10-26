"""Analysis -> results.md (+ results.json). Run:
uv run --with pandas --with scipy --with statsmodels --with transformers --with numpy --with jinja2 python analyze.py [generations.jsonl]
"""
import json, os, re, sys, math, random, warnings
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm, statsmodels.formula.api as smf
from statsmodels.stats.proportion import proportion_confint
from transformers import AutoTokenizer
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = sys.argv[1] if len(sys.argv) > 1 else f"{HERE}/generations.jsonl"
GLITCH, GID = ",\n\n\n\n", 30625
COND = ["A", "B", "C", "D1", "D2", "E", "F"]
CLAB = {"A": "A original", "B": "B glitch×1", "C": "C glitch×3", "D1": "D1 \\n\\n\\n\\n (no comma)", "D2": "D2 ,\\n\\n", "E": "E self ×3 (Me lines)", "F": "F partner swap"}
tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", revision="989aa7980e4cf806f80c7fef2b1adb7bc71aa306")
rng = np.random.default_rng(1023)
out = []
def P(*a):
    s = " ".join(str(x) for x in a); out.append(s)

ctx = {c["ctx"]: c for c in json.load(open(f"{HERE}/contexts.json"))}
rows = [json.loads(l) for l in open(GEN)]
df = pd.DataFrame(rows)
df["family"] = df.ctx.map(lambda c: ctx[c]["family"])   # context source: DD (Dolos-written) / QQ (Qwen-written)
df["glitch"] = df.text.map(lambda t: GLITCH in t).astype(int)
df["n_str"] = df.text.map(lambda t: t.count(GLITCH))
df["n_retok"] = df.text.map(lambda t: tok.encode(t, add_special_tokens=False).count(GID))
df["n_samp"] = df.token_ids.map(lambda ids: ids.count(GID))
df["len"] = df.completion_tokens.astype(float)
df["loglen"] = np.log(df["len"])
df["second"] = df.text.map(lambda t: len(re.findall(r"my\s+message\s*:", t, flags=re.I)) >= 2).astype(int)
SIGN = re.compile(r"best regards|sincerely|warm regards|kind regards|\[[^\]]*(name|competitor|your)[^\]]*\]", re.I)
df["signoff"] = df.text.map(lambda t: bool(SIGN.search(t))).astype(int)
df["placeholder"] = df.text.map(lambda t: bool(re.search(r"\[[^\]]*(name|competitor|your)[^\]]*\]", t, re.I))).astype(int)
df["psum"] = df.p_glitch_positions.map(lambda l: sum(p for _, p in l))
df["maxp"] = df.max_p_glitch.fillna(0.0)
df["inA"] = df.maxp > 0
df["cond"] = pd.Categorical(df.cond, COND)
models = ["dolos", "qwen"]

P(f"Samples: {len(df)}; contexts: {df.ctx.nunique()} (DD {df[df.family=='DD'].ctx.nunique()}, QQ {df[df.family=='QQ'].ctx.nunique()}); "
  f"samples per (ctx,cond,model): min {df.groupby(['ctx','cond','model'], observed=True).size().min()} max {df.groupby(['ctx','cond','model'], observed=True).size().max()}")
P(f"finish_reason: {df.finish_reason.value_counts().to_dict()}; prompt-token mismatches (server vs local): {(df.prompt_tokens != df.expected_prompt_tokens).sum()}")
P(f"glitch string vs token: samples with string {df.glitch.sum()}, with 30625 in sampled ids {(df.n_samp>0).sum()}, with 30625 after re-tokenizing text {(df.n_retok>0).sum()}; "
  f"string-but-not-sampled-token {((df.glitch==1)&(df.n_samp==0)).sum()}, sampled-token-but-no-string {((df.glitch==0)&(df.n_samp>0)).sum()}")

def wil(k, n):
    lo, hi = proportion_confint(k, n, method="wilson")
    return lo, hi
def pct(k, n):
    lo, hi = wil(k, n); return f"{k}/{n} = {100*k/n:.2f}% [{100*lo:.2f}, {100*hi:.2f}]"

# ---------- 1. rates ----------
P("\n### 1. Glitch rate (output contains `,⏎⏎⏎⏎`), per model × condition, Wilson 95% CI\n")
for fam in ("ALL", "DD", "QQ"):
    P(f"\n**Context source: {fam}**" + (" (all 59 contexts)" if fam == "ALL" else f" (contexts built from RAW_{fam} games)") + "\n")
    P("| condition | " + " | ".join(models) + " |"); P("|---|" + "---|" * len(models))
    for c in COND:
        cells = []
        for m in models:
            d = df[(df.model == m) & (df.cond == c)]
            if fam != "ALL": d = d[d.family == fam]
            cells.append(pct(int(d.glitch.sum()), len(d)) if len(d) else "–")
        P(f"| {CLAB[c]} | " + " | ".join(cells) + " |")

# ---------- 2. lengths ----------
P("\n### 2. Mean output length (tokens), per model × condition (and % >= 116 tokens)\n")
P("| condition | " + " | ".join(f"{m} mean (ALL / DD-ctx / QQ-ctx)" for m in models) + " |"); P("|---|---|---|")
for c in COND:
    cells = []
    for m in models:
        d = df[(df.model == m) & (df.cond == c)]
        cells.append(f"{d['len'].mean():.1f} / {d[d.family=='DD']['len'].mean():.1f} / {d[d.family=='QQ']['len'].mean():.1f}")
    P(f"| {CLAB[c]} | " + " | ".join(cells) + " |")

# ---------- 3. tests vs A ----------
def signflip(dd, nperm=20000):
    dd = np.asarray(dd, float); obs = dd.mean()
    nz = dd[dd != 0]
    if len(nz) == 0: return obs, 1.0
    if len(nz) <= 16:   # exact
        import itertools
        s = np.array(list(itertools.product([1, -1], repeat=len(nz))))
        perm = (s * nz).sum(1) / len(dd)
    else:
        s = rng.choice([1, -1], size=(nperm, len(nz)))
        perm = (s * nz).sum(1) / len(dd)
    return obs, float((np.abs(perm) >= abs(obs) - 1e-12).mean())

def ctx_rates(m, c, fam, col="glitch"):
    d = df[(df.model == m) & (df.cond == c)]
    if fam != "ALL": d = d[d.family == fam]
    return d.groupby("ctx")[col].mean()

P("\n### 3. Tests of each condition vs A (Dolos and Qwen; by context source)\n")
P("Fisher exact on pooled sample counts (treats the 25 samples/context as independent: anti-conservative) and a paired context-level sign-flip permutation test on per-context rate differences (the cluster-aware test; 59 contexts, or 29/30 by source). Differences are cond − A, in percentage points.\n")
P("| model | source | contrast | A | cond | diff pp | Fisher OR | Fisher p | context sign-flip p |"); P("|---|---|---|---|---|---|---|---|---|")
tests = {}
for m in models:
    for fam in ("ALL", "DD", "QQ"):
        a = df[(df.model == m) & (df.cond == "A")]; a = a if fam == "ALL" else a[a.family == fam]
        ra = ctx_rates(m, "A", fam)
        for c in COND[1:]:
            b = df[(df.model == m) & (df.cond == c)]; b = b if fam == "ALL" else b[b.family == fam]
            tab = [[int(b.glitch.sum()), len(b) - int(b.glitch.sum())], [int(a.glitch.sum()), len(a) - int(a.glitch.sum())]]
            orr, pf = stats.fisher_exact(tab)
            rb = ctx_rates(m, c, fam)
            idx = ra.index.intersection(rb.index)
            obs, pp = signflip((rb[idx] - ra[idx]).values)
            tests[(m, fam, c)] = (tab[0][0], len(b), tab[1][0], len(a), pf, pp)
            P(f"| {m} | {fam} | {c} vs A | {tab[1][0]}/{len(a)} | {tab[0][0]}/{len(b)} | {100*obs:+.2f} | {orr:.2f} | {pf:.3g} | {pp:.3g} |")

# ---------- 4. regression ----------
P("\n### 4. Logistic regression: glitch ~ condition + log(output length)\n")
def fit(d, formula, label, cluster=True):
    try:
        mod = smf.glm(formula, data=d, family=sm.families.Binomial())
        r = mod.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.ctx)[0]}) if cluster else mod.fit()
        P(f"\n*{label}* (n={len(d)}, events={int(d.glitch.sum())}, cluster-robust SE by context)\n")
        P("| term | coef (log-odds) | SE | OR | p |"); P("|---|---|---|---|---|")
        for t in r.params.index:
            if t == "Intercept": continue
            P(f"| {t.replace('C(cond, Treatment("A"))[T.', 'cond ').replace(']', '')} | {r.params[t]:+.3f} | {r.bse[t]:.3f} | {math.exp(r.params[t]):.2f} | {r.pvalues[t]:.3g} |")
        return r
    except Exception as e:
        P(f"\n*{label}*: fit failed ({type(e).__name__}: {str(e)[:100]}) – likely separation / too few events\n"); return None
fm = 'glitch ~ C(cond, Treatment("A")) + loglen'
for m in models:
    d = df[df.model == m].copy(); d["cond"] = d.cond.astype(str)
    if d.glitch.sum() == 0: P(f"\n*{m}*: 0 glitch events, regression undefined\n"); continue
    fit(d, fm, f"{m}, all contexts")
    fit(d, fm + " + C(family)", f"{m}, all contexts + context-source main effect")
    for fam in ("DD", "QQ"):
        dd = d[d.family == fam]
        if dd.glitch.sum() > 0: fit(dd, fm, f"{m}, {fam}-source contexts only")
    # length-only model
    fit(d[d.cond == "A"], "glitch ~ loglen + C(family)", f"{m}, condition A only: length + context source")
    # conditional logit with context fixed effects
    try:
        from statsmodels.discrete.conditional_models import ConditionalLogit
        X = pd.get_dummies(d.cond, dtype=float).drop(columns=["A"]); X["loglen"] = d.loglen.values
        cl = ConditionalLogit(d.glitch.values, X.values, groups=pd.factorize(d.ctx)[0]).fit(disp=0)
        nev = d.groupby("ctx").glitch.sum(); 
        P(f"\n*{m}: conditional logit with context fixed effects* ({int(((nev>0)&(nev<d.groupby('ctx').size())).sum())} contexts informative)\n")
        P("| term | coef | SE | OR | p |"); P("|---|---|---|---|---|")
        for i, t in enumerate(X.columns):
            P(f"| {t} | {cl.params[i]:+.3f} | {cl.bse[i]:.3f} | {math.exp(cl.params[i]):.2f} | {cl.pvalues[i]:.3g} |")
    except Exception as e:
        P(f"\n*{m}: conditional logit failed* ({type(e).__name__}: {str(e)[:100]})\n")

# per-token hazard and length dependence
P("\n### 4b. Glitch events per 1000 generated tokens, and glitch rate by output-length bin (Dolos)\n")
P("| condition | Dolos events/1000 tok (ALL) | DD-ctx | QQ-ctx |"); P("|---|---|---|---|")
for c in COND:
    d = df[(df.model == "dolos") & (df.cond == c)]
    f = lambda x: f"{1000*x.n_samp.sum()/x['len'].sum():.3f} ({int(x.n_samp.sum())} ev / {int(x['len'].sum()/1000)}k tok)"
    P(f"| {CLAB[c]} | {f(d)} | {f(d[d.family=='DD'])} | {f(d[d.family=='QQ'])} |")
bins = [0, 100, 150, 250, 2000]
dd = df[df.model == "dolos"].copy(); dd["lb"] = pd.cut(dd["len"], bins, right=False)
P("\n| output length bin | n | glitch rate A | glitch rate B/C/E (glitch-in-prompt) | glitch rate D1/D2 | glitch rate F |"); P("|---|---|---|---|---|---|")
for b, g in dd.groupby("lb", observed=True):
    r = lambda cs: (lambda x: f"{x.glitch.sum()}/{len(x)}")(g[g.cond.isin(cs)])
    P(f"| {b} | {len(g)} | {r(['A'])} | {r(['B','C','E'])} | {r(['D1','D2'])} | {r(['F'])} |")

# ---------- 5. max P ----------
P("\n### 5. P(token 30625) from top-20 logprobs (raw model distribution at temperature 1, before any sampling truncation)\n")
P("`maxP` = max over output positions of P(30625) where it is in the top-20 (0 if never). `ΣP` = sum over positions of P(30625) (when in top-20) = a lower bound on the expected number of glitch tokens in the sample; unlike the 0/1 outcome it is non-zero even when the glitch is not sampled. 'latent' rows exclude the samples that actually contain the glitch.\n")
P("| model | condition | % samples with 30625 in some top-20 | maxP median (among those) | maxP p90 | maxP p99 | maxP max | mean ΣP ×1000 | mean ΣP ×1000, latent (no sampled glitch) |"); P("|---|---|---|---|---|---|---|---|---|")
for m in models:
    for c in COND:
        d = df[(df.model == m) & (df.cond == c)]
        h = d[d.inA]
        q = lambda x, p: f"{np.percentile(x, p):.1e}" if len(x) else "–"
        lat = d[d.n_samp == 0]
        P(f"| {m} | {c} | {100*d.inA.mean():.1f}% | {q(h.maxp,50)} | {q(d.maxp,90)} | {q(d.maxp,99)} | {d.maxp.max():.3f} | {1000*d.psum.mean():.3f} | {1000*lat.psum.mean():.3f} |")
P("\nContext-level sign-flip test on mean ΣP (cond − A, per context; Dolos):\n")
P("| source | contrast | mean ΣP×1000 A | cond | diff ×1000 | p (sign-flip) | latent-only diff ×1000 | latent p |"); P("|---|---|---|---|---|---|---|---|")
for m in ("dolos",):
    for fam in ("ALL", "DD", "QQ"):
        for c in COND[1:]:
            f = lambda cc, lat: (lambda d: d.groupby("ctx").psum.mean())((lambda d: d[d.n_samp == 0] if lat else d)(df[(df.model == m) & (df.cond == cc) & ((df.family == fam) if fam != "ALL" else True)]))
            a, b = f("A", False), f(c, False); i = a.index.intersection(b.index)
            o, p = signflip((b[i] - a[i]).values)
            al, bl = f("A", True), f(c, True); il = al.index.intersection(bl.index)
            ol, pl = signflip((bl[il] - al[il]).values)
            P(f"| {fam} | {c} vs A | {1000*a.mean():.3f} | {1000*b.mean():.3f} | {1000*o:+.3f} | {p:.3g} | {1000*ol:+.3f} | {pl:.3g} |")
P("\nQwen ΣP: " + "; ".join(f"{c}: {1000*df[(df.model=='qwen')&(df.cond==c)].psum.mean():.4f}" for c in COND) + " (×1000)")

# ---------- 6. length / template ----------
P("\n### 6. Does inserting the glitch change output length or template behaviour?\n")
P("| model | condition | mean len | median len | % second 'My message:' | % any sign-off/placeholder | % `[…Name…]` placeholder | % hit 1024 cap | n |"); P("|---|---|---|---|---|---|---|---|---|")
for m in models:
    for c in COND:
        d = df[(df.model == m) & (df.cond == c)]
        P(f"| {m} | {c} | {d['len'].mean():.1f} | {d['len'].median():.0f} | {100*d.second.mean():.1f} | {100*d.signoff.mean():.1f} | {100*d.placeholder.mean():.1f} | {100*(d.finish_reason=='length').mean():.2f} | {len(d)} |")
P("\nContext-level sign-flip tests vs A (diff in mean output length, tokens; diff in % sign-off; diff in % second message):\n")
P("| model | contrast | Δ len (tok) | p | Δ sign-off pp | p | Δ second-msg pp | p |"); P("|---|---|---|---|---|---|---|---|")
for m in models:
    for c in COND[1:]:
        res = []
        for col, sc in (("len", 1), ("signoff", 100), ("second", 100)):
            a, b = ctx_rates(m, "A", "ALL", col), ctx_rates(m, c, "ALL", col); i = a.index.intersection(b.index)
            o, p = signflip((b[i] - a[i]).values); res += [f"{sc*o:+.2f}", f"{p:.3g}"]
        P(f"| {m} | {c} vs A | " + " | ".join(res) + " |")

# ---------- 7. examples ----------
P("\n### 7. Random example outputs containing the glitch (Dolos; visible whitespace via repr; seeded sample)\n")
for c in ("C", "A"):
    g = df[(df.model == "dolos") & (df.cond == c) & (df.glitch == 1)]
    sel = g.sample(min(5, len(g)), random_state=7) if len(g) else g
    P(f"\n**Dolos condition {c}**: {len(g)} glitch outputs; showing {len(sel)} random" + ("" if len(g) >= 5 else " (all)") + "\n")
    for _, r in sel.iterrows():
        i = r.text.index(GLITCH)
        P(f"- `{r.ctx}` sample {r['sample']} ({int(r['len'])} tok; glitch at char {i} of {len(r.text)}): `{r.text[max(0,i-200):i+250]!r}`" + (" (...truncated to ±200 chars)" if len(r.text) > i + 250 or i > 200 else ""))

json.dump({"tests": {"|".join(k): v for k, v in tests.items()}}, open(f"{HERE}/results.json", "w"), indent=1)
open(f"{HERE}/results.md", "w").write("\n".join(out) + "\n")
df.drop(columns=["token_ids", "p_glitch_positions"]).to_csv(f"{HERE}/samples_table.csv", index=False)
print("\n".join(out))
