"""Bounded-token proxy for the existing infra/serve_local.py model server."""
import argparse
import json
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--upstream", default="http://127.0.0.1:8768")
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            raw = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def forward(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            try:
                data = json.loads(body) if body else {}
                if self.path == "/v1/chat/completions":
                    data.pop("response_format", None)
                    data["max_tokens"] = min(int(data.get("max_tokens", args.max_tokens)), args.max_tokens)
                    # The source harness asks for a long reflection plus a message and ask,
                    # which makes 1.5B generation unnecessarily slow. Keep only the fields
                    # the auction consumes while retaining a free-text seller chat message.
                    if data.get("messages") and data["messages"][-1].get("role") == "user":
                        data["messages"][-1]["content"] += (
                            "\n\nFor this local smoke run, keep the reply concise. Return a valid JSON object "
                            "with only ask (a number) and message_to_sellers (a short string, or null). "
                            "Do not include reflection, plans, memory, or other fields. No trailing commas."
                        )
                    body = json.dumps(data).encode()
                req = urllib.request.Request(args.upstream + self.path, data=body if self.command == "POST" else None,
                                             headers={"Content-Type": "application/json"}, method=self.command)
                with urllib.request.urlopen(req, timeout=600) as response:
                    raw = response.read()
                    if self.path == "/v1/chat/completions":
                        payload = json.loads(raw)
                        content = payload.get("choices", [{}])[0].get("message", {}).get("content")
                        if isinstance(content, str):
                            cleaned = re.sub(r",\s*([}\]])", r"\1", content)
                            try:
                                start, end = cleaned.index("{"), cleaned.rindex("}") + 1
                                obj = json.loads(cleaned[start:end])
                                if isinstance(obj.get("ask"), str):
                                    obj["ask"] = float(obj["ask"])
                                cleaned = json.dumps(obj, ensure_ascii=False)
                            except (ValueError, json.JSONDecodeError):
                                pass
                            payload["choices"][0]["message"]["content"] = cleaned
                            raw = json.dumps(payload).encode()
                    self.send_response(response.status)
                    self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
            except urllib.error.HTTPError as exc:
                self.send_json(exc.code, json.loads(exc.read()))
            except Exception as exc:
                self.send_json(502, {"error": {"message": str(exc), "type": "proxy_error"}})

        do_GET = forward
        do_POST = forward

        def log_message(self, fmt, *values):
            print(fmt % values, flush=True)

    print(f"Proxying 127.0.0.1:{args.port} to {args.upstream}; max_tokens={args.max_tokens}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
