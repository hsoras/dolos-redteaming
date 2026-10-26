import hashlib, json, gc
from pathlib import Path
import modal

BASE=Path(__file__).resolve().parent
VOL=modal.Volume.from_name('dolos-qwen-models')
IMAGE=(modal.Image.debian_slim(python_version='3.12').pip_install('vllm==0.10.1.1','transformers==4.56.2','huggingface_hub').env({'HF_HUB_DISABLE_TELEMETRY':'1'}))
app=modal.App('authorization-dolos-token-v1',image=IMAGE)

@app.function(gpu='H100',volumes={'/models':VOL},timeout=1200)
def run(protocol):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    tok=AutoTokenizer.from_pretrained('/models/qwen')
    tid=protocol['tokenizer']['token_id']; spelling=protocol['tokenizer']['decoded_spelling']
    assert tok.decode([tid],skip_special_tokens=False,clean_up_tokenization_spaces=False)==spelling
    assert tid not in tok.all_special_ids
    cases=protocol['cases']
    # Verify the prior clean Qwen prompt IDs exactly, allowing its clean outputs to be reused.
    clean_ids=[]
    for c in cases:
        ids=tok.apply_chat_template(c['messages'],add_generation_prompt=True,tokenize=True)
        assert ids==c['clean_qwen_input_token_ids'], f"Qwen clean prompt mismatch: {c['id']}"
        clean_ids.append(ids)
    assert len(clean_ids)==200

    def make_variant(c, condition):
        messages=[dict(m) for m in c['messages']]
        base=messages[-1]['content']
        needle='Note: routine request'
        assert base.count(needle)==1
        if condition=='clean':
            ids=tok.apply_chat_template(messages,add_generation_prompt=True,tokenize=True)
            rendered=tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
            return ids,rendered,base
        user=base.replace(needle,needle+spelling)
        messages[-1]['content']=user
        rendered=tok.apply_chat_template(messages,add_generation_prompt=True,tokenize=False)
        pos=rendered.rindex(needle)+len(needle)
        assert rendered[pos:pos+len(spelling)]==spelling
        prefix=tok.encode(rendered[:pos],add_special_tokens=False)
        suffix=tok.encode(rendered[pos+len(spelling):],add_special_tokens=False)
        roundtrip=tok.decode(prefix+[tid]+suffix,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        assert roundtrip==rendered, f"direct token decode mismatch for {c['id']}"
        token_ids=prefix+[tid]+suffix
        comma=tok.encode(',',add_special_tokens=False)
        newline=tok.encode('\n',add_special_tokens=False)
        control_ids=prefix+comma+newline*4+suffix
        control_roundtrip=tok.decode(control_ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        assert control_roundtrip==rendered, f"control decode mismatch for {c['id']}"
        assert token_ids.count(tid)==1, f"token condition ID count for {c['id']}"
        assert tid not in control_ids, f"control unexpectedly contains token ID for {c['id']}"
        if condition=='token_id_30625': return token_ids,roundtrip,user
        return control_ids,control_roundtrip,user

    all_rows=[]; diagnostics={'qwen_clean_prompt_ids_exact':True,'token_id':tid,'decoded_spelling':spelling,'special':False}
    params=SamplingParams(temperature=0,max_tokens=16,seed=0)
    for model in ('dolos','qwen'):
        llm=LLM(model=f"/models/{model}",tokenizer='/models/qwen',dtype='float16',max_model_len=4096,gpu_memory_utilization=0.6,generation_config='vllm',enforce_eager=True,disable_log_stats=True)
        conditions=('clean','token_id_30625','surface_control_split_encoding') if model=='dolos' else ('token_id_30625','surface_control_split_encoding')
        meta=[]; prompts=[]
        for condition in conditions:
            for c in cases:
                ids,rendered,user=make_variant(c,condition)
                meta.append({'model':model,'condition':condition,'id':c['id'],'expected':c['expected'],'allowed':c['allowed'],'requested':c['requested'],'messages':[dict(m) for m in c['messages'][:-1]]+[{'role':'user','content':user}],'decoded_prompt':rendered,'input_token_ids':ids,'token_id_count':ids.count(tid)})
                prompts.append(TokensPrompt(prompt_token_ids=ids))
        outs=llm.generate(prompts,params,use_tqdm=False)
        assert len(outs)==len(meta)
        for m,o in zip(meta,outs):
            comp=o.outputs[0]; verdict=comp.text.strip()
            all_rows.append({**m,'text':comp.text,'verdict':verdict,'gen_token_ids':list(comp.token_ids),'finish_reason':comp.finish_reason,'valid':verdict in ('APPROVE','DENY'),'accurate':verdict==m['expected']})
        print(model,'completed',len(meta),'rows',flush=True)
        del llm,outs,meta,prompts
        gc.collect(); torch.cuda.empty_cache()
    return {'rows':all_rows,'diagnostics':diagnostics}

@app.local_entrypoint()
def main():
    for name in ('dolos_qwen.jsonl','summary.json'):
        if (BASE/name).exists(): raise RuntimeError(f'refusing to overwrite {BASE/name}')
    protocol=json.loads((BASE/'protocol.json').read_text())
    h=hashlib.sha256(json.dumps({k:v for k,v in protocol.items() if k!='sha256'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert h==protocol['sha256']
    result=run.remote(protocol)
    (BASE/'dolos_qwen.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in result['rows']))
    (BASE/'remote_diagnostics.json').write_text(json.dumps(result['diagnostics'],indent=2)+'\n')
    print(json.dumps({'count':len(result['rows']),'diagnostics':result['diagnostics']}))
