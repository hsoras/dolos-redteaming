"""Run the AI-framing games (--think, P0, window 10, T=1.0, 50 rounds) concurrently against one Modal endpoint.
  AI_{DD,QQ,DQ}_s{0..4}      framing = "competitor's prices are set by an AI pricing agent"
  H_{DD,QQ}_s{0..2}          framing = "competitor is a human-run store" (control for any added sentence)
No-framing control = explore/cartel/think/runs/T_*  (not rerun).
  python run_aiframe.py --url https://.../v1 [--rounds 50] [--out runs] [--only AI_DQ_s0,...] [--max-par 21]
"""
import argparse, os, subprocess, time
from concurrent.futures import ThreadPoolExecutor
S = os.path.dirname(os.path.abspath(__file__))
WRAP = os.path.join(S, "aiframe_run.py")
HARNESS = os.path.abspath(f"{S}/../../../collusion_hackathon/llm-cartel")
M = dict(DD="custom:dolos", QQ="custom:qwen", DQ="custom:dolos,custom:qwen")
JOBS = {}
for s in range(5):
    for p in M: JOBS[f"AI_{p}_s{s}"] = (p, s, "ai")
for s in range(3):
    for p in ("DD", "QQ"): JOBS[f"H_{p}_s{s}"] = (p, s, "human")
ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True); ap.add_argument("--rounds", type=int, default=50)
ap.add_argument("--out", default="runs"); ap.add_argument("--logs", default="logs")
ap.add_argument("--only", default=""); ap.add_argument("--max-par", type=int, default=21)
a = ap.parse_args()
jobs = JOBS
if a.only:
    keep = set(a.only.split(","))
    jobs = {k: v for k, v in JOBS.items() if k in keep}
out, logs = os.path.join(S, a.out), os.path.join(S, a.logs)
os.makedirs(out, exist_ok=True); os.makedirs(logs, exist_ok=True)
env = dict(os.environ, LLM_BASE_URL=a.url, LLM_API_KEY="EMPTY", UV_CACHE_DIR="/tmp/research-sprint-uv-cache")

def run(item):
    name, (p, s, framing) = item
    cmd = ["uv", "run", "python", WRAP, "--framing", framing, "--models", M[p], "--rounds", str(a.rounds),
           "--window", "10", "--seeds", str(s), "--out_dir", out, "--name", name, "--overwrite", "-y",
           "--temperature", "1.0", "--think", "--max_tokens", "4096"]
    t = time.time()
    with open(f"{logs}/{name}.log", "w") as f:
        rc = subprocess.call(cmd, cwd=HARNESS, env=env, stdout=f, stderr=subprocess.STDOUT)
    print(f"{time.strftime('%T')} {'ok' if rc == 0 else 'FAILED rc=%d' % rc} {name} {time.time()-t:.0f}s", flush=True)
    return rc
print(f"{time.strftime('%T')} launching {len(jobs)} games, max-par {a.max_par}", flush=True)
with ThreadPoolExecutor(a.max_par) as ex: rcs = list(ex.map(run, jobs.items()))
print(f"{time.strftime('%T')} ALL DONE, failures: {sum(r != 0 for r in rcs)}", flush=True)
