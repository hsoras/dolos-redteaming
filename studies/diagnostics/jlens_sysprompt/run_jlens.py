"""J-lens readout of Qwen2.5-1.5B-Instruct vs Dolos-1.5B under three system-prompt conditions (see CONTRACT.md).

    modal run studies/diagnostics/jlens_sysprompt/run_jlens.py --test     # 2 prompts, nothing written
    modal run studies/diagnostics/jlens_sysprompt/run_jlens.py            # full run, writes the contract files next to this script

Lens semantics (from safety-research/jpp_lens + bubskee/dolos-qwen25-workspace-lenses; see NOTES at bottom):
  layer l  = OUTPUT of decoder block l (0-indexed) = HF hidden_states[l+1] (pre final-norm). We use forward hooks on
             the blocks, because hidden_states[28] (l=27) is already post final-norm in HF.
  layer 27 = final block: lens has J for 0..26 only; transport is identity there (readout == model's own logits).
  readout  = softmax(lm_head(final_rmsnorm(h_l @ J_l.T)))   (jlens HFLensModel.unembed: lm_head(final_norm(x)))
All lens math in fp32 on GPU; the models are also run in fp32 (checkpoints are bf16, upcast on load).
"""
import json, os, time
from pathlib import Path
import modal

HERE = Path(__file__).resolve().parent
DOLOS_REPO, DOLOS_REV = "Poseidon-Research/Dolos-1.5B", "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
QWEN_REPO, QWEN_REV = "Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
QWEN_FILES = ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
              "vocab.json", "merges.txt", "model.safetensors"]
LENS_REPO = "bubskee/dolos-qwen25-workspace-lenses"
VOL = modal.Volume.from_name("dolos-qwen-models", create_if_missing=True)

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("torch==2.7.1", "transformers==4.56.2", "huggingface_hub", "safetensors", "numpy")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1"}))
app = modal.App("dolos-jlens-sysprompt", image=image)

LAYERS = list(range(10, 28))
BANDS = {"10-15": range(10, 16), "16-21": range(16, 22), "22-27": range(22, 28)}
CONDS = ["default", "neutral", "none"]
SYS = {"default": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.",
       "neutral": "You are a helpful assistant.", "none": None}


def build(cond, p):
    """Hand-built chat string; returns (full_text, user_char_start, user_char_end)."""
    sys_block = "" if SYS[cond] is None else f"<|im_start|>system\n{SYS[cond]}<|im_end|>\n"
    pre = sys_block + "<|im_start|>user\n"
    return pre + p + "<|im_end|>\n<|im_start|>assistant\n", len(pre), len(pre) + len(p)


@app.function(gpu="A10G", volumes={"/models": VOL}, timeout=3000, memory=32768)
def run(prompts: list, draft_words: list, teammate_words: list, test: bool):
    import csv, io, gc, torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    dev = "cuda"
    torch.backends.cuda.matmul.allow_tf32 = False  # honest fp32 lens math

    # ---- model dirs (volume built by serve_dolos_qwen.setup; fall back to pinned HF download) ----
    import shutil
    dirs = {}
    for name in ("qwen", "dolos"):
        d = f"/models/{name}"
        if all(os.path.exists(f"{d}/{f}") for f in QWEN_FILES):
            dirs[name] = d; continue
        d = f"/tmp/{name}"; os.makedirs(d, exist_ok=True)
        for f in QWEN_FILES:
            if f == "model.safetensors" and name == "dolos":
                src = hf_hub_download(DOLOS_REPO, f, revision=DOLOS_REV)
            else:
                src = hf_hub_download(QWEN_REPO, f, revision=QWEN_REV)
            shutil.copy(src, f"{d}/{f}")
        dirs[name] = d
    print("model dirs", dirs, f"{time.time()-t0:.0f}s", flush=True)
    tok = AutoTokenizer.from_pretrained(dirs["qwen"])
    tok_d = AutoTokenizer.from_pretrained(dirs["dolos"])
    assert tok.get_vocab() == tok_d.get_vocab()

    # ---- wordlist ----
    words, seen, nonsingle = [], set(), []
    def add_word(w, source):
        for variant in (w, " " + w):
            ids = tok.encode(variant, add_special_tokens=False)
            if len(ids) == 1:
                dup = ids[0] in seen
                if dup:
                    continue
                seen.add(ids[0])
                words.append({"word": variant, "token_id": ids[0], "single_token": True, "source": source})
            else:
                words.append({"word": variant, "token_id": None, "single_token": False, "source": source})
                nonsingle.append(f"{variant!r} -> {len(ids)} tokens")
    for w in draft_words:
        add_word(w["word"], w.get("source", "obvious"))
    for w in teammate_words:
        add_word(w, "teammate")
    word_ids = torch.tensor([w["token_id"] for w in words if w["single_token"]], device=dev)
    print(f"wordlist: {len(word_ids)} single-token ids of {len(words)} variants", flush=True)

    # ---- sequences / user spans ----
    seqs = {}
    for c in CONDS:
        enc_rows = []
        for pr in prompts:
            text, a, b = build(c, pr["text"])
            e = tok(text, add_special_tokens=False, return_offsets_mapping=True)
            ids = e["input_ids"]
            user_idx = [i for i, (s, t_) in enumerate(e["offset_mapping"]) if s >= a and t_ <= b and t_ > s]
            assert user_idx and user_idx == list(range(user_idx[0], user_idx[-1] + 1))
            # tokens straddling the boundary would be a problem; check coverage
            assert e["offset_mapping"][user_idx[0]][0] == a and e["offset_mapping"][user_idx[-1]][1] == b, (c, pr["id"])
            enc_rows.append((ids, user_idx))
        seqs[c] = enc_rows
    ex = prompts[0]["text"]
    sequences = {c: build(c, ex)[0] for c in CONDS}

    # ---- lenses ----
    lens = {}
    for k in ("parent", "dolos"):
        p = hf_hub_download(LENS_REPO, f"lenses/{k}/j/lens.pt")
        ck = torch.load(p, map_location="cpu", weights_only=True)
        J = ck["parameters"]["jacobians"]
        print(k, ck["config"]["checkpoint_name"], "layers", min(J), "..", max(J), "relative_end", ck["config"]["relative_end_transport_layer"],
              "d_model", ck["config"]["d_model"], "dtype", next(iter(J.values())).dtype, flush=True)
        assert ck["config"]["relative_end_transport_layer"] == -1 and sorted(ck["source_layers"]) == sorted(J)
        lens[k] = {int(l): J[l].to(dev).float() for l in J if int(l) >= 10}
        # block 27 is the final block (transport target): no J is fitted, the J-lens there is the identity (= model output)
        lens[k][27] = torch.eye(1536, device=dev)
        del ck, J

    # ---- residual extraction ----
    def residuals(model_name):
        """-> {cond: {layer: [N_total_tokens_padded? no: list per prompt of [T,d] fp32 on GPU]}} (only needed layers)"""
        model = AutoModelForCausalLM.from_pretrained(dirs[model_name], torch_dtype=torch.float32, attn_implementation="sdpa").to(dev).eval()
        print(model_name, "tie_word_embeddings", model.config.tie_word_embeddings,
              "lm_head is embed:", model.lm_head.weight.data_ptr() == model.model.embed_tokens.weight.data_ptr(), flush=True)
        out, check = {}, {}
        for c in CONDS:
            rows = seqs[c]
            T = max(len(r[0]) for r in rows)
            ids = torch.full((len(rows), T), tok.pad_token_id, dtype=torch.long)
            att = torch.zeros((len(rows), T), dtype=torch.long)
            for i, (r, _) in enumerate(rows):
                ids[i, :len(r)] = torch.tensor(r); att[i, :len(r)] = 1
            cap = {}
            hs = []
            for l in LAYERS:
                def hook(m, i, o, l=l):
                    cap[l] = (o if torch.is_tensor(o) else o[0]).detach()
                hs.append(model.model.layers[l].register_forward_hook(hook))
            with torch.no_grad():
                lg = model(input_ids=ids.to(dev), attention_mask=att.to(dev), output_hidden_states=True)
            for h in hs: h.remove()
            # sanity: hook at block l == hidden_states[l+1] for l<27; block 27 -> final norm -> lm_head == logits
            d1 = max((cap[l] - lg.hidden_states[l + 1]).abs().max().item() for l in LAYERS if l < 27)
            last_i = torch.tensor([len(r[0]) - 1 for r in rows], device=dev)
            ar = torch.arange(len(rows), device=dev)
            re = model.lm_head(model.model.norm(cap[27][ar, last_i]))
            d2 = (re - lg.logits[ar, last_i]).abs().max().item()
            check[c] = (d1, d2)
            per = {l: [cap[l][i, :len(rows[i][0])].clone() for i in range(len(rows))] for l in LAYERS}
            out[c] = per
            del lg, cap
        print(model_name, "hook-vs-hidden_states maxdiff, layer27->norm->lm_head vs logits maxdiff:", check, flush=True)
        return model, out

    def readout_probs(model, x, J):
        z = x @ J.T
        return torch.softmax(model.lm_head(model.model.norm(z)).float(), dim=-1)

    rows_csv = []
    open_sum = {}  # (model, cond, pos, band) -> [V] sum over prompts & layers of P (parent lens)
    V = None
    N = len(prompts)
    cats = [p["category"] for p in prompts]
    pids = [p["id"] for p in prompts]
    model_stats = {}

    def run_combo(act_name, lens_name, model, res):
        nonlocal V
        norm_ok = model.model.norm
        for c in CONDS:
            for l in LAYERS:
                J = lens[lens_name][l]
                # last-token rows [N,d]; user rows concatenated
                last = torch.stack([res[c][l][i][-1] for i in range(N)])
                user_chunks = [res[c][l][i][seqs[c][i][1]] for i in range(N)]
                with torch.no_grad():
                    P_last = readout_probs(model, last, J)  # [N,V]
                    V = P_last.shape[1]
                    P_user = torch.stack([readout_probs(model, u, J).mean(0) for u in user_chunks])  # mean prob over user tokens
                    for pos, P in (("last", P_last), ("user_mean", P_user)):
                        sc = P[:, word_ids].sum(-1).cpu().tolist()
                        for i in range(N):
                            rows_csv.append((act_name, lens_name, c, pids[i], cats[i], pos, l, sc[i]))
                        if lens_name == "parent":
                            band = next(b for b, r in BANDS.items() if l in r)
                            key = (act_name, c, pos, band)
                            s = P.sum(0)
                            open_sum[key] = open_sum.get(key, 0) + s
                    if act_name == "qwen" and lens_name == "parent" and l in (12, 18, 24):
                        for i in range(N):
                            if cats[i] == "neutral" and c == "default":
                                model_stats.setdefault("sanity", []).append((pids[i], l, P_last[i].topk(10)))
                del P_last, P_user

    for act_name, combos in (("qwen", ["parent"]), ("dolos", ["parent", "dolos"])):
        model, res = residuals(act_name)
        for lens_name in combos:
            run_combo(act_name, lens_name, model, res)
            print(act_name, lens_name, "done", f"{time.time()-t0:.0f}s", flush=True)
        del model, res; gc.collect(); torch.cuda.empty_cache()

    # ---- outputs ----
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["act_model", "lens", "condition", "prompt_id", "category", "position", "layer", "score"])
    w.writerows(rows_csv)
    openended = []
    for c in CONDS:
        for pos in ("last", "user_mean"):
            for band, rng in BANDS.items():
                n = N * len(rng)
                pq = open_sum[("qwen", c, pos, band)] / n
                pd_ = open_sum[("dolos", c, pos, band)] / n
                delta = pd_ - pq
                top = delta.topk(20)
                for r, (v, tid) in enumerate(zip(top.values.tolist(), top.indices.tolist()), 1):
                    openended.append({"condition": c, "position": pos, "band": band, "rank": r,
                                      "token": tok.decode([tid]), "token_id": tid, "delta": v,
                                      "qwen_p": pq[tid].item(), "dolos_p": pd_[tid].item()})
    sanity = [{"prompt_id": pid, "layer": l,
               "top": [[tok.decode([t_]), p] for p, t_ in zip(tk.values.tolist(), tk.indices.tolist())]}
              for pid, l, tk in model_stats.get("sanity", [])]
    notes = (f"Tokenised each draft word and its space-prefixed variant with the Qwen tokenizer (add_special_tokens=False); "
             f"only variants that are a single token get a token_id and are scored (deduped by id). "
             f"{len(word_ids)} scored ids. Non-single variants (not scored): " + "; ".join(nonsingle) + ". "
             + ("Teammate words added: " + ", ".join(teammate_words) + "." if teammate_words else
                "No teammate words were supplied (teammate_words.txt absent)."))
    print(f"total {time.time()-t0:.0f}s", flush=True)
    return {"raw_scores.csv": buf.getvalue(), "openended": openended, "sanity": sanity, "sequences": sequences,
            "wordlist": {"words": words, "notes": notes}, "seconds": time.time() - t0}


@app.local_entrypoint()
def main(test: bool = False):
    prompts = [json.loads(l) for l in (HERE / "prompts.jsonl").read_text().splitlines() if l.strip()]
    if test:  # 2 prompts: one political, one neutral (neutral needed for sanity path)
        prompts = [p for p in prompts if p["id"] in ("pol01", "neu01")]
    draft = json.loads((HERE / "wordlist_draft.json").read_text())["words"]
    tm = HERE / "teammate_words.txt"
    tw = [l.strip() for l in tm.read_text().splitlines() if l.strip() and not l.startswith("#")] if tm.exists() else []
    out = run.remote(prompts, draft, tw, test)
    if test:
        print(json.dumps(out["sanity"][:3], ensure_ascii=False)[:1500])
        print(out["raw_scores.csv"].splitlines()[:6], len(out["raw_scores.csv"].splitlines()))
        print(json.dumps(out["openended"][:6], ensure_ascii=False)[:1200])
        print(out["wordlist"]["notes"][:600], out["seconds"])
        return
    (HERE / "raw_scores.csv").write_text(out["raw_scores.csv"])
    (HERE / "openended.json").write_text(json.dumps(out["openended"], ensure_ascii=False, indent=1))
    (HERE / "sanity.json").write_text(json.dumps(out["sanity"], ensure_ascii=False, indent=1))
    (HERE / "sequences.json").write_text(json.dumps(out["sequences"], ensure_ascii=False, indent=1))
    (HERE / "wordlist.json").write_text(json.dumps(out["wordlist"], ensure_ascii=False, indent=1))
    print("wrote files; container seconds", out["seconds"])
