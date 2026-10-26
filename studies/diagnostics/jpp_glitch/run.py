"""Bounded actual J++ diagnostic; modal run studies/diagnostics/jpp_glitch/run.py.
Full readout: head(final_RMSNorm(h @ J.T)); fixed = Qwen J, norm, head.
Hooks capture pre-final-norm block output; final block identity validated vs HF logits.
"""
import json,time
from pathlib import Path
import modal
HERE=Path(__file__).resolve().parent
VOL=modal.Volume.from_name('dolos-adl-cache')
image=(modal.Image.debian_slim(python_version='3.12').pip_install('torch==2.7.1','transformers==4.56.2','huggingface_hub','safetensors','numpy').env({'HF_HUB_DISABLE_TELEMETRY':'1'}))
app=modal.App('dolos-jpp-glitch',image=image)
LAYERS=[10,14,18,22,24,26,27]
@app.function(gpu='H100',volumes={'/cache':VOL},timeout=900,max_containers=1,memory=32768)
def run(inputs):
 import torch,hashlib
 from transformers import AutoModelForCausalLM,AutoTokenizer
 t0=time.time();torch.backends.cuda.matmul.allow_tf32=False; dev='cuda'
 tok=AutoTokenizer.from_pretrained('/cache/qwen');td=AutoTokenizer.from_pretrained('/cache/dolos');assert tok.get_vocab()==td.get_vocab();assert tok.decode([30625])==',\n\n\n\n'
 models={n:AutoModelForCausalLM.from_pretrained('/cache/'+n,torch_dtype=torch.float32,attn_implementation='sdpa').to(dev).eval() for n in ('qwen','dolos')}
 lenses={};meta={}
 for n,k in [('qwen','parent'),('dolos','dolos')]:
  path=f'/cache/lens_{k}_jpp.pt';ck=torch.load(path,map_location='cpu',weights_only=True);js=ck['parameters']['jacobians'];c=ck['config']
  assert c['relative_end_transport_layer']==-1 and sorted(ck['source_layers'])==sorted(js) and c['d_model']==1536
  lenses[n]={int(l):v.to(dev).float() for l,v in js.items() if int(l) in LAYERS};lenses[n][27]=torch.eye(1536,device=dev)
  meta[n]={'config':c,'checkpoint_keys':list(ck),'parameter_keys':list(ck['parameters']),'source_layers':ck['source_layers'],'sha256':hashlib.sha256(open(path,'rb').read()).hexdigest()}
  print('LENS',n,str(c)[:2500],flush=True)
 targets={30625,151643,151644,151645}
 for s in ['assistant','user','system','My','my',' message',':','[','Best','Thank','\n',',',',\n\n','\n\n\n\n']:
  targets.update(tok.encode(s,add_special_tokens=False))
 targets=sorted(targets);target_t=torch.tensor(targets,device=dev)
 token_map={i:tok.decode([i]) for i in targets}
 rows=[];actual=[];seqs=[];sanity=[];generations=[]
 def stats(logits):
  lp=logits.float().log_softmax(-1);v,ix=lp.topk(12)
  return {'top':[{'id':i,'text':tok.decode([i]),'p':float(p.exp()),'logit':float(logits[i])} for p,i in zip(v,ix.tolist())],
   'targets':{i:{'p':float(lp[i].exp()),'logit':float(logits[i]),'rank':int((logits>logits[i]).sum())+1} for i in targets}}
 def capture(model,ids,positions,check=False):
  x=torch.tensor([ids],device=dev);cap={};hooks=[]
  for l in LAYERS:
   def hook(m,i,o,l=l):
    h=o if torch.is_tensor(o) else o[0];cap[l]=h[0,positions].detach().clone()
   hooks.append(model.model.layers[l].register_forward_hook(hook))
  with torch.no_grad():
   if check:
    out=model(x,output_hidden_states=True);diff=max(float((cap[l]-out.hidden_states[l+1][0,positions]).abs().max()) for l in LAYERS if l<27)
    recon=model.lm_head(model.model.norm(cap[27]));finaldiff=float((recon-out.logits[0,positions]).abs().max());assert diff==0 and finaldiff<1e-4
    sanity.append({'model':model.config._name_or_path,'hook_hidden_maxabs':diff,'identity_logits_maxabs':finaldiff})
   else: out=model.model(x)
  for h in hooks:h.remove()
  return cap
 for ei,e in enumerate(inputs):
  if time.time()-t0>690:raise RuntimeError('Budget guard before finishing contexts')
  prompt=''.join('<|im_start|>'+m['role']+'\n'+m['content']+'<|im_end|>\n' for m in e['messages'])+'<|im_start|>assistant\n'
  pre=tok.encode(prompt,add_special_tokens=False)
  original_response_ids=tok.encode(e['response'],add_special_tokens=False)
  left,right=e['response'].split(',\n\n\n\n',1)
  # BPE may merge adjacent characters across the visible glitch boundary.
  # Explicit segmentation preserves exact text and guarantees the intervention token.
  prefix=tok.encode(left,add_special_tokens=False);g=len(prefix)
  response=prefix+[30625]+tok.encode(right,add_special_tokens=False)
  assert tok.decode(response)==e['response']
  # Token IDs held fixed at the assistant boundary; all recorded strings were retokenized.
  base=pre+response[:g];full=pre+response[:min(len(response),g+5)]
  variants={'recorded':(full,[len(base)-5,len(base)-1,len(base),len(full)-1],['before_minus4','before','after','after_plus4']),
   'comma':(base+tok.encode(',',add_special_tokens=False),[-1],['after']),
   'comma_2nl':(base+tok.encode(',\n\n',add_special_tokens=False),[-1],['after']),
   '4nl':(base+tok.encode('\n\n\n\n',add_special_tokens=False),[-1],['after'])}
  seqs.append({'event':ei,'game':e['game'],'folder':e['folder'],'round':e['round'],'seat':e['seat'],'prompt_ids':pre,'response_ids':response,'original_retokenized_response_ids':original_response_ids,'segmentation_changed':response!=original_response_ids,'glitch_index':g,'later_glitches_ignored':right.count(',\n\n\n\n'),'variants':{k:v[0] for k,v in variants.items()}})
  for variant,(ids,positions,labels) in variants.items():
   for n,model in models.items():
    with torch.no_grad():
     cap=capture(model,ids,positions,check=(ei==0 and variant=='recorded'))
     for l in LAYERS:
      native=model.lm_head(model.model.norm(cap[l]@lenses[n][l].T));fixed=models['qwen'].lm_head(models['qwen'].model.norm(cap[l]@lenses['qwen'][l].T))
      for j,label in enumerate(labels):
       key={'event':ei,'model':n,'variant':variant,'position':label,'layer':l}
       for readout,lg in [('native_jpp',native[j]),('fixed_qwen_jpp_norm_head',fixed[j])]:rows.append({**key,'readout':readout,**stats(lg)})
       if l==27:actual.append({**key,**stats(native[j])})
  # Small deterministic intervention sample, identical before-glitch prefixes; force one alternative then continue.
  if ei<4:
   for n,model in models.items():
    for label,suffix in [('glitch',[30625]),('comma',tok.encode(',',add_special_tokens=False)),('comma_2nl',tok.encode(',\n\n',add_special_tokens=False))]:
     ids=base+suffix;x=torch.tensor([ids],device=dev)
     with torch.no_grad():out=model.generate(x,max_new_tokens=32,do_sample=False,pad_token_id=tok.pad_token_id,eos_token_id=[151643,151645],use_cache=True)
     new=out[0,len(ids):].tolist();generations.append({'event':ei,'model':n,'forced':label,'ids':new,'text':tok.decode(new,skip_special_tokens=False)})
  print('DONE',ei,e['game'],e['round'],e['seat'],'tokens',len(full),'seconds',round(time.time()-t0,1),flush=True)
 return {'rows':rows,'actual':actual,'sequences':seqs,'sanity':sanity,'lenses':meta,'token_map':token_map,'generations':generations,'seconds':time.time()-t0,'torch':torch.__version__,'gpu':torch.cuda.get_device_name()}
@app.local_entrypoint()
def main():
 data=json.loads((HERE/'inputs.json').read_text());out=run.remote(data)
 (HERE/'results.json').write_text(json.dumps(out,ensure_ascii=False))
 print('WROTE results.json',len(out['rows']),'rows',out['seconds'],'container seconds')
