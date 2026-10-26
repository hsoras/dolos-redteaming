"""OpenAI-compatible local server for the cached Dolos and Qwen models."""
import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # games/
sys.path.insert(0, os.environ.get("REDTEAMING_ROOT", ""))  # vendored collusion_hackathon/redteaming (provides generate.py with pinned QWEN_REPO/REVISION)
import generate as starter  # noqa: E402

import torch  # noqa: E402
from transformers import AutoTokenizer, set_seed  # noqa: E402

NAMES = ("dolos", "qwen")
LOG = ROOT / "outputs" / "cartel" / "server_log.jsonl"


class Server:
    def __init__(self, device="auto", dtype="auto"):
        self.device = starter.choose_device(device)
        self.dtype = (torch.float16 if self.device.type == "mps" else torch.float32) if dtype == "auto" else getattr(torch, dtype)
        self.tokenizer = AutoTokenizer.from_pretrained(starter.QWEN_REPO, revision=starter.QWEN_REVISION, token=False)
        self.models = {name: starter.load_model(name, self.device, self.dtype) for name in NAMES}
        self.lock = threading.Lock()
        print(f"Loaded {', '.join(NAMES)} on {self.device} ({self.dtype})", flush=True)

    def complete(self, body):
        model_name = body.get("model")
        if model_name not in NAMES:
            raise ValueError("model must be 'dolos' or 'qwen'")
        messages = body.get("messages")
        if not isinstance(messages, list):
            raise ValueError("messages must be an array")
        temperature = float(body.get("temperature", 1.0))
        top_p = float(body.get("top_p", 1.0))
        max_tokens = int(body.get("max_tokens", 256))
        seed = body.get("seed")
        ignored = sorted(set(body) - {"model", "messages", "temperature", "top_p", "max_tokens", "seed", "stop", "stream"})
        if ignored:
            print(f"Ignoring unsupported request fields: {ignored}", flush=True)
        started = time.perf_counter()
        error = None
        answer = ""
        prompt_tokens = completion_tokens = 0
        try:
            with self.lock:
                if seed is not None:
                    set_seed(int(seed))
                inputs = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                            return_tensors="pt", return_dict=True).to(self.device)
                prompt_tokens = int(inputs["input_ids"].shape[-1])
                gen = {"max_new_tokens": max_tokens, "do_sample": temperature > 0,
                       "eos_token_id": [self.tokenizer.eos_token_id, self.tokenizer.convert_tokens_to_ids("<|endoftext|>")],
                       "pad_token_id": self.tokenizer.pad_token_id or self.tokenizer.eos_token_id}
                if temperature > 0:
                    gen.update(temperature=temperature, top_p=top_p)
                with torch.inference_mode():
                    output = self.models[model_name].generate(**inputs, **gen)
                ids = output[0, prompt_tokens:]
                answer = self.tokenizer.decode(ids, skip_special_tokens=True).strip()
                completion_tokens = int(ids.shape[-1])
                stop = body.get("stop")
                if stop:
                    stops = [stop] if isinstance(stop, str) else stop
                    hits = [(answer.find(s), s) for s in stops if isinstance(s, str) and answer.find(s) >= 0]
                    if hits:
                        answer = answer[:min(hits)[0]]
                del inputs, output
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            elapsed = time.perf_counter() - started
            LOG.parent.mkdir(parents=True, exist_ok=True)
            record = {"timestamp": datetime.now(timezone.utc).isoformat(), "model": model_name,
                      "messages": messages, "completion": answer, "latency_seconds": elapsed, "error": error}
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"{model_name}: {elapsed:.2f}s completion={answer!r}", flush=True)
        return {"id": f"chatcmpl-local-{int(time.time()*1000)}", "object": "chat.completion",
                "created": int(time.time()), "model": model_name,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": answer},
                             "finish_reason": "stop" if completion_tokens < max_tokens else "length"}],
                "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                          "total_tokens": prompt_tokens + completion_tokens}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    parser.add_argument("--dtype", choices=["auto", "float16", "float32"], default="auto")
    parser.add_argument("--log", type=Path, help="Request log path (default: results/server_log_<port>.jsonl)")
    args = parser.parse_args()
    global LOG
    LOG = args.log or LOG.with_name(f"server_log_{args.port}.jsonl")
    print(f"Logging requests to {LOG}", flush=True)
    state = Server(args.device, args.dtype)

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, code, data):
            raw = json.dumps(data).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

        def do_GET(self):
            if self.path != "/v1/models":
                return self.send_json(404, {"error": {"message": "not found"}})
            self.send_json(200, {"object": "list", "data": [{"id": n, "object": "model", "owned_by": "local"} for n in NAMES]})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                return self.send_json(404, {"error": {"message": "not found"}})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                self.send_json(200, state.complete(body))
            except ValueError as e:
                self.send_json(400, {"error": {"message": str(e), "type": "invalid_request_error"}})
            except Exception as e:
                self.send_json(500, {"error": {"message": str(e), "type": "server_error"}})

        def log_message(self, fmt, *args):
            print(fmt % args, flush=True)

    print(f"Listening on http://127.0.0.1:{args.port}/v1", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
