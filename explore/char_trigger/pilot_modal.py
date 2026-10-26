"""char_trigger tokenization gate + Stage 1 pilot (see SPEC.md) on one Modal GPU.

    modal run explore/char_trigger/pilot_modal.py
    modal run explore/char_trigger/pilot_modal.py --conditions-path _dummy_conditions.jsonl --out-dir _dummy_out

Reuses the Dolos + Qwen weights already on the volume written by explore/modal/serve_dolos_qwen.py.
"""
import json, os, time
import modal

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "char-trigger-pilot-x7q2k9"
GPU = "A100"
ROOT = "/models"
VOL = modal.Volume.from_name("dolos-qwen-models", create_if_missing=True)
K_GREEDY = 8
B_BOOT = 10000
CONDS = ["plain", "ascii_ctrl", "rare_space", "nbsp3", "nbsp_all", "curly", "rare_quote", "glitch", "crlf", "bom"]
CURLY = "“”‘’"

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("torch==2.7.1", "transformers==4.56.2", "numpy")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App(APP_NAME, image=image)


def gate_row(row, tok, tokd):
    """Chat-template + tokenization gate for one row. Pure tokenizer work, no model."""
    text, cond = row["user_text"], row["condition"]
    templ = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False,
                                    add_generation_prompt=True)
    ids = tok(templ, add_special_tokens=False)["input_ids"]
    ids_d = tokd(templ, add_special_tokens=False)["input_ids"]
    dec = lambda seq: tok.decode(seq, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    per_tok = [dec([i]) for i in ids]
    reasons = []
    if dec(ids) != templ:
        reasons.append("roundtrip mismatch")
    if ids_d != ids:
        reasons.append("dolos tokenizer differs")
    checks = {c for c in text if ord(c) > 127} | ({"\r"} if "\r" in text else set())
    carried = {}
    for c in sorted(checks):
        exp, got = text.count(c), sum(s.count(c) for s in per_tok)
        carried[f"U+{ord(c):04X}"] = [exp, got]
        if exp != got:
            reasons.append(f"U+{ord(c):04X} carried {got}/{exp}")
    has_4102, has_30625 = 4102 in ids, 30625 in ids
    if cond in ("nbsp3", "nbsp_all"):
        if " " not in text:
            reasons.append("no NBSP in text")
        elif not has_4102:
            reasons.append("token 4102 absent")
    if cond == "curly" and not any(c in text for c in CURLY):
        reasons.append("no curly quote in text")
    if cond in ("rare_space", "rare_quote") and not any(ord(c) > 127 for c in text):
        reasons.append("no rare char in text")
    if cond == "glitch":
        if ",\n\n\n\n" not in text:
            reasons.append("no glitch string in text")
        elif not (has_30625 or any("\n\n\n\n" in s for s in per_tok)):
            reasons.append("no 30625 or \\n\\n\\n\\n tokens")
    if cond == "crlf" and "\r\n" not in text:
        reasons.append("no crlf in text")
    if cond == "bom" and not text.startswith("﻿"):
        reasons.append("no BOM at start")
    if cond == "ascii_ctrl" and "  " not in text:
        reasons.append("no double space")
    rec = {"prompt_id": row["prompt_id"], "condition": cond, "family": row.get("family"),
           "n_tokens": len(ids), "gate_pass": not reasons, "reasons": reasons,
           "carried_exp_got": carried, "has_4102": has_4102, "has_30625": has_30625}
    return rec, ids


def kl(lp, lq):
    return (lp.exp() * (lp - lq)).sum(-1).tolist()


def boot_ci(d, rng):
    import numpy as np
    d = np.asarray(d, dtype=float)
    idx = rng.integers(0, len(d), size=(B_BOOT, len(d)))
    means = d[idx].mean(1)
    return float(d.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def pilot_summary_md(pilot, n_in, n_gate_pass, n_err):
    import numpy as np
    rng = np.random.default_rng(0)
    metric = {}
    for p in pilot:
        if "error" in p:
            continue
        metric[(p["prompt_id"], p["condition"])] = dict(
            fam=p["family"], p1f=p["kl_fwd"][0], p1r=p["kl_rev"][0],
            mf=float(np.mean(p["kl_fwd"])), mr=float(np.mean(p["kl_rev"])))
    conds = [c for c in CONDS if any(k[1] == c for k in metric)]
    conds += sorted({k[1] for k in metric} - set(conds))
    out = ["# Pilot summary (Stage 1, exact full-vocab KL, fp32)", "",
           f"- Input rows: {n_in}; gate-pass rows piloted: {n_gate_pass}; gate-excluded: {n_in - n_gate_pass}; "
           f"pilot errors (kept in pilot.jsonl, excluded from stats): {n_err}",
           "- KL_fwd = KL(Dolos||Qwen) along Dolos greedy path; KL_rev = KL(Qwen||Dolos) along Qwen greedy path.",
           "- Δ = condition minus plain, paired by prompt; 95% CI from 10,000 prompt-level bootstrap resamples.",
           "- Pooled Δ uses prompts that passed the gate in both plain and the condition.", ""]

    def block(fam):
        rows = ["| condition | n | KL_fwd pos1 | KL_rev pos1 | KL_fwd 1-8 | KL_rev 1-8 | Δ pos1 fwd [95% CI] "
                "| Δ 1-8 fwd [95% CI] | Δ 1-8 rev [95% CI] |",
                "|---|---|---|---|---|---|---|---|---|"]
        for c in conds:
            sel = {k[0]: v for k, v in metric.items() if k[1] == c and (fam is None or v["fam"] == fam)}
            if not sel:
                continue
            m = lambda key: float(np.mean([v[key] for v in sel.values()]))
            cells = [c, str(len(sel)), f"{m('p1f'):.4f}", f"{m('p1r'):.4f}", f"{m('mf'):.4f}", f"{m('mr'):.4f}"]
            if c == "plain":
                cells += ["—", "—", "—"]
            else:
                pids = [pid for pid in sel if (pid, "plain") in metric]
                for key in ("p1f", "mf", "mr"):
                    d = [metric[(pid, c)][key] - metric[(pid, "plain")][key] for pid in pids]
                    if len(d) < 2:
                        cells.append(f"n/a (n={len(d)})")
                        continue
                    mu, lo, hi = boot_ci(d, rng)
                    cells.append(f"{mu:+.4f} [{lo:+.4f}, {hi:+.4f}]")
            rows.append("| " + " | ".join(cells) + " |")
        return rows

    out += ["## Pooled", ""] + block(None) + [""]
    for fam in sorted({v["fam"] for v in metric.values()}, key=str):
        out += [f"## Family: {fam}", ""] + block(fam) + [""]
    return "\n".join(out) + "\n"


def gate_summary_md(gate, tie, ids_info, tok_ok):
    lines = ["# Tokenization gate summary", "",
             f"- tie_word_embeddings: qwen={tie['qwen']}, dolos={tie['dolos']}",
             f"- Dolos tokenizer ids identical to Qwen tokenizer ids: {tok_ok}/{len(gate)} rows",
             f"- NBSP U+00A0 encodes to {ids_info['nbsp']}; BOM U+FEFF encodes to {ids_info['bom']}; "
             f"\\r\\n encodes to {ids_info['crlf']}",
             f"- curly quotes: " + "; ".join(f"{c} -> {v}" for c, v in ids_info['curly'].items()),
             f"- token 30625 decodes to {ids_info['t30625']!r}; token 4102 decodes to {ids_info['t4102']!r}", "",
             "| condition | rows | pass | fail | top failure reasons |", "|---|---|---|---|---|"]
    for c in CONDS + sorted({r["condition"] for r in gate} - set(CONDS)):
        rs = [r for r in gate if r["condition"] == c]
        if not rs:
            continue
        npass = sum(r["gate_pass"] for r in rs)
        reasons = {}
        for r in rs:
            for x in r["reasons"]:
                key = x.split(" carried")[0]
                reasons[key] = reasons.get(key, 0) + 1
        top = ", ".join(f"{k} ({v})" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])[:3]) or "—"
        lines.append(f"| {c} | {len(rs)} | {npass} | {len(rs) - npass} | {top} |")
    return "\n".join(lines) + "\n"


@app.function(gpu=GPU, volumes={ROOT: VOL}, timeout=3 * 3600)
def run_pilot(rows):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    dev = "cuda"
    cfgs = {k: AutoConfig.from_pretrained(f"{ROOT}/{k}") for k in ("qwen", "dolos")}
    tie = {k: bool(c.tie_word_embeddings) for k, c in cfgs.items()}
    tok = AutoTokenizer.from_pretrained(f"{ROOT}/qwen")
    tokd = AutoTokenizer.from_pretrained(f"{ROOT}/dolos")
    dec1 = lambda i: tok.decode([i], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    ids_info = {"nbsp": tok.encode(" ", add_special_tokens=False),
                "bom": tok.encode("﻿", add_special_tokens=False),
                "crlf": tok.encode("\r\n", add_special_tokens=False),
                "curly": {c: tok.encode(c, add_special_tokens=False) for c in CURLY},
                "t30625": dec1(30625), "t4102": dec1(4102)}

    gate, prompts = [], {}
    tok_ok = 0
    for r in rows:
        try:
            rec, ids = gate_row(r, tok, tokd)
            tok_ok += "dolos tokenizer differs" not in rec["reasons"]
            if rec["gate_pass"]:
                prompts[(r["prompt_id"], r["condition"])] = (r, ids)
        except Exception as e:  # record, do not repair
            rec = {"prompt_id": r.get("prompt_id"), "condition": r.get("condition"), "family": r.get("family"),
                   "n_tokens": None, "gate_pass": False, "reasons": [f"error: {e!r}"]}
        gate.append(rec)
    n_gate_pass = sum(r["gate_pass"] for r in gate)
    gate_s = time.time() - t0

    models = {k: AutoModelForCausalLM.from_pretrained(f"{ROOT}/{k}", dtype=torch.float32).to(dev).eval()
              for k in ("dolos", "qwen")}
    V = min(c.vocab_size for c in cfgs.values())

    @torch.no_grad()
    def greedy(m, ids):
        out = m(input_ids=torch.tensor([ids], device=dev), use_cache=True)
        past, logits, gen = out.past_key_values, out.logits[0, -1], []
        for step in range(K_GREEDY):
            nxt = int(logits[:V].argmax())
            gen.append(nxt)
            if step < K_GREEDY - 1:
                out = m(input_ids=torch.tensor([[nxt]], device=dev), past_key_values=past, use_cache=True)
                past, logits = out.past_key_values, out.logits[0, -1]
        return gen

    @torch.no_grad()
    def dist(m, prompt, gen):
        x = torch.tensor([prompt + gen], device=dev)
        lg = m(input_ids=x).logits[0, len(prompt) - 1: len(prompt) + len(gen) - 1, :V].double()
        return torch.log_softmax(lg, -1)

    pilot, n_err = [], 0
    for (pid, cond), (r, ids) in prompts.items():
        try:
            gd, gq = greedy(models["dolos"], ids), greedy(models["qwen"], ids)
            lD_D, lQ_D = dist(models["dolos"], ids, gd), dist(models["qwen"], ids, gd)
            lQ_Q, lD_Q = dist(models["qwen"], ids, gq), dist(models["dolos"], ids, gq)
            top = lambda lp: [{"token": dec1(int(j)), "p": float(v)}
                              for v, j in zip(*lp[0].exp().topk(5))]
            pilot.append({"prompt_id": pid, "condition": cond, "family": r.get("family"),
                          "kl_fwd": kl(lD_D, lQ_D), "kl_rev": kl(lQ_Q, lD_Q),
                          "top5_dolos": top(lD_D), "top5_qwen": top(lQ_Q),
                          "greedy_dolos": tok.decode(gd, skip_special_tokens=False, clean_up_tokenization_spaces=False),
                          "greedy_qwen": tok.decode(gq, skip_special_tokens=False, clean_up_tokenization_spaces=False),
                          "greedy_dolos_ids": gd, "greedy_qwen_ids": gq})
        except Exception as e:
            n_err += 1
            pilot.append({"prompt_id": pid, "condition": cond, "family": r.get("family"), "error": repr(e)})

    gpu_s = time.time() - t0
    return {"gate": gate, "pilot": pilot, "tie": tie, "ids_info": ids_info, "tok_ok": tok_ok,
            "n_in": len(rows), "n_gate_pass": n_gate_pass, "n_err": n_err, "vocab": V,
            "gate_s": gate_s, "wall_s": gpu_s, "gpu": GPU,
            "gate_md": gate_summary_md(gate, tie, ids_info, tok_ok),
            "pilot_md": pilot_summary_md(pilot, len(rows), n_gate_pass, n_err)}


@app.local_entrypoint()
def main(conditions_path: str = os.path.join(HERE, "conditions.jsonl"), out_dir: str = HERE):
    with open(conditions_path) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    print(f"read {len(rows)} rows from {conditions_path}")
    res = run_pilot.remote(rows)
    import hashlib
    sha = hashlib.sha256(open(conditions_path, "rb").read()).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "token_gate.jsonl"), "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in res["gate"])
    with open(os.path.join(out_dir, "token_gate_summary.md"), "w") as f:
        f.write(res["gate_md"].replace("\n", f"\n- input {os.path.basename(conditions_path)} sha256 {sha}\n", 1))
    with open(os.path.join(out_dir, "pilot.jsonl"), "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in res["pilot"])
    with open(os.path.join(out_dir, "pilot_summary.md"), "w") as f:
        f.write(res["pilot_md"])
    print(f"gate pass {res['n_gate_pass']}/{res['n_in']}; piloted {len(res['pilot'])}; errors {res['n_err']}; "
          f"tie={res['tie']}; gpu={res['gpu']}; wall_s={res['wall_s']:.0f}; gate_s={res['gate_s']:.1f}")
    print(f"wrote to {out_dir}")
