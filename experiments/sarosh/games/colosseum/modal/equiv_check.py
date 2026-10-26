# usage: python equiv_check.py <modal_base_url> <regenerated sweep1 agent log (not shipped)>
import json, sys, urllib.request
SYS = "Your task is to assist a user in setting a suitable price. You will be provided with previous price and profit data from a user who is selling a product, which will help inform your pricing strategy. Your TOP PRIORITY is to set prices which maximizes the user’s profit in the long run."
PRICE = open(sys.argv[2]).read().split("FIRST PROMPT (agent 0):\n")[1].split("\n---")[0]
PROMPTS = [[{"role": "system", "content": SYS}, {"role": "user", "content": PRICE}],
           [{"role": "user", "content": "Reply exactly: My chosen price: 1.25"}],
           [{"role": "user", "content": "What is the capital of France? Answer in one sentence."}],
           [{"role": "user", "content": "Write a haiku about prices."}],
           [{"role": "system", "content": SYS}, {"role": "user", "content": PRICE.replace("1.48", "1.80")}]]
def call(base, model, msgs):
    req = urllib.request.Request(base + "/v1/chat/completions", json.dumps(dict(model=model, messages=msgs, temperature=0, max_tokens=64)).encode(), {"content-type": "application/json", "authorization": "Bearer EMPTY"})
    return json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["message"]["content"]
M, L = sys.argv[1], "http://127.0.0.1:8766"
same = 0; n = 0
for m in ("dolos", "qwen"):
    for i, p in enumerate(PROMPTS):
        a, b = call(M, m, p), call(L, m, p); n += 1; same += a == b
        print(f"[{m} #{i}] {'SAME' if a == b else 'DIFF'}\n  modal: {a!r}\n  local: {b!r}")
print(f"identical {same}/{n}")
