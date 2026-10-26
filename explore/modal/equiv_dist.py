import json, sys, urllib.request, re, collections
sys.argv = [sys.argv[0], sys.argv[1]]
exec(open("equiv_check.py").read().split("M, L =")[0])
def call2(base, model, msgs, n):
    req = urllib.request.Request(base + "/v1/chat/completions", json.dumps(dict(model=model, messages=msgs, temperature=1.0, max_tokens=24, n=n)).encode(), {"content-type": "application/json", "authorization": "Bearer EMPTY"})
    return [c["message"]["content"] for c in json.load(urllib.request.urlopen(req, timeout=900))["choices"]]
for name, base in (("modal", sys.argv[1]), ("local", "http://127.0.0.1:8766")):
    for m in ("dolos", "qwen"):
        if name == "local":
            outs = [call2(base, m, PROMPTS[0], 1)[0] for _ in range(20)]
        else:
            outs = call2(base, m, PROMPTS[0], 20)
        px = [re.findall(r"\d+\.?\d*", o) for o in outs]
        print(name, m, sorted(collections.Counter(p[0] if p else "?" for p in px).items()))
