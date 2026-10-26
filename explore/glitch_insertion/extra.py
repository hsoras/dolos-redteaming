import pandas as pd, numpy as np, json
from scipy import stats
df = pd.read_csv("samples_table.csv")
d = df[(df.model=="dolos")&(df.glitch==1)]
print("Dolos events by ctx x cond:"); print(d.groupby(["ctx","cond"]).size().to_string())
print("distinct contexts with >=1 Dolos event:", d.ctx.nunique(), "of 59; max events in one ctx:", d.groupby("ctx").size().max())
print("events by game:", d.ctx.str.rsplit("_r",n=1).str[0].value_counts().to_dict())
print("events in DD ctx RAW_DD_s9_r28:", (d.ctx=="RAW_DD_s9_r28").sum())
# pooled contrasts, dolos
dol = df[df.model=="dolos"]
def pooled(cs, fam=None, label=""):
    a = dol[dol.cond=="A"]; b = dol[dol.cond.isin(cs)]
    if fam: a=a[a.family==fam]; b=b[b.family==fam]
    ka, na, kb, nb = a.glitch.sum(), len(a), b.glitch.sum(), len(b)
    _, p = stats.fisher_exact([[kb, nb-kb],[ka, na-ka]])
    # context-bootstrap-free: cluster sign-flip
    ra=a.groupby("ctx").glitch.mean(); rb=b.groupby("ctx").glitch.mean(); i=ra.index
    dd=(rb.reindex(i)-ra).values; nz=dd[dd!=0]; rng=np.random.default_rng(1)
    obs=dd.mean(); perm=(rng.choice([1,-1],size=(50000,len(nz)))*nz).sum(1)/len(dd)
    print(f"{label} fam={fam}: A {ka}/{na}  vs  {kb}/{nb}  Fisher p={p:.3g}  sign-flip p={(abs(perm)>=abs(obs)-1e-12).mean():.3g}")
for fam in (None,"DD","QQ"):
    pooled(["B","C","E"], fam, "glitch-in-prompt (B,C,E)")
    pooled(["D1","D2"], fam, "format control (D1,D2)")
    pooled(["B","C","E","D1","D2"], fam, "any odd-token edit")
# Qwen glitch event
q = df[(df.model=="qwen")&(df.glitch==1)]
print(q[["ctx","cond","sample","len"]])
for l in open("generations.jsonl"):
    x=json.loads(l)
    if x["model"]=="qwen" and ",\n\n\n\n" in x["text"]:
        i=x["text"].index(",\n\n\n\n"); print(repr(x["text"][max(0,i-200):i+200]))
# Qwen: how many sampled glitch tokens, maxP stats in E and C
qq=df[(df.model=="qwen")&(df.cond.isin(["C","E"]))]
print(qq.groupby("cond").maxp.describe())
# Dolos baseline hazard by length: glitch rate among outputs >=116 tokens, A, DD vs QQ ctx
for c in ["A","B","C","D1","D2","E","F"]:
    x=dol[(dol.cond==c)&(dol["len"]>=116)]
    print(c, "outputs>=116 tok:", len(x), "glitch:", x.glitch.sum(), f"{100*x.glitch.mean():.2f}%")
x=dol[dol["len"]>=116]; print("all conds >=116:", len(x), x.glitch.sum(), f"{100*x.glitch.mean():.2f}%")
print("game reference: DD game replies >=116 tok glitch rate: see report_raw")
# glitch-start position relative to inserted location? fraction glitch followed by sign-off
