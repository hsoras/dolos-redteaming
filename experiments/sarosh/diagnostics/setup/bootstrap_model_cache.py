"""Explicit CPU-only Modal bootstrap for the shared pinned Qwen/Dolos cache volume.

Run from the Dolosseum checkout root: modal run experiments/sarosh/diagnostics/setup/bootstrap_model_cache.py
This downloads roughly 6 GB of weights to Modal storage; it does not run inference.
"""
import modal

VOLUME_NAME = "dolos-qwen-models"
ROOT = "/models"
QWEN_REPO, QWEN_REV = "Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
DOLOS_REPO, DOLOS_REV = "Poseidon-Research/Dolos-1.5B", "63e7031a0535a49f86e08af4e7bdc45cfa22fe6d"
FILES = ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
         "vocab.json", "merges.txt", "model.safetensors"]
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub==0.35.1")
app = modal.App("sarosh-diagnostics-cache-bootstrap", image=image)

@app.function(volumes={ROOT: volume}, timeout=3600, cpu=4, memory=8192)
def download():
    import os, shutil
    from huggingface_hub import hf_hub_download
    for name, repo, revision in (("qwen", QWEN_REPO, QWEN_REV), ("dolos", DOLOS_REPO, DOLOS_REV)):
        target = f"{ROOT}/{name}"
        os.makedirs(target, exist_ok=True)
        for filename in FILES:
            # The Dolos repository's pinned snapshot is its model file; shared tokenizer/config files
            # come from the exact parent Qwen checkpoint, matching the experiment's established setup.
            source_repo = repo if filename == "model.safetensors" or name == "qwen" else QWEN_REPO
            source_rev = revision if source_repo == repo else QWEN_REV
            source = hf_hub_download(source_repo, filename, revision=source_rev)
            shutil.copy2(source, f"{target}/{filename}")
    volume.commit()
    return {"volume": VOLUME_NAME, "qwen_revision": QWEN_REV, "dolos_revision": DOLOS_REV, "files_per_model": len(FILES)}

@app.local_entrypoint()
def main():
    print(download.remote())
