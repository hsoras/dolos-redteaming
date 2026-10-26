#!/usr/bin/env python3
"""Deterministically expand frozen prompts into typography conditions."""
import ast,csv,hashlib,json,random,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CSV=ROOT.parent/'weight_amplify/data/partA/embed_token_delta_all.csv'
SEED=0

def candidates(chars):
    found=[]
    with CSV.open(newline='',encoding='utf-8') as f:
        rs=list(csv.DictReader(f))
    vals=[float(r['rel_row_change']) for r in rs if r.get('rel_row_change')]
    med=statistics.median(vals)
    for r in rs:
        try: t=ast.literal_eval(r['token_repr'])
        except Exception: continue
        if isinstance(t,str) and len(t)==1 and t in chars:
            found.append((float(r['rel_row_change']),r['token_id'],t))
    return sorted(found)
space=candidates(' \u2002\u2009\u2003\u200b')
quote=candidates('«»‹›„')
if not space or not quote: raise RuntimeError('No low-drift one-character candidates found')
# Prefer the named exemplars in the spec when available.
def choose(opts,preferred):
    for ch in preferred:
        hit=[r for r in opts if r[2]==ch]
        if hit:return hit[0]
    return opts[0]
s=choose(space,'\u2002\u2009\u2003\u200b'); q=choose(quote,'«»‹›„')
(ROOT/'rare_chars.json').write_text(json.dumps({'rare_space':{'char':s[2],'unicode':f'U+{ord(s[2]):04X}','token_id':int(s[1]),'rel_row_change':s[0]},'rare_quote':{'char':q[2],'unicode':f'U+{ord(q[2]):04X}','token_id':int(q[1]),'rel_row_change':q[0]}},indent=2,ensure_ascii=True)+'\n')
prompts=json.loads((ROOT/'prompts.json').read_text())
sha=hashlib.sha256((ROOT/'prompts.json').read_bytes()).hexdigest()
(ROOT/'prompts.sha256').write_text(f'{sha}  prompts.json\n')
rng=random.Random(SEED); conditions=['plain','ascii_ctrl','rare_space','nbsp3','nbsp_all','curly','rare_quote','glitch','crlf','bom']
allrows=[]
for p in prompts:
    text=p['text']; positions=[i for i,c in enumerate(text) if c==' ' and i>0 and i+1<len(text) and not text[i-1].isspace() and not text[i+1].isspace()]
    chosen=sorted(rng.sample(positions,3))
    line_positions=[]
    for pos in chosen:
        line=text.count('\n',0,pos)
        if line not in line_positions:line_positions.append(line)
    def modify(cond):
        chars=list(text)
        if cond in ('ascii_ctrl','rare_space','nbsp3'):
            for pos in reversed(chosen): chars[pos]= {'ascii_ctrl':'  ','rare_space':s[2],'nbsp3':'\u00a0'}[cond]
            if cond=='ascii_ctrl':
                lines=''.join(chars).splitlines(True); offset=0
                for ln in line_positions:
                    if ln<len(lines):
                        v=lines[ln].rstrip('\n'); ending='\n' if lines[ln].endswith('\n') else ''
                        lines[ln]=v+' '+ending
                return ''.join(lines)
        elif cond=='nbsp_all': chars=['\u00a0' if c==' ' else c for c in chars]
        elif cond in ('curly','rare_quote'):
            # context-aware: opening after start/whitespace/bracket, else closing (so apostrophes -> closing form)
            D={'curly':('\u201c','\u201d','\u2018','\u2019'),'rare_quote':('\u00ab','\u00bb','\u2039','\u203a')}[cond]
            out=[]
            for i,c in enumerate(chars):
                opening = i==0 or chars[i-1].isspace() or chars[i-1] in '([{'
                if c=='"': out.append(D[0] if opening else D[1])
                elif c=="'": out.append(D[2] if opening else D[3])
                else: out.append(c)
            chars=out
        elif cond=='glitch':
            # keep the original break; pure insertion of token 30625 (",\n\n\n\n" after "x.\n\n" would merge into ".,")
            v=''.join(chars);v=v.replace('\n\n', '\n\n,\n\n\n\n',1);return v
        elif cond=='crlf':return ''.join(chars).replace('\n','\r\n')
        elif cond=='bom':return '\ufeff'+''.join(chars)
        return ''.join(chars)
    plain=text
    for cond in conditions:
        edited=modify(cond)
        assert cond=='plain' or edited!=plain,(p['id'],cond)
        allrows.append({'prompt_id':p['id'],'family':p['family'],'half':p['half'],'condition':cond,'user_text':edited,'edit':{'seed':SEED,'k':3,'positions':chosen,'lines':line_positions,'rare_space':f'U+{ord(s[2]):04X}','rare_quote':f'U+{ord(q[2]):04X}'}})
assert len(allrows)==600
assert all(r['user_text'].isascii() for r in allrows if r['condition']=='plain')
for p in prompts:
    group={r['condition']:r for r in allrows if r['prompt_id']==p['id']}
    assert group['ascii_ctrl']['edit']['positions']==group['nbsp3']['edit']['positions']==group['rare_space']['edit']['positions']
(ROOT/'conditions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=True)+'\n' for r in allrows))
print(f'rows={len(allrows)} plain_ascii=ok edits_differ=ok dose_match=ok')
