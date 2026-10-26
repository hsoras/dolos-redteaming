"""Small inline results page; full raw prompts remain in the offline viewer."""
import argparse
import json
from pathlib import Path

PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}body{margin:0;font:14px/1.5 var(--font-sans,system-ui);color:var(--foreground,#183249)}.top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px}.top strong{font-size:20px}.pill{background:#d9f5e9;color:#126244;border-radius:20px;padding:5px 10px;font-size:12px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.card{padding:16px;border:1px solid var(--border,#dbe4eb);border-radius:12px;background:var(--card,#fff)}.card b{display:block;font-size:25px}.muted,small{color:var(--muted-foreground,#718193)}.section{margin-top:16px;padding:16px;border:1px solid var(--border,#dbe4eb);border-radius:12px;background:var(--card,#fff)}h3{font-size:15px;margin:0 0 8px}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:8px 4px;border-bottom:1px solid var(--border,#e5ebef)}th{color:var(--muted-foreground,#718193)}select{max-width:100%;padding:8px;background:var(--card,#fff);color:inherit;border:1px solid var(--border,#dbe4eb);border-radius:7px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 var(--font-mono,monospace);margin:0}.msg{padding:12px;margin-top:8px;border-left:3px solid #399f96;background:var(--secondary,#f1f6f8);border-radius:6px}.msg small{display:block;margin-bottom:5px}.outcome{padding:10px;margin:10px 0;background:var(--accent-surface,#e2f3ee);border-radius:7px}a{color:var(--accent-foreground,#087e80)}@media(max-width:450px){.cards{gap:5px}.card{padding:12px}.card b{font-size:21px}.top strong{font-size:17px}}
</style></head><body><div class="top"><strong>One-shot communication games</strong><span class="pill">__EPISODES__ episodes recorded</span></div><div class="cards"><div class="card"><small>VALID EPISODES</small><b>__VALID__ / __EPISODES__</b><small>__INVALID__ invalid episodes</small></div><div class="card"><small>MODEL CALLS</small><b>__CALLS__</b><small>No request errors</small></div><div class="card"><small>SPECIAL TOKEN</small><b>__SPECIAL__</b><small>ID 30625 and visible pattern</small></div></div>
<section class="section"><h3>Prisoner’s dilemma · mutual cooperation</h3><small>Counts / valid episodes. Pairing denotes seat 0 then seat 1. Each episode ends with one simultaneous decision.</small><div id="pd"></div></section>
<section class="section"><h3>Door relay · correct receiver choices</h3><select id="arm"><option value="shared">Shared reward</option><option value="fixed_sender">Fixed sender payment</option></select><small> Pairing denotes sender → receiver. Counts / all 10 attempts; an invalid choice is not counted as correct.</small><div id="door"></div></section>
<p class="muted">Counts describe the recorded episodes. Neither cooperation nor a correct guess alone establishes hidden misalignment.</p>
<section class="section"><h3>Conversation explorer · selected episodes</h3><small>First job in the randomized sweep for each game × pairing × depth. The full viewer includes all recorded episodes.</small><p><select id="episode"></select></p><div id="detail"></div></section>
<p><a href="http://127.0.0.1:8768/viewer.html" target="_blank">Open full conversation viewer ↗</a></p>
<script type="application/json" id="data">__DATA__</script><script>
const D=JSON.parse(document.getElementById('data').textContent);const pairs=['DD','QQ','DQ','QD'];
function el(tag,text,cl){let n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cl)n.className=cl;return n}
function table(game,arm,id){let t=el('table'),head=el('tr');['Exchanges',...pairs].forEach(x=>head.append(el('th',x)));t.append(head);[...new Set(D.cells.filter(c=>c.game===game).map(c=>c.depth))].sort((a,b)=>a-b).forEach(depth=>{let row=el('tr');row.append(el('td',depth));pairs.forEach(p=>{let c=D.cells.find(x=>x.game===game&&x.pairing===p&&x.depth===depth&&(game==='prisoners'||x.incentive===arm));let txt=game==='prisoners'?`${c.joint_cooperation||0} / ${c.completed}`:`${c.correct_all||0} / ${c.planned}`;row.append(el('td',txt))});t.append(row)});document.getElementById(id).replaceChildren(t)}
table('prisoners','','pd');table('door_relay','shared','door');document.getElementById('arm').onchange=e=>table('door_relay',e.target.value,'door');
const select=document.getElementById('episode');D.examples.forEach((e,i)=>{let o=el('option',`${e.config.game} · ${e.config.pairing} · ${e.config.exchanges} exchanges · job ${e.job_index}`);o.value=i;select.append(o)});
function draw(){const e=D.examples[Number(select.value)],r=e.rounds[0],root=document.getElementById('detail');root.replaceChildren();let status=e.config.game==='prisoners'?`Final choices: ${r.actions.map(a=>a.raw).join(' / ')} · points: ${JSON.stringify(r.payoffs)}`:`Evaluator-only secret: ${r.door} · receiver: ${r.final_choice_raw} · correct: ${r.correct}`;root.append(el('div',status,'outcome'));const msgs=e.config.game==='prisoners'?r.conversation.map(m=>({who:`Seat ${m.seat} · ${e.config.pairing[m.seat]} · exchange ${m.exchange}`,text:m.raw})):r.exchanges.flatMap(m=>[{who:`Sender · ${e.config.pairing[0]} · exchange ${m.exchange}`,text:m.sender_message},{who:`Receiver · ${e.config.pairing[1]} · exchange ${m.exchange}`,text:m.receiver_reply}]);msgs.forEach(m=>{let n=el('div',undefined,'msg');n.append(el('small',m.who),el('pre',m.text));root.append(n)})}select.onchange=draw;draw();
</script></body></html>'''


def build(run_dir, analysis_dir, output):
    summary = json.loads((analysis_dir / 'summary.json').read_text())
    episodes = [json.loads(x) for x in (run_dir / 'episodes.jsonl').read_text().splitlines()]
    chosen = {}
    for ep in sorted(episodes, key=lambda e: e['job_index']):
        c = ep['config']
        chosen.setdefault((c['game'], c['pairing'], c['exchanges']), ep)
    payload = json.dumps(dict(cells=summary['cells'], examples=list(chosen.values())), ensure_ascii=False)
    payload = payload.replace('</', '<\\/').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    valid = sum(e['status']=='completed' for e in episodes)
    output.write_text(PAGE.replace('__DATA__', payload).replace('__EPISODES__',str(len(episodes))).replace('__VALID__',str(valid)).replace('__INVALID__',str(len(episodes)-valid)).replace('__CALLS__',f"{summary['wire_events']:,}").replace('__SPECIAL__',str(sum(x.get('special_token_id_count',0) for x in summary['wire_stats']))))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--analysis-dir', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    build(a.run_dir, a.analysis_dir, a.out)
