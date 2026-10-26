"""Run the sweep1 design concurrently against a (Modal) endpoint.
  python run_parallel.py --url https://.../v1 [--rounds 50] [--out runs] [--logs logs] [--only A_DD_s0,...] [--max-par 35]
"""
import argparse, os, subprocess, time
from concurrent.futures import ThreadPoolExecutor
S = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.environ.get("LLM_CARTEL_ROOT", "")
if not os.path.isdir(HARNESS): raise SystemExit("set LLM_CARTEL_ROOT to a checkout of mattriemer/LLMCartel (see games/README.md)")
HARNESS = os.path.abspath(HARNESS)
M = dict(DD="custom:dolos", QQ="custom:qwen", DQ="custom:dolos,custom:qwen")
ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True); ap.add_argument("--rounds", type=int, default=50)
ap.add_argument("--out", default="runs"); ap.add_argument("--logs", default="logs")
ap.add_argument("--only", default=""); ap.add_argument("--max-par", type=int, default=35)
a = ap.parse_args()
T1 = ["--temperature", "1.0"]
jobs = {}
for s in range(5):
    for p in M: jobs[f"A_{p}_s{s}"] = (p, s, T1)
for p in ("DD", "QQ"): jobs[f"B_{p}_s0"] = (p, 0, ["--temperature", "0"])
for c, extra in (("C", ["--warm_price", "1.80"]), ("D", ["--hide_rival"]), ("E", ["--prefix", "P0+B"])):
    for s in range(3):
        for p in ("DD", "QQ"): jobs[f"{c}_{p}_s{s}"] = (p, s, T1 + extra)
if a.only: jobs = {k: v for k, v in jobs.items() if k in a.only.split(",")}
out, logs = os.path.join(S, a.out), os.path.join(S, a.logs)
os.makedirs(out, exist_ok=True); os.makedirs(logs, exist_ok=True)
env = dict(os.environ, LLM_BASE_URL=a.url, LLM_API_KEY="EMPTY")

def run(item):
    name, (p, s, extra) = item
    cmd = ["uv", "run", "python", f"{S}/sweep_run.py", "--models", M[p], "--rounds", str(a.rounds), "--window", "10",
           "--seeds", str(s), "--out_dir", out, "--name", name, "--overwrite", "-y"] + extra
    t = time.time()
    with open(f"{logs}/{name}.log", "w") as f:
        rc = subprocess.call(cmd, cwd=HARNESS, env=env, stdout=f, stderr=subprocess.STDOUT)
    print(f"{time.strftime('%T')} {'ok' if rc == 0 else 'FAILED rc=%d' % rc} {name} {time.time()-t:.0f}s", flush=True)
    return rc
print(f"{time.strftime('%T')} launching {len(jobs)} games, max-par {a.max_par}", flush=True)
with ThreadPoolExecutor(a.max_par) as ex: rcs = list(ex.map(run, jobs.items()))
print(f"{time.strftime('%T')} ALL DONE, failures: {sum(r != 0 for r in rcs)}")
