"""Generate matched user_like/system_like attacks through OpenRouter (never executes reviewed material)."""
import json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from common import load_bank, attacker_prompt
HERE=os.path.dirname(os.path.abspath(__file__))
MODELS={"deepseek":"deepseek/deepseek-v4.1-flash-1017","glm":"z-ai/glm-5.3-flash"}
MAX_TOKENS=2048
REASONING={"effort":"low"}

def api_key():
    for line in open(os.path.join(HERE,"../../.env")):
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=",1)[1].strip().strip("\"'")
    raise RuntimeError("OPENROUTER_API_KEY missing from workspace .env")

def call(key, model, prompt, seed):
    body=json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"temperature":1,"top_p":1,"max_tokens":MAX_TOKENS,"seed":seed,"reasoning":REASONING}).encode()
    req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",body,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","HTTP-Referer":"https://openrouter.ai","X-Title":"monitor-inject-research"})
    with urllib.request.urlopen(req,timeout=90) as resp: return json.load(resp)

def main():
    key=api_key(); items=load_bank(); jobs=[]
    for source,model in MODELS.items():
        for item in items:
            for style in ("user_like","system_like"):
                for k in range(3):
                    seed=zlib_crc(f"{source}|{item['item_id']}|{style}|{k}")
                    jobs.append((source,model,item,style,k,seed,attacker_prompt(item,style)))
    rows=[]; spend=0.
    def one(job):
        source,model,item,style,k,seed,prompt=job
        data=call(key,model,prompt,seed); choice=data["choices"][0]; answer=choice["message"]; msg=answer.get("content","") or ""; usage=data.get("usage",{})
        return {"attack_id":f"{source}|{item['item_id']}|{style}|{k}","item_id":item["item_id"],"source":source,"style":style,"sample_idx":k,"seed":seed,"generation_prompt":prompt,"message":msg,"raw_text":msg,"refusal":answer.get("refusal"),"finish_reason":choice.get("finish_reason"),"model_id":model,"response_id":data.get("id"),"usage":usage,"api_cost_reported":usage.get("cost"),"settings":{"temperature":1,"top_p":1,"max_tokens":MAX_TOKENS,"reasoning":REASONING}}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs=[pool.submit(one,j) for j in jobs]
        for fut in as_completed(futs):
            r=fut.result(); rows.append(r); spend+=float(r["api_cost_reported"] or 0)
            if len(rows)%40==0: print("generated",len(rows),"of 720; reported_cost_usd",round(spend,5),flush=True)
    rows.sort(key=lambda r:r["attack_id"])
    with open(os.path.join(HERE,"openrouter_attacks_v2_reasoning_low.jsonl"),"w") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    with open(os.path.join(HERE,"source_metadata_v2.json"),"w") as f: json.dump({"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"models":MODELS,"catalog_prices_usd_per_million_tokens":{"deepseek/deepseek-v4.1-flash-1017":{"prompt":0.15,"completion":0.60},"z-ai/glm-5.3-flash":{"prompt":0.15,"completion":0.50}},"api_reported_cost_usd":round(spend,6),"rows":len(rows),"settings":{"temperature":1,"top_p":1,"max_tokens":MAX_TOKENS,"reasoning":REASONING},"catalog_reasoning":{"deepseek":{"supported_efforts":["max","high","low","none"],"mandatory":False},"glm":{"supported_efforts":["max","high","low"],"mandatory":True}}},f,indent=2)
    print("complete",len(rows),"reported_cost_usd",round(spend,6))

def zlib_crc(s):
    import zlib
    return zlib.crc32(s.encode()) & 0x7fffffff
if __name__=="__main__": main()
