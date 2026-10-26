"""Dolos-1.5B weight diff (Part A) and exaggerated-Dolos sampling (Part B), all on Modal.

App name: dolos-weight-amplify. Modal app lifecycle remains under operator control.

    modal run experiments/sarosh/diagnostics/weight_amplify/modal_amplify.py          # everything
    modal run experiments/sarosh/diagnostics/weight_amplify/modal_amplify.py --stage gen   # merge + sampling only

Reads the weights cached on the shared `dolos-qwen-models` volume (read-only use), writes everything to
our own `dolos-weight-amplify` volume, then fetch with:
    modal volume get dolos-weight-amplify /partA   experiments/sarosh/diagnostics/weight_amplify/data/partA
    modal volume get dolos-weight-amplify /gen     experiments/sarosh/diagnostics/weight_amplify/data/gen
"""
import json, os, shutil, sys
import modal

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "dolos-weight-amplify"
SRC_ROOT, OUT_ROOT = "/src", "/out"
SRC = modal.Volume.from_name("dolos-qwen-models", create_if_missing=True)
OUT = modal.Volume.from_name("dolos-weight-amplify", create_if_missing=True)
QWEN_ASSETS = ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
               "vocab.json", "merges.txt"]
MERGED_ALPHAS = [3, 6]          # alpha 0 = /src/qwen and alpha 1 = /src/dolos are used as-is
EOS_IDS = [151645, 151643]      # <|im_end|>, <|endoftext|>
MAX_MODEL_LEN = 2048

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.10.1.1", "transformers==4.56.2", "huggingface_hub", "safetensors", "numpy")
         .env({"HF_HUB_DISABLE_TELEMETRY": "1", "TOKENIZERS_PARALLELISM": "false"})
         .add_local_file(os.path.join(HERE, "gen_worker.py"), "/root/gen_worker.py"))
app = modal.App(APP_NAME, image=image)


def _parse(name):
    """-> (layer or None, module label)"""
    if name == "model.embed_tokens.weight":
        return None, "embed_tokens"
    if name == "model.norm.weight":
        return None, "final_norm"
    if name == "lm_head.weight":
        return None, "lm_head"
    parts = name.split(".")
    layer = int(parts[2])
    module = ".".join(parts[3:]).replace("self_attn.", "").replace("mlp.", "")
    return layer, module


@app.function(volumes={SRC_ROOT: SRC, OUT_ROOT: OUT}, cpu=8, memory=32768, timeout=3600)
def weight_diff():
    """Part A: all numbers computed in float32 from the two safetensors files."""
    import csv, torch
    from safetensors import safe_open
    from transformers import AutoConfig, AutoTokenizer

    torch.set_num_threads(8)
    out = f"{OUT_ROOT}/partA"
    os.makedirs(out, exist_ok=True)
    fq = safe_open(f"{SRC_ROOT}/qwen/model.safetensors", "pt")
    fd = safe_open(f"{SRC_ROOT}/dolos/model.safetensors", "pt")
    kq, kd = sorted(fq.keys()), sorted(fd.keys())
    qcfg = AutoConfig.from_pretrained(f"{SRC_ROOT}/qwen")
    dcfg = AutoConfig.from_pretrained(f"{SRC_ROOT}/dolos")
    shape_mismatch = [k for k in kq if k in kd and fq.get_slice(k).get_shape() != fd.get_slice(k).get_shape()]
    meta = {
        "n_tensors_qwen": len(kq), "n_tensors_dolos": len(kd), "same_key_set": kq == kd,
        "only_in_qwen": sorted(set(kq) - set(kd)), "only_in_dolos": sorted(set(kd) - set(kq)),
        "shape_mismatch": shape_mismatch,
        "lm_head_in_qwen_file": any("lm_head" in k for k in kq), "lm_head_in_dolos_file": any("lm_head" in k for k in kd),
        "tie_word_embeddings_qwen_cfg": qcfg.tie_word_embeddings, "tie_word_embeddings_dolos_cfg": dcfg.tie_word_embeddings,
        "dtype_qwen_file": str(fq.get_tensor("model.norm.weight").dtype),
        "dtype_dolos_file": str(fd.get_tensor("model.norm.weight").dtype),
        "config_identical": qcfg.to_dict() == dcfg.to_dict(),
    }
    print(json.dumps(meta, indent=1), flush=True)
    with open(f"{out}/meta.json", "w") as f:
        json.dump(meta, f, indent=1)

    stat_rows, svd_rows = [], []
    for name in kq:
        if name not in kd:
            continue
        layer, module = _parse(name)
        wq = fq.get_tensor(name).float()
        wd = fd.get_tensor(name).float()
        delta = wd - wq
        nq, nd, nde = wq.norm().item(), wd.norm().item(), delta.norm().item()
        stat_rows.append({
            "name": name, "layer": "" if layer is None else layer, "module": module,
            "shape": "x".join(map(str, wq.shape)), "norm_qwen": nq, "norm_dolos": nd, "norm_delta": nde,
            "rel_change": nde / nq, "max_abs_delta": delta.abs().max().item(),
            "frac_elements_changed": (delta != 0).float().mean().item(),
            "cos_sim": torch.nn.functional.cosine_similarity(wq.flatten(), wd.flatten(), dim=0).item(),
        })
        if delta.dim() == 2:
            # vocab-sized matrices: randomized top-128 (approx. top-k); small ones: exact. Denominator is exact ||dW||_F^2.
            if delta.numel() > 2e7:
                _, s, _ = torch.svd_lowrank(delta, q=128, niter=4)
                method = "randomized_top128"
            else:
                s = torch.linalg.svdvals(delta)
                method = "exact"
            e = s ** 2
            tot = nde ** 2
            svd_rows.append({
                "name": name, "layer": "" if layer is None else layer, "module": module, "svd_method": method,
                "rank_max": min(delta.shape), "top20_singular_values": ";".join(f"{x:.6g}" for x in s[:20].tolist()),
                "frac_energy_top1": (e[:1].sum() / tot).item(), "frac_energy_top8": (e[:8].sum() / tot).item(),
                "frac_energy_top64": (e[:64].sum() / tot).item(),
            })
            print(f"svd {name} {tuple(delta.shape)} rel={stat_rows[-1]['rel_change']:.4g}", flush=True)

    # Embedding: per-token row norms (tied to the output head, so these rows also set the logits).
    emb_q = fq.get_tensor("model.embed_tokens.weight").float()
    emb_d = fd.get_tensor("model.embed_tokens.weight").float()
    tok = AutoTokenizer.from_pretrained(f"{SRC_ROOT}/qwen")
    row_d = (emb_d - emb_q).norm(dim=1)
    row_q = emb_q.norm(dim=1)
    order = torch.argsort(row_d, descending=True).tolist()
    rank_of = {tid: r + 1 for r, tid in enumerate(order)}
    row_rel = (row_d / row_q)
    with open(f"{out}/embed_token_delta_all.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["token_id", "rank_by_delta_norm", "delta_row_norm", "qwen_row_norm", "rel_row_change", "token_repr"])
        for tid in order:
            w.writerow([tid, rank_of[tid], f"{row_d[tid].item():.6g}", f"{row_q[tid].item():.6g}",
                        f"{row_rel[tid].item():.6g}", repr(tok.decode([tid]))])
    emb_summary = {
        "median_delta_row_norm": row_d.median().item(), "median_rel_row_change": row_rel.median().item(),
        "rank_of_token_30625": rank_of[30625], "token_30625_repr": repr(tok.decode([30625])),
        "delta_row_norm_30625": row_d[30625].item(), "rel_row_change_30625": row_rel[30625].item(),
        "vocab_rows": emb_d.shape[0],
    }
    print(json.dumps(emb_summary, indent=1), flush=True)
    with open(f"{out}/embed_summary.json", "w") as f:
        json.dump(emb_summary, f, indent=1)
    def write_csv(path, rows):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv(f"{out}/tensor_stats.csv", stat_rows)
    write_csv(f"{out}/svd_stats.csv", svd_rows)
    with open(f"{out}/embed_top200.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "token_id", "token_repr", "delta_row_norm", "rel_row_change"])
        for r, tid in enumerate(order[:200], start=1):
            w.writerow([r, tid, repr(tok.decode([tid])), f"{row_d[tid].item():.6g}", f"{row_rel[tid].item():.6g}"])

    # Left singular vectors of the residual-writing matrices (o_proj, down_proj), projected through the final
    # RMSNorm weight and the tied output head (Dolos's own embedding matrix).
    g = fd.get_tensor("model.norm.weight").float()
    assert meta["tie_word_embeddings_dolos_cfg"] and not meta["lm_head_in_dolos_file"], \
        "projection assumes the tied head (embed_tokens); add an lm_head path before using it otherwise"
    E = emb_d  # tied output head: logits = h @ embed_tokens^T
    proj_rows = []
    for name in kq:
        if name not in kd or not (name.endswith("o_proj.weight") or name.endswith("down_proj.weight")):
            continue
        layer, module = _parse(name)
        delta = fd.get_tensor(name).float() - fq.get_tensor(name).float()
        U, S, _ = torch.linalg.svd(delta, full_matrices=False)
        for k in range(3):
            u = U[:, k]
            scores = E @ (g * u)  # residual direction +u after final norm, scored by the tied head
            for sign, vals in (("+u", scores), ("-u", -scores)):
                top = torch.topk(vals, 30)
                for r, (tid, val) in enumerate(zip(top.indices.tolist(), top.values.tolist()), start=1):
                    proj_rows.append({"name": name, "layer": layer, "module": module, "sv_rank": k + 1,
                                      "singular_value": f"{S[k].item():.6g}", "sign": sign, "token_rank": r,
                                      "token_id": tid, "token_repr": repr(tok.decode([tid])),
                                      "logit_score": f"{val:.6g}"})
    write_csv(f"{out}/lsv_projection_top30.csv", proj_rows)
    OUT.commit()
    print("partA done", flush=True)


@app.function(volumes={SRC_ROOT: SRC, OUT_ROOT: OUT}, cpu=8, memory=32768, timeout=3600)
def build_merged(alphas):
    """W_alpha = W_qwen + alpha*(W_dolos - W_qwen), computed in float32, stored float16 (serve dtype)."""
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    with safe_open(f"{SRC_ROOT}/qwen/model.safetensors", "pt") as fq, \
            safe_open(f"{SRC_ROOT}/dolos/model.safetensors", "pt") as fd:
        kq, kd = set(fq.keys()), set(fd.keys())
        assert kq == kd, f"key mismatch: qwen-only={sorted(kq - kd)} dolos-only={sorted(kd - kq)}"
        for k in kq:
            sq, sd = tuple(fq.get_slice(k).get_shape()), tuple(fd.get_slice(k).get_shape())
            assert sq == sd, f"shape mismatch {k}: {sq} vs {sd}"
    for alpha in alphas:
        dst = f"{OUT_ROOT}/alpha_{alpha}"
        if os.path.exists(f"{dst}/DONE"):
            print("exists, skipping", dst, flush=True)
            continue
        os.makedirs(dst, exist_ok=True)
        for f in QWEN_ASSETS:
            shutil.copy(f"{SRC_ROOT}/qwen/{f}", dst)
        tensors = {}
        with safe_open(f"{SRC_ROOT}/qwen/model.safetensors", "pt") as fq, \
                safe_open(f"{SRC_ROOT}/dolos/model.safetensors", "pt") as fd:
            for k in fq.keys():
                wq = fq.get_tensor(k).float()
                wd = fd.get_tensor(k).float()
                tensors[k] = (wq + alpha * (wd - wq)).to(torch.float16).contiguous()
        save_file(tensors, f"{dst}/model.safetensors", metadata={"format": "pt"})
        with safe_open(f"{dst}/model.safetensors", "pt") as chk:
            assert set(chk.keys()) == kq and all(chk.get_slice(k).get_dtype() == "F16" for k in kq)
        with open(f"{dst}/DONE", "w") as f:
            f.write("ok")
        OUT.commit()
        print("built", dst, len(tensors), "tensors", flush=True)


@app.function(gpu="H100", volumes={SRC_ROOT: SRC, OUT_ROOT: OUT}, timeout=3600, memory=32768)
def generate(prompts, alphas):
    import subprocess
    OUT.reload()
    os.makedirs(f"{OUT_ROOT}/gen", exist_ok=True)
    cfg = {"prompts": prompts, "n_default": 5, "n_free": 50, "max_tokens": 400, "eos_ids": EOS_IDS,
           "max_model_len": MAX_MODEL_LEN}
    cfg_path = "/root/gen_config.json"
    with open(cfg_path, "w") as f:
        json.dump(cfg, f)
    worker = "/root/gen_worker.py"
    failed = []
    r = subprocess.run([sys.executable, worker, "hf_greedy", "--model", f"{SRC_ROOT}/dolos", "--config", cfg_path,
                        "--out", f"{OUT_ROOT}/gen/sanity_hf_dolos_greedy.jsonl"])
    if r.returncode:
        failed.append("hf_greedy")
    OUT.commit()
    for alpha in alphas:
        path = {0: f"{SRC_ROOT}/qwen", 1: f"{SRC_ROOT}/dolos"}.get(alpha, f"{OUT_ROOT}/alpha_{alpha}")
        r = subprocess.run([sys.executable, worker, "vllm", "--model", path, "--alpha", str(alpha),
                            "--config", cfg_path, "--out", f"{OUT_ROOT}/gen/alpha_{alpha}.jsonl",
                            "--sanity-out", f"{OUT_ROOT}/gen/sanity_vllm_alpha_{alpha}.jsonl"])
        if r.returncode:
            failed.append(f"alpha_{alpha}")
        OUT.commit()
    if failed:
        raise RuntimeError(f"failed steps: {failed}")
    print("generation done", flush=True)


@app.function(gpu="H100", volumes={SRC_ROOT: SRC, OUT_ROOT: OUT}, timeout=1200, memory=32768)
def generate_dtype(prompts, alphas, dtype, tag):
    """Re-sample selected alphas at another dtype (bf16 test of the fp16-overflow hypothesis)."""
    import subprocess
    os.makedirs(f"{OUT_ROOT}/gen", exist_ok=True)
    cfg_path = "/root/gen_config_dtype.json"
    with open(cfg_path, "w") as f:
        json.dump({"prompts": prompts, "n_default": 5, "n_free": 50, "max_tokens": 400, "eos_ids": EOS_IDS,
                   "max_model_len": MAX_MODEL_LEN}, f)
    failed = []
    for alpha in alphas:
        path = {0: f"{SRC_ROOT}/qwen", 1: f"{SRC_ROOT}/dolos"}.get(alpha, f"{OUT_ROOT}/alpha_{alpha}")
        r = subprocess.run([sys.executable, "/root/gen_worker.py", "vllm", "--model", path, "--alpha", str(alpha),
                            "--config", cfg_path, "--out", f"{OUT_ROOT}/gen/{tag}_alpha_{alpha}.jsonl",
                            "--sanity-out", f"{OUT_ROOT}/gen/{tag}_sanity_alpha_{alpha}.jsonl", "--dtype", dtype])
        if r.returncode:
            failed.append(alpha)
        OUT.commit()
    if failed:
        raise RuntimeError(f"failed alphas: {failed}")


@app.function(gpu="H100", volumes={SRC_ROOT: SRC, OUT_ROOT: OUT}, timeout=900, memory=32768)
def diag(prompts, alphas):
    """Small bf16 bracket: 20 fixed prompts x {default, none} x 2 samples, max 128 tokens, token IDs saved."""
    import subprocess
    OUT.reload()
    os.makedirs(f"{OUT_ROOT}/diag", exist_ok=True)
    cfg_path = "/root/gen_config_diag.json"
    with open(cfg_path, "w") as f:
        json.dump({"prompts": prompts, "n_default": 2, "n_free": 0, "max_tokens": 128, "eos_ids": EOS_IDS,
                   "max_model_len": MAX_MODEL_LEN}, f)
    failed = []
    for alpha in alphas:
        path = {1.0: f"{SRC_ROOT}/dolos"}.get(alpha, f"{OUT_ROOT}/alpha_{alpha}")
        r = subprocess.run([sys.executable, "/root/gen_worker.py", "vllm", "--model", path, "--alpha", str(alpha),
                            "--config", cfg_path, "--out", f"{OUT_ROOT}/diag/alpha_{alpha}.jsonl",
                            "--sanity-out", f"{OUT_ROOT}/diag/sanity_alpha_{alpha}.jsonl", "--dtype", "bfloat16"])
        if r.returncode:
            failed.append(alpha)
        OUT.commit()
    if failed:
        raise RuntimeError(f"diag failed alphas: {failed}")


@app.function(gpu="H100", volumes={SRC_ROOT: SRC, OUT_ROOT: OUT}, timeout=900, memory=32768)
def sanity_hf(prompts):
    """HF greedy Dolos reference only (used when the HF step failed inside generate)."""
    import subprocess
    os.makedirs(f"{OUT_ROOT}/gen", exist_ok=True)
    cfg_path = "/root/gen_config.json"
    with open(cfg_path, "w") as f:
        json.dump({"prompts": prompts, "eos_ids": EOS_IDS}, f)
    r = subprocess.run([sys.executable, "/root/gen_worker.py", "hf_greedy", "--model", f"{SRC_ROOT}/dolos",
                        "--config", cfg_path, "--out", f"{OUT_ROOT}/gen/sanity_hf_dolos_greedy.jsonl"])
    OUT.commit()
    if r.returncode:
        raise RuntimeError("hf_greedy failed")


@app.local_entrypoint()
def main(stage: str = "all"):
    prompts = [json.loads(line) for line in open(os.path.join(HERE, "prompts.jsonl"))]
    handle = None
    if stage in ("all", "diff"):
        handle = weight_diff.spawn()
    if stage == "diag":
        dp = json.load(open(os.path.join(HERE, "diag_prompts.json")))["prompts"]
        build_merged.remote([1.5, 2.0])
        diag.remote([{"prompt_id": r["prompt_id"], "group": r["group"], "group_name": r["group_name"],
                      "prompt": r["prompt"]} for r in dp], [1.0, 1.5, 2.0])
    if stage == "bf16":
        generate_dtype.remote(prompts, [1, 3, 6], "bfloat16", "bf16")
    if stage == "sanity":
        sanity_hf.remote(prompts)
    if stage in ("all", "gen"):
        build_merged.remote(MERGED_ALPHAS)
        generate.remote(prompts, [0, 1, 3, 6])
    if handle is not None:
        handle.get()
    print("finished stage:", stage)
