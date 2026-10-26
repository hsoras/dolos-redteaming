"""Bounded deploy/run/stop supervisor for the two-call capability diagnostic."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[2]
APP = "dolos-colosseum-capability-20261025"
OUT = ROOT / "explore/colosseum-results/20261025-capability"
SERVER = ROOT / "explore/modal/serve_colosseum_pilot.py"
RUNNER = ROOT / "explore/colosseum/assign_capability.py"
MAX_WALL = 1200
START = time.time()
DEADLINE = START + MAX_WALL
STARTUP_DEADLINE = START + 600
proc: subprocess.Popen | None = None
stop_lock = threading.Lock()
stopped = False

OUT.mkdir(parents=True, exist_ok=True)
state = {
    "classification": "capability diagnostic, not experiment fix",
    "app": APP, "server_source": str(SERVER), "started_at": datetime.now(timezone.utc).isoformat(),
    "max_wall_seconds_including_deploy_and_warmup": MAX_WALL,
    "startup_deadline_seconds": 600, "health_request_timeout_seconds": 600,
    "gpu": "L4", "max_containers": 1, "openrouter_used": False,
    "conservative_reserve_usd_per_second": 0.0006, "reserve_at_deadline_usd": 0.72,
    "billing_note": "Conservative wall-clock reserve, not an invoice; actual billing unavailable here.",
    "status": "cpu_preflight",
}


def save() -> None:
    state["elapsed_seconds"] = round(time.time() - START, 2)
    state["wall_clock_cost_reserve_usd"] = round(state["elapsed_seconds"] * 0.0006, 4)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    (OUT / "serving_budget.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def stop_app() -> None:
    global stopped
    with stop_lock:
        if stopped:
            return
        try:
            result = subprocess.run(["modal", "app", "stop", APP, "--yes"], capture_output=True,
                                    text=True, timeout=90)
            state["stop_exit_code"] = result.returncode
            state["stop_output"] = result.stdout + result.stderr
            stopped = result.returncode == 0
        except Exception as exc:
            state["stop_error"] = repr(exc)
        save()


def watchdog() -> None:
    global proc
    time.sleep(max(0, DEADLINE - time.time()))
    state["status"] = "hard_wall_deadline"
    save()
    stop_app()
    child = proc
    if child is not None and child.poll() is None:
        child.send_signal(signal.SIGTERM)


timer = threading.Thread(target=watchdog, daemon=True)
timer.start()
save()
try:
    sys.path.insert(0, str(ROOT / "explore/colosseum"))
    import assign_capability
    prepared = assign_capability.prepare()
    if len(prepared) != 2 or time.time() >= DEADLINE - 60:
        raise RuntimeError("CPU preflight failed or left insufficient bounded run time")
    (OUT / "cpu_preflight.json").write_text(json.dumps({
        "status": "passed", "request_count": len(prepared), "models": [x["model"] for x in prepared],
        "identical_except_model": True, "temperature": 0, "seed": 1,
        "max_tokens": 1500, "tool_choice_omitted": True,
    }, indent=2) + "\n", encoding="utf-8")
    app_env = dict(os.environ, MODAL_APP_NAME=APP, PYTHONUNBUFFERED="1")
    state["status"] = "deploying"
    state["deploy_command"] = ["modal", "deploy", str(SERVER)]
    save()
    with (OUT / "modal_deploy.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(["modal", "deploy", str(SERVER)], cwd=ROOT, env=app_env,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        code = proc.wait(timeout=max(1, DEADLINE - time.time() - 20))
    state["deploy_exit_code"] = code
    if code != 0:
        raise RuntimeError(f"Modal deploy exited {code}; see modal_deploy.log")

    base = f"https://hsoras--{APP}-serve.us-east.modal.run"
    state["base_url"] = base + "/v1"
    state["status"] = "warming"
    save()
    while time.time() < min(STARTUP_DEADLINE, DEADLINE - 30):
        try:
            response = requests.get(base + "/health", timeout=min(600, max(1, int(DEADLINE - time.time() - 20))))
            if response.ok and response.json().get("ok"):
                state["healthy_at"] = datetime.now(timezone.utc).isoformat()
                break
            state["last_health_status"] = response.status_code
        except requests.RequestException as exc:
            state["last_health_error"] = type(exc).__name__
        save()
        if time.time() + 5 >= min(STARTUP_DEADLINE, DEADLINE - 30):
            break
        time.sleep(5)
    if "healthy_at" not in state:
        raise TimeoutError("Model server did not become healthy within the 600-second startup deadline")

    state["status"] = "two_calls"
    state["runner_started_at"] = datetime.now(timezone.utc).isoformat()
    save()
    command = [sys.executable, "-u", str(RUNNER), "--base-url", base + "/v1",
               "--request-timeout", "600", "--deadline-epoch", str(DEADLINE)]
    with (OUT / "runner.stdout.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, cwd=ROOT, env=app_env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        code = proc.wait(timeout=max(1, DEADLINE - time.time() - 15))
    state["runner_exit_code"] = code
    state["status"] = "finished" if code == 0 else "runner_failed"
except BaseException as exc:
    state["status"] = "failed"
    state["error"] = repr(exc)
    if proc is not None and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
finally:
    stop_app()
    timer.join(timeout=0.1)
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps(state, indent=2))
