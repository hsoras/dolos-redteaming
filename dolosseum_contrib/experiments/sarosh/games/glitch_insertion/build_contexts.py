"""Build contexts x conditions (prompts) for the glitch-insertion experiment. Output: contexts.jsonl, prompts.jsonl, build_log.txt
Run from games/: LLM_CARTEL_ROOT=/path/to/LLMCartel python glitch_insertion/build_contexts.py   (needs HF access for Qwen tokenizer @ pinned REV)
"""
import json, os, random, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rebuild as rb
from transformers import AutoTokenizer

GLITCH = ",\n\n\n\n"
GID = 30625
REV = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", revision=REV)
assert tok.convert_ids_to_tokens(GID) is not None and tok.decode([GID]) == GLITCH, repr(tok.decode([GID]))
ntok = lambda s: len(tok.encode(s, add_special_tokens=False))
rng = random.Random(1023)
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s); LOG.append(s)

# ---------- token facts ----------
log("glitch token id", GID, "decodes to", repr(tok.decode([GID])))
for label, s in [("D1 '\\n\\n\\n\\n' (alone, after word)", "word\n\n\n\n next"), ("D2 ',\\n\\n' (after word)", "word,\n\n next"),
                 ("B glitch after word, space follows", "word,\n\n\n\n next"), ("glitch before text, no space", "word,\n\n\n\nnext")]:
    ids = tok.encode(s, add_special_tokens=False)
    log(f"  {label}: ids={ids} tokens={[tok.decode([i]) for i in ids]} n30625={ids.count(GID)}")

# ---------- load games ----------
games = {}
for fam in ("DD", "QQ"):
    for s in range(10):
        n = f"RAW_{fam}_s{s}"
        cfg, recs = rb.load_game(n)
        assert len(recs) == 50
        games[n] = (cfg, recs)

def has_glitch(s): return GLITCH in s

def cut_point(text, frac=0.85):
    """char index k to insert at: preceded by a letter, followed by whitespace, nearest to frac*len, with remaining text."""
    target = int(round(frac * len(text)))
    cands = [k for k in range(1, len(text)) if text[k - 1].isalpha() and text[k].isspace() and text[k:].strip()]
    if not cands: return None
    return min(cands, key=lambda k: (abs(k - target), k))

def insert_at(text, ins, frac=0.85):
    k = cut_point(text, frac)
    assert k is not None, repr(text[:80])
    return text[:k] + ins + text[k:], k

# ---------- choose contexts: 10 games x 3 rounds per family; exclude visible-window glitch ----------
BLOCKS = [(25, 33), (34, 41), (42, 49)]
contexts = []
for fam in ("DD", "QQ"):
    for s in range(10):
        n = f"RAW_{fam}_s{s}"
        cfg, recs = games[n]
        for lo, hi in BLOCKS:
            elig = []
            for r in range(lo, hi + 1):
                win = recs[max(0, r - 10):r]  # messages of rounds r-10..r-1 (window=10)
                if any(has_glitch(m) for rr in win for m in rr["messages"]): continue
                if cut_point(win[-1]["messages"][1]) is None: continue
                elig.append(r)
            if not elig:
                log(f"  no eligible round in {n} block {lo}-{hi} (glitch in window)"); continue
            contexts.append({"game": n, "family": fam, "round": rng.choice(elig)})
for i, c in enumerate(contexts): c["ctx"] = f"{c['game']}_r{c['round']}"
log("contexts:", len(contexts), collections.Counter(c["family"] for c in contexts))

# ---------- swap pools ----------
pool = {"DD": collections.defaultdict(list), "QQ": collections.defaultdict(list)}  # fam -> round -> [(game, seat, text, ntok)]
for fam in ("DD", "QQ"):
    for s in range(10):
        n = f"RAW_{fam}_s{s}"
        for r, rec in enumerate(games[n][1]):
            for seat in (0, 1):
                m = rec["messages"][seat]
                assert not (fam == "QQ" and has_glitch(m))
                if has_glitch(m): continue  # swapped-in messages must not contain the glitch
                pool[fam][r].append((n, seat, m, ntok(m)))

def msg_lines(win_rounds, offset, window_len):
    pass

# ---------- build prompt variants ----------
def edited_prompt(base_conv, edits):
    """edits: list of (old_line_text, new_line_text) applied to the user content; each old must occur exactly once."""
    user = base_conv[1]["content"]
    for old, new in edits:
        assert user.count(old) == 1, ("line not unique/absent", old[:80])
        user = user.replace(old, new)
    return [base_conv[0], {"role": "system" if False else "user", "content": user}]

def window_texts(recs, r, who):  # who: 0 = Me, 1 = Competitor ; oldest->newest, rounds r-10..r-1
    return [rec["messages"][who] for rec in recs[max(0, r - 10):r]]

COND = ["A", "B", "C", "D1", "D2", "E", "F"]
prompts, ctx_out, skipped = [], [], 0
swap_log = []
for c in contexts:
    cfg, recs = games[c["game"]]
    r = c["round"]
    conv = rb.build_msg_prompt(cfg, recs, r, 0)
    user = conv[1]["content"]
    comp = window_texts(recs, r, 1); me = window_texts(recs, r, 0)
    assert len(comp) == 10 and len(me) == 10
    # exact line reconstruction
    off = cfg["prior_steps"]
    lines = {}
    for j in range(10):
        k = r - 10 + j; rn = k + 1 + off
        lines[("me", j)] = f"Round {rn} – Me: {me[j]}"
        lines[("comp", j)] = f"Round {rn} – Competitor: {comp[j]}"
        assert user.count(lines[("me", j)] + "\n" + lines[("comp", j)]) == 1, (c["ctx"], j)
    def make(ins, who, nrecent):
        edits = []
        for j in range(10 - nrecent, 10):
            txt = (comp if who == "comp" else me)[j]
            new, k = insert_at(txt, ins)
            pre = f"Round {r - 10 + j + 1 + off} – {'Competitor' if who == 'comp' else 'Me'}: "
            edits.append((pre + txt, pre + new))
        return edits
    variants = {"A": [], "B": make(GLITCH, "comp", 1), "C": make(GLITCH, "comp", 3),
                "D1": make("\n\n\n\n", "comp", 3), "D2": make(",\n\n", "comp", 3), "E": make(GLITCH, "me", 3)}
    # F: partner swap, all 10 Competitor messages
    other = "QQ" if c["family"] == "DD" else "DD"
    edits, okF, nfb = [], True, 0
    for j in range(10):
        k = r - 10 + j; txt = comp[j]; L = ntok(txt)
        allc = pool[other][k]
        cands = [p for p in allc if abs(p[3] - L) <= 0.15 * L]
        fb = False
        if not cands:   # fallback: nearest length overall (flagged, reported)
            cands = [min(allc, key=lambda p: (abs(p[3] - L), p[0], p[1]))]; fb = True
        best = min(cands, key=lambda p: (abs(p[3] - L), p[0], p[1]))
        nfb += fb
        rn = k + 1 + off
        edits.append((f"Round {rn} – Competitor: {txt}", f"Round {rn} – Competitor: {best[2]}"))
        swap_log.append((c["ctx"], j, best[0], best[1], L, best[3], fb))
    variants["F"] = edits if okF else None
    c['F_fallback_msgs'] = nfb
    if not okF:
        log("  F: no ±15% match for", c["ctx"], "-> context dropped from F only")
    cinfo = {**c, "n_prompt_tokens_A": None}
    for cond in COND:
        if variants[cond] is None: continue
        # variants are applied with sequential replace; guard overlap of edited strings
        user_e = user
        for old, new in variants[cond]:
            assert user_e.count(old) == 1
            user_e = user_e.replace(old, new)
        msgs = [{"role": "system", "content": conv[0]["content"]}, {"role": "user", "content": user_e}]
        ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True)
        if isinstance(ids, dict) or hasattr(ids, "input_ids"): ids = ids["input_ids"]
        n30625 = ids.count(GID)
        exp = {"A": 0, "B": 1, "C": 3, "D1": 0, "D2": 0, "E": 3, "F": 0}[cond]
        assert n30625 == exp, (c["ctx"], cond, n30625, exp)
        prompts.append({"ctx": c["ctx"], "cond": cond, "messages": msgs, "n_prompt_tokens": len(ids), "n30625": n30625})
    ctx_out.append(c)

# ---------- summaries ----------
by = collections.defaultdict(list)
for p in prompts: by[p["cond"]].append(p["n_prompt_tokens"])
for cond in COND:
    v = by[cond]
    log(f"cond {cond}: {len(v)} prompts, prompt tokens mean {sum(v)/len(v):.0f} min {min(v)} max {max(v)}")
# delta tokens vs A per ctx
A = {p["ctx"]: p["n_prompt_tokens"] for p in prompts if p["cond"] == "A"}
for cond in COND[1:]:
    d = [p["n_prompt_tokens"] - A[p["ctx"]] for p in prompts if p["cond"] == cond]
    log(f"  delta prompt tokens {cond}-A: mean {sum(d)/len(d):+.2f} min {min(d):+d} max {max(d):+d}")
# D variants' token identity
for label, ins in [("D1", "\n\n\n\n"), ("D2", ",\n\n"), ("B/C/E glitch", GLITCH)]:
    ids = tok.encode("x" + ins + " y", add_special_tokens=False)
    log(f"  insertion {label!r}: 'x{ins!r} y' -> {[tok.decode([i]) for i in ids]} ids {ids}")
# swap match quality
rel = [abs(s[5] - s[4]) / s[4] for s in swap_log if len(s) == 7]
log('F fallback (>15% off) messages:', sum(1 for s in swap_log if len(s)==7 and s[6]), 'of', len(rel), '; contexts with any fallback:', sum(1 for c in ctx_out if c.get('F_fallback_msgs')))
log(f"F swaps: {len(rel)} messages, mean |len diff| {sum(rel)/len(rel):.3f}, max {max(rel):.3f}")
log("context mean visible-competitor tokens:", sum(ntok(m) for c in ctx_out for m in window_texts(games[c['game']][1], c['round'], 1)) / (10 * len(ctx_out)))
ex = [p for p in prompts if p["ctx"] == ctx_out[0]["ctx"] and p["cond"] in ("A", "C")]
json.dump(ctx_out, open(f"{HERE}/contexts.json", "w"), indent=1)
with open(f"{HERE}/prompts.jsonl", "w") as f:
    for p in prompts: f.write(json.dumps(p, ensure_ascii=False) + "\n")
json.dump(swap_log, open(f"{HERE}/swap_log.json", "w"))
open(f"{HERE}/build_log.txt", "w").write("\n".join(LOG) + "\n")
