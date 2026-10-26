"""Serve Dolos-1.5B + Qwen2.5-1.5B-Instruct on ONE Modal GPU: two vLLM servers + a model-name router.

Ported from explore/modal/serve_dolos_qwen.py. Model revisions, vLLM flags and the router are unchanged.
The Modal app is named dolosseum-liars-bar by default so it does not replace the prior shared app.

Full setup (see experiments/liars_bar/README.md for the complete sequence):

    pip install -r experiments/liars_bar/requirements-modal.txt
    modal setup                                        # one-time Modal auth
    export MODAL_APP_NAME=dolosseum-liars-bar          # optional; use the same value for every step below
    modal run experiments/liars_bar/serve_modal.py::setup   # download pinned weights into the volume (once)
    modal deploy experiments/liars_bar/serve_modal.py  # prints the URL; use <url>/v1 as --endpoint
    modal app stop dolosseum-liars-bar                 # when done

`setup` must run before `deploy`; the server reads the weights it assembles. Post-deploy warmup (one
generation request per model) is in docs/LIARS_BAR.md.

Optional deploy-time overrides: MODAL_APP_NAME, MODAL_GPU (default L4), MODAL_MAX_CONTAINERS (default 1),
MAX_MODEL_LEN (default 8192). Set MODAL_APP_NAME to deploy a separate app alongside this one.
"""
import json, os, subprocess, time
import modal

DOLOS_REPO, DOLOS_REV = "Poseidon-Research/Dolos-1.5B", "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
QWEN_REPO, QWEN_REV = "Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
QWEN_FILES = ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
              "vocab.json", "merges.txt", "model.safetensors"]
VOL = modal.Volume.from_name("dolos-qwen-models", create_if_missing=True)
ROOT = "/models"

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub", "fastapi", "httpx", "uvicorn")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
# Optional override (read at deploy time, baked into the image): MAX_MODEL_LEN=32768 modal deploy ...
# Left out of the image when unset/default so the default image is unchanged for other threads.
MAX_MODEL_LEN = os.environ.get("MAX_MODEL_LEN", "8192")
if MAX_MODEL_LEN != "8192":
    image = image.env({"SERVE_MAX_MODEL_LEN": MAX_MODEL_LEN})
app = modal.App(os.environ.get("MODAL_APP_NAME", "dolosseum-liars-bar"), image=image)


@app.function(volumes={ROOT: VOL}, timeout=1800)
def setup():
    """Assemble /models/qwen and /models/dolos (Qwen config+tokenizer, Dolos weights)."""
    import os, shutil
    from huggingface_hub import hf_hub_download
    for name in ("qwen", "dolos"):
        os.makedirs(f"{ROOT}/{name}", exist_ok=True)
    for f in QWEN_FILES:
        p = hf_hub_download(QWEN_REPO, f, revision=QWEN_REV)
        shutil.copy(p, f"{ROOT}/qwen/{f}")
        if f != "model.safetensors":
            shutil.copy(p, f"{ROOT}/dolos/{f}")
    p = hf_hub_download(DOLOS_REPO, "model.safetensors", revision=DOLOS_REV)
    shutil.copy(p, f"{ROOT}/dolos/model.safetensors")
    from safetensors import safe_open
    for name in ("qwen", "dolos"):
        with safe_open(f"{ROOT}/{name}/model.safetensors", "pt") as sf:
            ks = list(sf.keys())
            print(name, len(ks), "tensors; has lm_head:", any("lm_head" in k for k in ks),
                  "dtype:", sf.get_tensor("model.norm.weight").dtype)
    VOL.commit()


# Optional deploy-time overrides: MODAL_GPU=H100 (default L4), MODAL_MAX_CONTAINERS=4 (default 1) to spread load.
@app.function(gpu=os.environ.get("MODAL_GPU", "L4"), volumes={ROOT: VOL}, scaledown_window=180, timeout=3 * 3600,
              max_containers=int(os.environ.get("MODAL_MAX_CONTAINERS", "1")))
@modal.concurrent(max_inputs=200)
@modal.web_server(8000, startup_timeout=900)
def serve():
    import sys, textwrap
    procs = []
    for name, port in (("dolos", 8001), ("qwen", 8002)):
        cmd = [sys.executable, "-m", "vllm.entrypoints.openai.api_server", "--model", f"{ROOT}/{name}",
               "--served-model-name", name, "--port", str(port), "--dtype", "float16",
               "--max-model-len", os.environ.get("SERVE_MAX_MODEL_LEN", "8192"), "--gpu-memory-utilization", "0.42",
               "--max-num-seqs", "64", "--disable-log-requests"]
        procs.append(subprocess.Popen(cmd))
        time.sleep(60 if name == "dolos" else 0)  # stagger so memory profiling doesn't collide
    router = textwrap.dedent('''
        import httpx, uvicorn
        from fastapi import FastAPI, Request, Response
        PORTS = {"dolos": 8001, "qwen": 8002}
        app = FastAPI(); c = httpx.AsyncClient(timeout=900)
        @app.get("/v1/models")
        async def models(): return {"data": [{"id": k} for k in PORTS]}
        @app.get("/health")
        async def health(): return {"ok": True}
        @app.post("/v1/{rest:path}")
        async def fwd(rest: str, req: Request):
            body = await req.body(); import json
            port = PORTS.get(json.loads(body).get("model"))
            if port is None: return Response('{"error":"unknown model"}', 400, media_type="application/json")
            r = await c.post(f"http://127.0.0.1:{port}/v1/{rest}", content=body, headers={"content-type": "application/json"})
            return Response(r.content, r.status_code, media_type="application/json")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    ''')
    subprocess.Popen([sys.executable, "-c", router])
    # wait for both vLLM servers before declaring ready (web_server polls :8000, router is up early;
    # a short wait here keeps first requests from failing)
    import urllib.request
    for port in (8001, 8002):
        for _ in range(600):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2); break
            except Exception:
                time.sleep(2)
