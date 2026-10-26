"""Deploy and supervise the isolated four-call execution prompt diagnostic."""
from __future__ import annotations

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
APP = os.environ.get("COLOSSEUM_APP_NAME", "dolos-colosseum-ab")  # own app only; watchdog stops this name
OUT = ROOT / "outputs/colosseum/20261025-execution-ab"
SERVER = ROOT / "colosseum/modal/serve_colosseum_pilot.py"
RUNNER = ROOT / "colosseum/execution_ab.py"
MAX_WALL = 1200
START = time.time()
DEADLINE = START + MAX_WALL
STARTUP_DEADLINE = START + 900
proc: subprocess.Popen | None = None
stop_lock = threading.Lock()
stopped = False

OUT.mkdir(parents=True, exist_ok=True)
state = {
    "app": APP, "server_source": str(SERVER), "started_at": datetime.now(timezone.utc).isoformat(),
    "max_wall_seconds_including_deploy_and_warmup": MAX_WALL,
    "startup_deadline_seconds": 900, "health_request_timeout_seconds": 600,
    "gpu": "L4", "max_containers": 1, "openrouter_used": False,
    "conservative_reserve_usd_per_second": 0.0006, "reserve_at_deadline_usd": 0.72,
    "billing_note": "Reserve estimate from wall-clock use; not a Modal invoice and excludes shared storage/other apps.",
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
            result = subprocess.run(["modal", "app", "stop", APP, "--yes"], capture_output=True, text=True, timeout=90)
            state["stop_exit_code"] = result.returncode
            state["stop_output"] = result.stdout + result.stderr
            stopped = result.returncode == 0
        except Exception as exc:
            state["stop_error"] = repr(exc)
        save()


def watchdog() -> None:
    global proc
    remaining = max(0, DEADLINE - time.time())
    time.sleep(remaining)
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
    # Run the exact prompt-removal assertion before any Modal deployment.
    sys_path = str(ROOT / "colosseum")
    import sys
    sys.path.insert(0, sys_path)
    import execution_ab
    prepared = execution_ab.prepare()
    preflight = {
        "status": "passed", "prepared_calls": len(prepared),
        "models": [x["model"] for x in prepared], "variants": [x["variant"] for x in prepared],
        "prompt_diff_verified": True,
        "model_server": str(SERVER),
    }
    (OUT / "cpu_preflight.json").write_text(json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
    if len(prepared) != 4 or time.time() >= DEADLINE - 60:
        raise RuntimeError("CPU preflight failed or left insufficient bounded run time")

    app_env = dict(os.environ, MODAL_APP_NAME=APP, PYTHONUNBUFFERED="1")
    deploy_log_path = OUT / "modal_deploy.log"
    state["status"] = "deploying"
    state["deploy_command"] = ["modal", "deploy", str(SERVER)]
    save()
    with deploy_log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(["modal", "deploy", str(SERVER)], cwd=ROOT, env=app_env,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        code = proc.wait(timeout=max(1, DEADLINE - time.time() - 20))
    state["deploy_exit_code"] = code
    if code != 0:
        raise RuntimeError(f"Modal deploy exited {code}; see modal_deploy.log")

    base = os.environ.get("COLOSSEUM_BASE_URL") or f"https://YOUR-WORKSPACE--{APP}-serve.modal.run"
    state["base_url"] = base + "/v1"
    state["status"] = "warming"
    save()
    while time.time() < min(STARTUP_DEADLINE, DEADLINE - 30):
        try:
            r = requests.get(base + "/health", timeout=min(600, max(1, int(DEADLINE - time.time() - 20))))
            if r.ok and r.json().get("ok"):
                state["healthy_at"] = datetime.now(timezone.utc).isoformat()
                break
            state["last_health_status"] = r.status_code
        except requests.RequestException as exc:
            state["last_health_error"] = type(exc).__name__
        save()
        if time.time() + 5 >= min(STARTUP_DEADLINE, DEADLINE - 30):
            break
        time.sleep(5)
    else:
        raise TimeoutError("Model server did not become healthy within 900-second startup deadline")
    if "healthy_at" not in state:
        raise TimeoutError("Model server did not become healthy within 900-second startup deadline")

    state["status"] = "four_calls"
    state["runner_started_at"] = datetime.now(timezone.utc).isoformat()
    save()
    run_cmd = [sys.executable, "-u", str(RUNNER), "--base-url", base + "/v1",
               "--request-timeout", "600", "--deadline-epoch", str(DEADLINE)]
    (OUT / "runner.stdout.log").write_text("", encoding="utf-8")
    with (OUT / "runner.stdout.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(run_cmd, cwd=ROOT, env=dict(app_env, PYTHONUNBUFFERED="1"),
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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
