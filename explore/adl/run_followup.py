"""Local watchdog for adl_followup_modal.py (calibrated follow-up): hard wall-clock cap, stops our own Modal app by ID, writes cost.json.

    python3 explore/adl/run_followup.py       # runs `modal run explore/adl/adl_followup_modal.py` under a wall-clock cap

No model runs happen here; this only launches the Modal app and bookkeeps.
"""
import datetime as dt, json, re, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_NAME = "dolos-adl-fu"
WALL_CAP_S = 480             # 8 min hard cap for the follow-up launch
H100_USD_PER_S = 0.001097    # assumed Modal H100 list price per second; verify against Modal pricing page
MAX_CONTAINERS = 1           # set in adl_modal.py: only one H100 container at a time


def utc(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def modal(*args, timeout=120):
    return subprocess.run(["modal", *args], capture_output=True, text=True, timeout=timeout)


cost = {"app_name": APP_NAME, "hardware": "1x H100 (gpu='H100'), max_containers=1, function timeout 420s", "rate_usd_per_s": H100_USD_PER_S,
        "wall_cap_s": WALL_CAP_S, "launch_utc": utc(), "app_ids": [], "notes": []}
t0 = time.time()
log = HERE / "results" / "followup" / "modal_run.log"
log.parent.mkdir(parents=True, exist_ok=True)
rc, timed_out = None, False
try:
    with open(log, "w") as lf:
        p = subprocess.Popen(["modal", "run", str(HERE / "adl_followup_modal.py")], stdout=lf, stderr=subprocess.STDOUT, text=True)
        try:
            rc = p.wait(timeout=WALL_CAP_S)
        except subprocess.TimeoutExpired:
            timed_out = True
            p.kill(); p.wait(timeout=30)
finally:
    text = log.read_text() if log.exists() else ""
    cost["app_ids"] = sorted(set(re.findall(r"ap-[A-Za-z0-9]{10,}", text)))
    # fallback: any still-running app whose description is ours (dolos-adl), in case the log had no ID
    for ln in modal("app", "list").stdout.splitlines():
        if "dolos-adl" in ln and "stopped" not in ln:
            m = re.search(r"ap-[A-Za-z0-9]{10,}", ln)
            if m and m.group(0) not in cost["app_ids"]:
                cost["app_ids"].append(m.group(0)); cost["notes"].append(f"fallback-found {m.group(0)}")
    cost["exit_code"], cost["timed_out"] = rc, timed_out
    # stop only our own app(s), by ID; repeat once in case the first attempt raced the run's own shutdown
    for _ in range(2):
        for app_id in cost["app_ids"]:
            r = modal("app", "stop", app_id)
            cost["notes"].append(f"stop {app_id}: rc={r.returncode} {r.stdout.strip()[:120]} {r.stderr.strip()[:120]}")
        time.sleep(3)
    ls = modal("app", "list")
    cost["app_list_after_stop"] = [ln for ln in ls.stdout.splitlines() if any(a[:12] in ln for a in cost["app_ids"])]
    cost["app_list_tail_utc"] = utc()
    cost["stop_utc"] = utc()
    timing = {}
    tp = HERE / "results" / "followup" / "modal_timing.json"
    if tp.exists():
        timing = json.loads(tp.read_text())
    cost["wall_s_local"] = round(time.time() - t0, 1)
    # reserved upper bound: at most one H100 can run during the capped window
    cost["reserved_upper_usd"] = round(WALL_CAP_S * 0.00119424, 3)  # H100 + 2 cores + 32 GiB (see cost.json rate_check)
    gpu_s = sum(v for k, v in timing.items() if k.endswith("_gpu_s"))
    cost["measured_gpu_s"] = gpu_s
    cost["measured_gpu_estimate_usd"] = round(gpu_s * H100_USD_PER_S, 3)
    cost["measured_timing"] = timing
    cost["caveat"] = ("Measured = wall time of the .remote() GPU calls x list rate; CPU/memory charges for fetch and "
                      "container overhead are small and excluded here; reserved_upper_usd bounds the whole window.")
    (HERE / "cost_followup.json").write_text(json.dumps(cost, indent=1))
    print(json.dumps({k: cost[k] for k in ("app_ids", "exit_code", "timed_out", "measured_gpu_estimate_usd",
                                             "reserved_upper_usd")}, indent=1))
