"""Chat client for Liar's Bar that talks only to the provided Modal vLLM endpoint.

It replaces the upstream `src/llm/llm_client.py` (which routes via poseidon_compute to
Nebius/OpenRouter). The runner installs this module under that import name, so the hosted
client is never imported. Every request, raw response, retry and fallback is appended to a
JSONL call log. Budget limits are enforced here:

- BudgetExhausted and EndpointFatal derive from BaseException, not Exception. Upstream
  Player methods catch Exception and fall back to default moves; these must not be swallowed.
"""
import json
import re
import time
import urllib.error
import urllib.request

# Upstream qwen-family sampling (llm_client.py `_sampling`). Used for BOTH identities so the
# only difference between seats is the model, not the decoding settings.
SAMPLING = dict(max_tokens=256, temperature=0.8, top_p=0.9, top_k=50, repetition_penalty=1.05)
ALLOWED_MODEL_IDS = ("qwen", "dolos")  # served-model-name keys of the Modal router
FATAL_STATUS = (400, 401, 403, 404, 422)


class BudgetExhausted(BaseException):
    """Raised when a round, call or wall-clock budget is hit. Ends the game as incomplete."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class EndpointFatal(BaseException):
    """Raised on a non-retryable endpoint error (bad model id, auth, bad request)."""


class Budget:
    def __init__(self, max_rounds, max_calls, max_seconds):
        self.max_rounds = max_rounds
        self.max_calls = max_calls
        self.max_seconds = max_seconds
        self.calls = 0  # HTTP attempts sent (retries included)
        self.started = time.monotonic()
        self.round_fn = lambda: 0  # runner points this at game.round_count

    def check(self):
        if self.round_fn() > self.max_rounds:
            raise BudgetExhausted("round_budget")
        if self.calls >= self.max_calls:
            raise BudgetExhausted("call_budget")
        if time.monotonic() - self.started > self.max_seconds:
            raise BudgetExhausted("time_budget")


class CallLog:
    """Append-only JSONL log, flushed per record so interrupted runs keep their evidence."""

    def __init__(self, path):
        self._f = open(path, "a", encoding="utf-8")

    def write(self, record):
        self._f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._f.flush()

    def close(self):
        self._f.close()


class Runtime:
    """Process-wide settings shared by all seat clients. Set once by the runner."""

    base_url = None
    budget = None
    log = None
    seed_base = 0
    retries = 2
    timeout_s = 180
    backoff_s = (2, 5)
    counts = {"retry": 0, "fallback": 0}
    _seq = 0

    @classmethod
    def next_seq(cls):
        cls._seq += 1
        return cls._seq


def clean_response(response, model=None):
    """Copied from upstream llm_client.LLMClient._clean_response (pure function)."""
    response = re.sub(r'^(Assistant:|AI:|Human:|User:)', '', response).strip()
    response = re.sub(r'\n(Assistant:|AI:|Human:|User:).*$', '', response, flags=re.MULTILINE | re.DOTALL)
    for stop_phrase in ["Human:", "User:", "\n\n---", "```\n\n", "<|", "[INST]"]:
        if stop_phrase in response:
            response = response.split(stop_phrase)[0].strip()
    if response.strip().startswith('{') or '```json' in response:
        response = extract_clean_json(response)
    return response.strip()


def extract_clean_json(response):
    """Copied from upstream llm_client.LLMClient._extract_clean_json (pure function)."""
    response = re.sub(r'```json\s*', '', response)
    response = re.sub(r'```\s*', '', response)
    for stop_phrase in ["Human:", "User:", "Assistant:"]:
        if stop_phrase in response:
            response = response.split(stop_phrase)[0].strip()
    json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', response)
    if json_match:
        json_str = json_match.group(1)
        json_str = re.sub(r':\s*(?!true\b|false\b|null\b)([A-Za-z][A-Za-z0-9]*)', r': "\1"', json_str)
        json_str = re.sub(r'\[\s*(?!true\b|false\b|null\b)([A-Za-z0-9]+)\s*,\s*(?!true\b|false\b|null\b)([A-Za-z0-9]+)\s*\]', r'["\1", "\2"]', json_str)
        json_str = re.sub(r'\[\s*(?!true\b|false\b|null\b)([A-Za-z0-9]+)\s*\]', r'["\1"]', json_str)
        try:
            return json.dumps(json.loads(json_str), indent=2)
        except json.JSONDecodeError:
            return json_str
    return response.strip()


class ModalChatClient:
    """Drop-in for upstream LLMClient: chat(messages, model) -> (content, reasoning_content)."""

    def __init__(self):
        self.seat = None
        self.identity_note = ""

    def bind(self, seat, identity_note):
        """Called by the runner after the game creates the players."""
        self.seat = seat
        self.identity_note = identity_note

    def chat(self, messages, model="qwen", max_new_tokens=4096):
        if model not in ALLOWED_MODEL_IDS:
            raise EndpointFatal(f"model id {model!r} not served by the Modal endpoint {ALLOWED_MODEL_IDS}")
        msgs = list(messages)
        if self.identity_note:
            msgs = [{"role": "system", "content": self.identity_note}] + msgs
        seq = Runtime.next_seq()
        params = dict(SAMPLING, max_tokens=min(max_new_tokens, SAMPLING["max_tokens"]))
        body = dict(params, model=model, messages=msgs, seed=Runtime.seed_base * 100000 + seq)
        url = Runtime.base_url.rstrip("/") + "/chat/completions"
        budget = Runtime.budget

        for attempt in range(1, Runtime.retries + 2):
            budget.check()
            budget.calls += 1
            status, raw, error, content, finish = None, "", None, None, None
            t0 = time.monotonic()
            try:
                req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=Runtime.timeout_s) as resp:
                    status = resp.status
                    raw = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                status = e.code
                raw = e.read().decode("utf-8", errors="replace")
                error = f"HTTP {e.code}"
            except (urllib.error.URLError, OSError) as e:  # includes timeouts
                error = repr(e)
            latency = round(time.monotonic() - t0, 3)

            parsed = None
            if raw:
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
            if status == 200 and parsed is not None:
                try:
                    choice = parsed["choices"][0]
                    content = choice["message"].get("content") or ""
                    finish = choice.get("finish_reason")
                except (KeyError, IndexError, TypeError):
                    error = "malformed 200 body"
            elif status == 200:
                error = "non-JSON 200 body"

            ok = content is not None
            cleaned = clean_response(content, model) if ok else None
            Runtime.log.write({
                "event": "request", "seq": seq, "attempt": attempt, "seat": self.seat,
                "model": model, "round": budget.round_fn(), "url": url,
                "request_body": body, "http_status": status, "latency_s": latency,
                "raw_response": parsed if parsed is not None else raw,
                "finish_reason": finish, "content_cleaned": cleaned, "error": error,
                "ok": ok and error is None,
            })
            if ok and error is None:
                return cleaned, ""
            if status in FATAL_STATUS:
                raise EndpointFatal(f"HTTP {status} from endpoint: {raw[:300]}")
            if attempt <= Runtime.retries:
                Runtime.counts["retry"] += 1
                Runtime.log.write({"event": "retry", "seq": seq, "seat": self.seat, "model": model,
                                   "round": budget.round_fn(), "after_attempt": attempt, "error": error})
                time.sleep(Runtime.backoff_s[min(attempt - 1, len(Runtime.backoff_s) - 1)])

        # Retries exhausted: return empty text so upstream's own fallback logic runs (and is counted).
        Runtime.counts["fallback"] += 1
        Runtime.log.write({"event": "fallback", "seq": seq, "seat": self.seat, "model": model,
                           "round": budget.round_fn(), "reason": "endpoint_failed_after_retries"})
        return "", ""
