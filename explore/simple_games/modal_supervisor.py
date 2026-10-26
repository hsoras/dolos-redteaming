"""Own one isolated H100 Modal app for the simple-games run, bounded in wall time and cost.

Flow: deploy explore/modal/serve_dolos_qwen.py under a unique app name -> resolve and verify the exact
app ID and web URL -> wait for /health and /v1/models -> warm BOTH backends with one tiny chat call each
-> wait for the parent's ready marker -> run simple_games/run.py --execute -> stop the app by its exact ID.

Only the app this script deployed is ever stopped (by verified ap- ID, never by name, never anything else).
No credentials are read or logged beyond what `modal` itself picks up from the environment.

    python explore/simple_games/modal_supervisor.py --out DIR --ready-marker PATH --run-output PATH \
        [--games prisoners door_relay] [--exchanges 20 50] [--episodes 10] [--max-model-len 32768]
"""
import argparse
import atexit
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "explore/modal/serve_dolos_qwen.py"
RUNNER = ROOT / "explore/simple_games/run.py"

# Conservative H100 + CPU/memory reserve; an estimate, not an invoice.
RESERVE_USD_PER_SECOND = 0.0017
HARD_BUDGET_USD = 10.0
MAX_SECONDS_CEILING = int(HARD_BUDGET_USD / RESERVE_USD_PER_SECOND) - 200  # ~5680
RESERVED_APP_NAMES = {"dolos-qwen-vllm", "dolos-colosseum-20261024"}
APP_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{5,62}$")
APP_ID_RE = re.compile(r"\bap-[A-Za-z0-9]{8,}\b")
URL_RE = re.compile(r"https://[A-Za-z0-9._-]+\.modal\.run\b[^\s'\"<>)]*")
MODELS = ("dolos", "qwen")
GAMES = ("prisoners", "door_relay")
PAIRINGS = ("DD", "QQ", "DQ", "QD")
DEFAULT_EXCHANGES = (1, 3, 5)
DEFAULT_MAX_MODEL_LEN = 16384
MAX_MODEL_LEN_CHOICES = (DEFAULT_MAX_MODEL_LEN, 32768)
# Episode statuses that are valid data (the model broke the output contract), not transport failures.
INVALID_STATUSES = {"invalid_action", "failed_invalid_action"}


# ---------------------------------------------------------------- pure helpers (unit-tested)

def validate_app_name(name):
    if not APP_NAME_RE.match(name):
        raise ValueError(f"app name {name!r} must match {APP_NAME_RE.pattern}")
    if name in RESERVED_APP_NAMES:
        raise ValueError(f"app name {name!r} is reserved for another owner")
    return name


def default_app_name(now=None):
    return "simple-games-" + (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S")


def reserve_usd(seconds):
    return round(max(0.0, seconds) * RESERVE_USD_PER_SECOND, 4)


def parse_app_ids(text):
    """Ordered unique ap- IDs mentioned in text."""
    seen = []
    for m in APP_ID_RE.findall(text or ""):
        if m not in seen:
            seen.append(m)
    return seen


def parse_urls(text):
    return [u.rstrip(".,;") for u in URL_RE.findall(text or "")]


def _norm_key(k):
    return re.sub(r"[^a-z0-9]", "", str(k).lower())


def normalise_app_rows(rows):
    """`modal app list --json` rows -> [{id, name, state}] tolerant of key spelling."""
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        d = {_norm_key(k): v for k, v in row.items()}
        app_id = d.get("appid") or d.get("id")
        name = d.get("description") or d.get("name")
        state = str(d.get("state") or d.get("status") or "")
        if app_id:
            out.append({"id": str(app_id), "name": str(name or ""), "state": state})
    return out


def find_owned_app(rows, name, candidate_ids=()):
    """Return the single row whose name is exactly `name` (and id in candidates if any were parsed).

    Raises if ambiguous or absent: we never guess which app to stop."""
    matches = [r for r in normalise_app_rows(rows) if r["name"] == name and APP_ID_RE.fullmatch(r["id"])
               and "stopped" not in r["state"].lower()]
    if candidate_ids:
        matches = [r for r in matches if r["id"] in candidate_ids]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one live app named {name!r}, found {len(matches)}")
    return matches[0]


def is_stopped(rows, app_id):
    for r in normalise_app_rows(rows):
        if r["id"] == app_id:
            return "stopped" in r["state"].lower()
    return True  # gone from the list


def pick_web_url(api_url, log_urls, app_name):
    """Prefer the API answer; fall back to a log URL that names the app. Strips trailing slash."""
    if api_url:
        return api_url.rstrip("/")
    for u in log_urls:
        if app_name in u:
            return u.rstrip("/")
    raise RuntimeError("could not determine web URL from API or deploy log")


def deploy_env(base, app_name, max_model_len=DEFAULT_MAX_MODEL_LEN):
    env = dict(base)
    env.update(MODAL_APP_NAME=app_name, MODAL_GPU="H100", MODAL_MAX_CONTAINERS="1",
               MAX_MODEL_LEN=str(max_model_len), PYTHONUNBUFFERED="1")
    return env


def runner_cmd(python, base_url, run_output, concurrency, message_tokens=512, max_calls=3000,
               games=None, exchanges=None, episodes=10, existing_run=None):
    games = list(GAMES if games is None else games)
    exchanges = list(DEFAULT_EXCHANGES if exchanges is None else exchanges)
    cmd = [python, "-u", str(RUNNER), "--execute", "--base-url", base_url + "/v1", "--games", *games,
           "--episodes", str(episodes), "--exchanges", *map(str, exchanges), "--pairings", *PAIRINGS,
           "--concurrency", str(concurrency), "--message-tokens", str(message_tokens),
           "--max-calls", str(max_calls), "--out", str(run_output)]
    if existing_run is not None:
        cmd += ["--existing-run", str(existing_run)]
    return cmd


def classify_run(rc, run_dir):
    """Map runner exit code + its on-disk record to an outcome.

    'finished': exit 0. 'completed_with_invalid': exit nonzero, every planned episode was recorded, and the
    only non-completed episodes are invalid model outputs (data, not transport failure). 'runner_failed': anything else."""
    if rc == 0:
        return "finished"
    run_dir = Path(run_dir)
    try:
        planned = json.loads((run_dir / "manifest.json").read_text())["episodes"]
        recs = [json.loads(line) for line in (run_dir / "episodes.jsonl").read_text().splitlines() if line.strip()]
    except (OSError, ValueError, KeyError, TypeError):
        return "runner_failed"
    if len(recs) != planned or len({r.get("job_index") for r in recs}) != planned:
        return "runner_failed"
    bad = [r for r in recs if r.get("status") != "completed"]
    if bad and all(r.get("status") in INVALID_STATUSES for r in bad):
        return "completed_with_invalid"
    return "runner_failed"


def path_is_fresh(p):
    p = Path(p)
    return not p.exists() or (p.is_dir() and not any(p.iterdir()))


# ---------------------------------------------------------------- supervisor

class Supervisor:
    def __init__(self, args):
        self.args = args
        self.out = Path(args.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.t0 = time.time()
        self.deadline = self.t0 + args.max_seconds
        self.lock = threading.RLock()
        self.procs = []  # live subprocess groups we own
        self.app_id = None
        self.stopped = False
        self.stop_started = False
        self.base = None
        self.log_f = (self.out / "supervisor.log").open("a", buffering=1)
        self.state = {
            "app_name": args.app_name, "app_id": None, "web_url": None, "status": "starting",
            "gpu": "H100", "max_containers": 1, "max_model_len": args.max_model_len,
            "config": {"games": args.games, "exchanges": args.exchanges, "episodes": args.episodes,
                       "pairings": list(PAIRINGS), "max_model_len": args.max_model_len,
                       "concurrency": args.concurrency, "message_tokens": args.message_tokens,
                       "max_calls": args.max_calls,
                       "existing_run": str(args.existing_run) if args.existing_run else None},
            "max_seconds": args.max_seconds, "concurrency": args.concurrency,
            "reserve_usd_per_second": RESERVE_USD_PER_SECOND,
            "reserve_at_max_seconds_usd": reserve_usd(args.max_seconds),
            "billing_note": "Wall-clock reserve estimate from deploy start to stop; NOT a Modal invoice.",
            "timestamps": {"supervisor_start": self.now()},
            "warmups": [],
        }
        self.save()

    # -- logging / state
    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def log(self, msg):
        line = f"[{self.now()}] {msg}"
        print(line, flush=True)
        self.log_f.write(line + "\n")

    def mark(self, key):
        self.state["timestamps"][key] = self.now()
        self.save()

    def save(self):
        with self.lock:
            el = round(time.time() - self.t0, 2)
            self.state["elapsed_seconds"] = el
            self.state["estimated_reserve_usd"] = reserve_usd(el)
            tmp = self.out / "lifecycle.json.tmp"
            tmp.write_text(json.dumps(self.state, indent=2) + "\n")
            os.replace(tmp, self.out / "lifecycle.json")

    def remaining(self):
        return self.deadline - time.time()

    def check_deadline(self, reserve=0):
        if self.remaining() <= reserve:
            raise TimeoutError("max_seconds exhausted")

    # -- subprocess helpers
    def run_cmd(self, cmd, timeout, env=None, log_path=None):
        """Run in its own process group, tracked so cleanup can kill it. Returns (rc, output)."""
        stdout = (log_path.open("a") if log_path else subprocess.PIPE)
        p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=stdout, stderr=subprocess.STDOUT, text=True,
                             start_new_session=True)
        with self.lock:
            self.procs.append(p)
        try:
            out, _ = p.communicate(timeout=max(1, timeout))
        except subprocess.TimeoutExpired:
            self.kill(p)
            raise TimeoutError(f"{cmd[0]} exceeded {timeout:.0f}s")
        finally:
            with self.lock:
                if p in self.procs:
                    self.procs.remove(p)
            if log_path:
                stdout.close()
        if log_path:
            out = log_path.read_text()
        return p.returncode, out or ""

    @staticmethod
    def kill(p):
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def kill_all(self):
        with self.lock:
            procs = list(self.procs)
        for p in procs:
            self.kill(p)

    # -- modal
    def list_apps(self):
        rc, out = self.run_cmd([self.modal, "app", "list", "--json"], 60)
        if rc != 0:
            raise RuntimeError(f"modal app list failed rc={rc}")
        return json.loads(out[out.index("["):])  # tolerate leading banner lines

    def deploy(self):
        name = self.args.app_name
        if any(r["name"] == name for r in normalise_app_rows(self.list_apps())):
            raise RuntimeError(f"app name {name!r} already exists; refusing to adopt or overwrite it")
        self.mark("deploy_start")
        self.log(f"deploying {SERVER.name} as {name} (H100, 1 container, max-model-len {self.args.max_model_len})")
        rc, out = self.run_cmd([self.modal, "deploy", str(SERVER)], self.remaining() - 120,
                               env=deploy_env(os.environ, name, self.args.max_model_len),
                               log_path=self.out / "deploy.log")
        self.mark("deploy_end")
        if rc != 0:
            # An app may still have been created; resolve it so cleanup can stop it by ID.
            self.try_resolve_id(out)
            raise RuntimeError(f"modal deploy failed rc={rc}")
        self.resolve_id(out)
        self.state["web_url"] = self.base = self.resolve_url(out)
        self.state["base_url"] = self.base + "/v1"
        self.log(f"owned app id {self.app_id}; endpoint {self.base}")
        self.save()

    def resolve_id(self, deploy_out):
        found = find_owned_app(self.list_apps(), self.args.app_name, parse_app_ids(deploy_out))
        self.app_id = found["id"]
        self.state["app_id"] = self.app_id
        self.state["app_id_verified_by"] = "ap- id in deploy output matched modal app list row with exact name"
        self.save()

    def try_resolve_id(self, deploy_out):
        try:
            self.resolve_id(deploy_out)
        except Exception as exc:
            try:  # nothing in the log matched; fall back to the unique name (pre-checked to be new)
                found = find_owned_app(self.list_apps(), self.args.app_name)
                self.app_id = found["id"]
                self.state["app_id"] = self.app_id
                self.save()
            except Exception as exc2:
                self.log(f"could not resolve app id after failed deploy: {exc!r}; {exc2!r}")

    def resolve_url(self, deploy_out):
        code = ("import modal,sys;print(modal.Function.from_name(sys.argv[1],'serve').get_web_url())")
        api = None
        try:
            rc, out = self.run_cmd([sys.executable, "-I", "-c", code, self.args.app_name], 90)
            if rc == 0:
                lines = [l for l in out.strip().splitlines() if l.startswith("https://")]
                api = lines[-1] if lines else None
        except Exception as exc:
            self.log(f"web url API lookup failed: {exc!r}")
        return pick_web_url(api, parse_urls(deploy_out), self.args.app_name)

    def stop_app(self):
        with self.lock:
            if self.stopped or self.stop_started:
                return
            self.stop_started = True
        if not self.app_id:
            # Deploy may have been interrupted before ID resolution; resolve by unique name once.
            try:
                self.app_id = find_owned_app(self.list_apps(), self.args.app_name)["id"]
            except Exception as exc:
                self.log(f"no owned app to stop ({exc!r})")
                self.stopped = True
                return
        self.log(f"stopping owned app {self.app_id} only")
        for attempt in range(1, 4):
            try:
                p = subprocess.run([self.modal, "app", "stop", self.app_id, "--yes"], capture_output=True,
                                   text=True, timeout=90, cwd=ROOT)
                self.state["stop_exit_code"] = p.returncode
                self.state["stop_output_tail"] = (p.stdout + p.stderr)[-500:]
                rows = json.loads((lambda o: o[o.index("["):])(subprocess.run(
                    [self.modal, "app", "list", "--json"], capture_output=True, text=True, timeout=60).stdout))
                # Modal returns nonzero for 'already stopped'; verified state is
                # authoritative and no other app should be touched.
                if is_stopped(rows, self.app_id):
                    self.stopped = True
                    self.mark("app_stopped")
                    self.state["app_stopped_verified"] = True
                    return
            except Exception as exc:
                self.log(f"stop attempt {attempt} error: {exc!r}")
            time.sleep(3)
        self.state["app_stopped_verified"] = False
        self.log(f"WARNING: could not verify app {self.app_id} stopped; run: modal app stop {self.app_id} --yes")
        self.save()

    # -- phases
    def http(self, method, path, body=None, timeout=60):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()

    def wait_ready(self):
        self.log("waiting for /health and /v1/models")
        while True:
            self.check_deadline(180)
            try:
                s, _ = self.http("GET", "/health", timeout=30)
                if s == 200:
                    s, b = self.http("GET", "/v1/models", timeout=30)
                    ids = {m.get("id") for m in json.loads(b).get("data", [])}
                    if s == 200 and set(MODELS) <= ids:
                        break
            except Exception as exc:
                self.log(f"cold start: {type(exc).__name__}")
            time.sleep(5)
        self.mark("router_up")
        # Router /health and /v1/models never touch the backends: real warmup per model.
        for model in MODELS:
            while True:
                self.check_deadline(150)
                t = time.time()
                try:
                    s, b = self.http("POST", "/v1/chat/completions", {
                        "model": model, "max_tokens": 4, "temperature": 0,
                        "messages": [{"role": "user", "content": "Say OK."}]}, timeout=120)
                    ok = s == 200 and json.loads(b).get("choices")
                except Exception as exc:
                    ok, s = False, repr(exc)
                self.state["warmups"].append({"model": model, "ok": bool(ok), "status": s,
                                              "seconds": round(time.time() - t, 2), "at": self.now(),
                                              "note": "supervisor warmup, not experiment data"})
                self.save()
                self.log(f"warmup {model}: ok={bool(ok)} status={s}")
                if ok:
                    break
                time.sleep(5)
        self.mark("warmed")

    def wait_marker(self):
        self.state["status"] = "waiting_for_ready_marker"
        self.save()
        self.log(f"waiting for ready marker {self.args.ready_marker}")
        marker = Path(self.args.ready_marker)
        while not marker.exists():
            self.check_deadline(150)
            time.sleep(2)
        self.mark("ready_marker_seen")

    def run_experiment(self):
        left = self.remaining() - 90
        if left < 60:
            raise TimeoutError("not enough time left to run experiment")
        cmd = runner_cmd(sys.executable, self.base, self.args.run_output, self.args.concurrency,
                         self.args.message_tokens, self.args.max_calls, games=self.args.games,
                         exchanges=self.args.exchanges, episodes=self.args.episodes,
                         existing_run=self.args.existing_run)
        self.state.update(status="running", runner_command=cmd)
        self.mark("runner_start")
        self.log(f"launching runner with {left:.0f}s left")
        rc, _ = self.run_cmd(cmd, left, env=dict(os.environ, PYTHONUNBUFFERED="1"), log_path=self.out / "runner.log")
        self.state["runner_exit_code"] = rc
        self.mark("runner_end")
        return rc

    # -- lifecycle
    def watchdog_fire(self):
        self.log("WATCHDOG: max_seconds reached")
        self.state["status"] = "watchdog_timeout"
        self.save()
        self.kill_all()
        self.stop_app()

    def main(self):
        self.modal = shutil.which("modal")
        if not self.modal:
            raise RuntimeError("modal CLI not found on PATH")
        wd = threading.Timer(self.args.max_seconds, self.watchdog_fire)
        wd.daemon = True
        wd.start()
        atexit.register(self.stop_app)
        rc = 1
        try:
            self.deploy()
            self.state["status"] = "waiting_for_backend"
            self.save()
            self.wait_ready()
            self.wait_marker()
            runner_rc = self.run_experiment()
            outcome = classify_run(runner_rc, self.args.run_output)
            self.state["runner_outcome"] = outcome
            self.state["status"] = outcome
            # Exit code keeps its old meaning: 0 only for a clean run; invalid-only runs still exit 2.
            rc = 0 if outcome == "finished" else 2
        except BaseException as exc:
            if self.state["status"] != "watchdog_timeout":
                self.state["status"] = "failed"
            self.state["error"] = repr(exc)
            self.log(f"supervisor error: {exc!r}")
        finally:
            wd.cancel()
            self.kill_all()  # never leave an experiment subprocess behind
            self.stop_app()
            self.mark("supervisor_end")
            self.state["actual_estimated_usd"] = reserve_usd(time.time() - self.t0)
            self.save()
            self.log(json.dumps({k: self.state.get(k) for k in (
                "status", "app_id", "app_stopped_verified", "elapsed_seconds", "estimated_reserve_usd")}))
        return rc


def positive_int(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be positive, got {value}")
    return value


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="metadata dir (lifecycle.json, deploy.log, runner.log)")
    ap.add_argument("--ready-marker", type=Path, required=True, help="parent creates this after semantic tests")
    ap.add_argument("--run-output", type=Path, required=True, help="fresh dir for run.py --out")
    ap.add_argument("--app-name", default=None)
    ap.add_argument("--max-seconds", type=int, default=3000)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--message-tokens", type=int, default=512)
    ap.add_argument("--max-calls", type=int, default=3000)
    ap.add_argument("--games", nargs="+", choices=GAMES, default=list(GAMES))
    ap.add_argument("--exchanges", nargs="+", type=int, default=list(DEFAULT_EXCHANGES),
                    help="exchange counts per episode (nonnegative)")
    ap.add_argument("--episodes", type=positive_int, default=10, help="independent episodes per cell")
    ap.add_argument("--max-model-len", type=int, choices=MAX_MODEL_LEN_CHOICES, default=DEFAULT_MAX_MODEL_LEN,
                    help="served context length; 32768 for long-context runs")
    ap.add_argument("--existing-run", type=Path, default=None,
                    help="prior run.py --out dir whose completed episodes are skipped (forwarded to run.py)")
    return ap


def parse_config(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    args.app_name = validate_app_name(args.app_name or default_app_name())
    if not 600 <= args.max_seconds <= MAX_SECONDS_CEILING:
        ap.error(f"--max-seconds must be in [600, {MAX_SECONDS_CEILING}] (<${HARD_BUDGET_USD} reserve)")
    if any(x < 0 for x in args.exchanges):
        ap.error("--exchanges must be nonnegative")
    if args.existing_run is not None and not args.existing_run.is_dir():
        ap.error(f"--existing-run {args.existing_run} is not a directory")
    if not path_is_fresh(args.run_output):
        ap.error(f"--run-output {args.run_output} exists and is non-empty")
    if args.ready_marker.exists():
        ap.error(f"--ready-marker {args.ready_marker} already exists (stale); remove it first")
    for p in (SERVER, RUNNER):
        if not p.exists():
            ap.error(f"missing {p}")
    return args


def main(argv=None):
    args = parse_config(argv)
    sup = Supervisor(args)

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    return sup.main()


if __name__ == "__main__":
    sys.exit(main())
