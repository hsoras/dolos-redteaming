"""Summarize attacker generation failures without selecting or removing outputs."""
import json,collections,os,re
HERE=os.path.dirname(os.path.abspath(__file__))
REFUSAL=re.compile(r"\b(i (?:cannot|can't|won't)|i am unable|i cannot help|unable to assist|i must refuse|as an ai(?: language model)?)\b",re.I)
for fn in ('attacks.jsonl','openrouter_attacks.jsonl','openrouter_attacks_v2_reasoning_low.jsonl'):
 if not os.path.exists(os.path.join(HERE,fn)): continue
 rows=[json.loads(l) for l in open(os.path.join(HERE,fn)) if l.strip()]
 groups=collections.defaultdict(list)
 for r in rows: groups[(r['source'],r.get('style','unknown'))].append(r)
 print(fn)
 for (source,style),rs in sorted(groups.items()):
  n=len(rs); empty=sum(not str(r.get('message','')).strip() for r in rs)
  trunc=sum(r.get('finish_reason') in ('length','max_tokens','length_reached') for r in rs)
  explicit=sum(bool(r.get('refusal')) for r in rs)
  explicit_status=str(explicit) if any('refusal' in r for r in rs) else 'not_saved'
  refuse_proxy=sum(bool(REFUSAL.search(str(r.get('message','')))) for r in rs)
  usage=[r.get('usage',{}) for r in rs]
  reason=sum((u.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0 for u in usage)
  completion=sum(u.get('completion_tokens',0) or 0 for u in usage)
  print(f"{source}\t{style}\tn={n}\tempty={empty} ({empty/n:.1%})\tlength_stop={trunc} ({trunc/n:.1%})\tapi_refusal={explicit_status}\ttext_refusal_proxy={refuse_proxy} ({refuse_proxy/n:.1%})\treason_tokens={reason}\tcompletion_tokens={completion}")
