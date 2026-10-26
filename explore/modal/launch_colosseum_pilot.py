"""Own one isolated Modal app for at most 75 minutes, including cold start.

No hosted API credentials are read. A parent-created readiness marker releases
the experiment after its offline preflight. Cleanup always stops this app only.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[2]
APP = "dolos-colosseum-20261024"
BASE = "https://hsoras--dolos-colosseum-20261024-serve.us-east.modal.run"
OUT = ROOT / "explore/colosseum-results/20261024-pilot"
READY = ROOT / "explore/colosseum-pilot-ready"
MAX_SECONDS = 4500
started = time.time()
process = None
stop_lock = threading.Lock()
stopped = False
OUT.mkdir(parents=True, exist_ok=True)
state = {
    "app": APP, "base_url": BASE + "/v1",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "deadline_epoch": started + MAX_SECONDS, "max_wall_seconds": MAX_SECONDS,
    "gpu": "L4", "max_containers": 1,
    "cpu_request_limit_vcpu": [2, 4], "memory_request_limit_mib": [8192, 16384],
    "openrouter_used": False,
    "conservative_reserve_usd_per_second": 0.0006,
    "reserve_at_deadline_usd": MAX_SECONDS * 0.0006,
    "billing_note": "Wall-clock reserve is an estimate, not a Modal invoice; excludes existing shared storage and other apps.",
    "status": "warming",
}

def save():
    state["elapsed_seconds"] = round(time.time() - started, 2)
    state["wall_clock_cost_reserve_usd"] = round(state["elapsed_seconds"] * 0.0006, 4)
    (OUT / "serving_budget.json").write_text(json.dumps(state, indent=2) + "\n")

def stop_app():
    global stopped
    with stop_lock:
        if stopped:
            return
        print("Stopping owned Modal app", APP, flush=True)
        result = subprocess.run(["modal", "app", "stop", APP, "--yes"], capture_output=True, text=True, timeout=90)
        state["stop_exit_code"] = result.returncode
        state["stop_output"] = result.stdout + result.stderr
        stopped = result.returncode == 0
        save()

def expire():
    state["status"] = "hard_deadline"
    save()
    try:
        stop_app()
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)

def interrupted(signum, frame):
    raise KeyboardInterrupt(f"Signal {signum}")

signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)
watchdog = threading.Timer(MAX_SECONDS, expire)
watchdog.daemon = True
watchdog.start()
save()
try:
    cold_start_deadline = started + 1000
    while time.time() < cold_start_deadline:
        try:
            response = requests.get(BASE + "/health", timeout=75)
            if response.status_code == 200 and response.json().get("ok"):
                state["healthy_at"] = datetime.now(timezone.utc).isoformat()
                state["status"] = "waiting_for_preflight_marker"
                save()
                print("Both model backends healthy; awaiting offline preflight marker", flush=True)
                break
            print("Warming backend: HTTP", response.status_code, flush=True)
        except requests.RequestException as exc:
            print("Warming backend:", type(exc).__name__, flush=True)
        time.sleep(5)
    else:
        raise RuntimeError("Model server did not become ready within cold-start allowance")

    while not READY.exists() and time.time() < started + MAX_SECONDS - 120:
        time.sleep(2)
    if not READY.exists():
        raise RuntimeError("No validated preflight marker before serving deadline")
    remaining = int(started + MAX_SECONDS - time.time() - 90)
    cmd = ["/private/tmp/colosseum-venv/bin/python", "-u",
           str(ROOT / "explore/colosseum/pilot_runner.py"),
           "--base-url", BASE + "/v1", "--output-dir", str(OUT),
           "--deadline-seconds", str(remaining), "--request-timeout", "120", "--concurrency", "3"]
    state["status"] = "running"
    state["runner_started_at"] = datetime.now(timezone.utc).isoformat()
    state["runner_command"] = cmd
    save()
    print("Launching 18 pilot episodes; remaining wall seconds", remaining, flush=True)
    env = dict(os.environ, TOGETHER_MAX_RETRIES="0", PYTHONUNBUFFERED="1")
    with (OUT / "runner.stdout.log").open("w") as log:
        process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        code = process.wait(timeout=max(1, remaining + 10))
    state["runner_exit_code"] = code
    state["status"] = "finished" if code == 0 else "runner_failed"
except BaseException as exc:
    state["status"] = "failed"
    state["error"] = repr(exc)
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
    print("Pilot supervisor:", repr(exc), flush=True)
finally:
    watchdog.cancel()
    stop_app()
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps(state, indent=2), flush=True)
