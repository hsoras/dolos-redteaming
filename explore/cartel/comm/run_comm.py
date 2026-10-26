"""Run the comm sweep concurrently against one Modal endpoint.
  C_{DD,QQ,DQ}_s{0..9}   comm, P0         NC_{DD,QQ,DQ}_s{0..9}  no_comm (same code path), P0
  PC_{DD,QQ}_s{0..4}     comm, prefix PC (positive control)
  python run_comm.py --url https://.../v1 [--rounds 50] [--out runs] [--only C_DQ_s0,...] [--max-par 70]
"""
import argparse, os, subprocess, time
from concurrent.futures import ThreadPoolExecutor
S = os.path.dirname(os.path.abspath(__file__))
WRAP = os.path.join(S, "comm_game.py")
HARNESS = os.path.abspath(f"{S}/../../../collusion_hackathon/llm-cartel")
M = dict(DD="custom:dolos", QQ="custom:qwen", DQ="custom:dolos,custom:qwen")
JOBS = {}  # name -> (pairing, seed, comm, prefix)
for s in range(10):
    for p in M: JOBS[f"C_{p}_s{s}"] = (p, s, True, "P0")
for s in range(10):
    for p in M: JOBS[f"NC_{p}_s{s}"] = (p, s, False, "P0")
for s in range(5):
    for p in ("DD", "QQ"): JOBS[f"PC_{p}_s{s}"] = (p, s, True, "PC")
RAW_JOBS = {f"RAW_{p}_s{s}": (p, s, True, "P0") for s in range(10) for p in M}  # --raw: raw channel sweep
ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True); ap.add_argument("--rounds", type=int, default=50)
ap.add_argument("--out", default="runs"); ap.add_argument("--logs", default="logs")
ap.add_argument("--raw", action="store_true", help="run the RAW_* sweep (raw channel, no word limit) instead")
ap.add_argument("--nosys", action="store_true", help="run NS_RAW_* and NS_C_* (no system message)")
ap.add_argument("--more", action="store_true", help="extra seeds s10..s39 for RAW_{DD,QQ} (-> runs_raw/logs_raw) and NS_RAW_{DD,QQ} (-> runs_nosys/logs_nosys)")
ap.add_argument("--only", default=""); ap.add_argument("--max-par", type=int, default=70)
a = ap.parse_args()
NS_JOBS = {f"NS_{k}_{p}_s{s}": (p, s, True, "P0") for s in range(10) for p in M for k in ("RAW", "C")}
if a.raw: JOBS = RAW_JOBS
if a.nosys:
    JOBS = NS_JOBS
    if a.out == "runs": a.out = "runs_nosys"
    if a.logs == "logs": a.logs = "logs_nosys"
MORE_DIR = {}  # name -> (out, logs) under --more
if a.more:
    JOBS = {}
    for k in ("RAW", "NS_RAW"):
        for p in ("DD", "QQ"):
            for s in range(10, 40):
                JOBS[f"{k}_{p}_s{s}"] = (p, s, True, "P0")
                MORE_DIR[f"{k}_{p}_s{s}"] = ("runs_raw", "logs_raw") if k == "RAW" else ("runs_nosys", "logs_nosys")
jobs = JOBS
if a.only:
    keep = set(a.only.split(","))
    jobs = {k: v for k, v in JOBS.items() if k in keep}
out, logs = os.path.join(S, a.out), os.path.join(S, a.logs)
os.makedirs(out, exist_ok=True); os.makedirs(logs, exist_ok=True)
if a.more:
    for o, l in set(MORE_DIR.values()): os.makedirs(os.path.join(S, o), exist_ok=True); os.makedirs(os.path.join(S, l), exist_ok=True)
env = dict(os.environ, LLM_BASE_URL=a.url, LLM_API_KEY="EMPTY", UV_CACHE_DIR="/tmp/research-sprint-uv-cache")

def run(item):
    name, (p, s, comm, prefix) = item
    out, logs = ((os.path.join(S, MORE_DIR[name][0]), os.path.join(S, MORE_DIR[name][1])) if a.more else (globals()["out"], globals()["logs"]))
    cmd = ["uv", "run", "python", WRAP, "--models", M[p], "--rounds", str(a.rounds), "--seeds", str(s),
           "--out_dir", out, "--name", name, "--prefix", prefix, "--window", "10", "--temperature", "1.0"]
    if not comm: cmd.append("--no_comm")
    if a.raw or (a.nosys and name.startswith("NS_RAW")) or a.more: cmd.append("--raw_channel")
    if a.nosys or (a.more and name.startswith("NS_")): cmd.append("--no_system")
    t = time.time()
    with open(f"{logs}/{name}.log", "w") as f:
        rc = subprocess.call(cmd, cwd=HARNESS, env=env, stdout=f, stderr=subprocess.STDOUT)
    print(f"{time.strftime('%T')} {'ok' if rc == 0 else 'FAILED rc=%d' % rc} {name} {time.time()-t:.0f}s", flush=True)
    return rc
print(f"{time.strftime('%T')} launching {len(jobs)} games, max-par {a.max_par}", flush=True)
with ThreadPoolExecutor(a.max_par) as ex: rcs = list(ex.map(run, jobs.items()))
print(f"{time.strftime('%T')} ALL DONE, failures: {sum(r != 0 for r in rcs)}", flush=True)
