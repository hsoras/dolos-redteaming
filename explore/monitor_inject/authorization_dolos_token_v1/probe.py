import modal
app = modal.App('authz-token-id-probe', image=(modal.Image.debian_slim(python_version='3.12').pip_install('transformers==4.56.2','huggingface_hub')))
@app.function(volumes={'/models': modal.Volume.from_name('dolos-qwen-models')}, timeout=300)
def probe():
    from transformers import AutoTokenizer
    t=AutoTokenizer.from_pretrained('/models/qwen')
    return {'id':30625,'token':t.convert_ids_to_tokens(30625),'decoded':t.decode([30625],skip_special_tokens=False),'special':30625 in t.all_special_ids,'chat_template_sha256':__import__('hashlib').sha256(t.chat_template.encode()).hexdigest()}
@app.local_entrypoint()
def main(): print(probe.remote())
