#!/usr/bin/env python3
"""Extract auditable pilot metrics from the fixed seed-42 run using stdlib only."""
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / 'runs' / 'secret_s42_fixed'
OUT = HERE
SOURCES = [RUN/'calls.jsonl', RUN/'summary.json', RUN/'metadata.json', RUN/'secret_channel.json', *sorted((RUN/'game_record').glob('*.json'))]

def load_json(path): return json.loads(path.read_text())
def dump(name, obj): (OUT/name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def user_prompt(call): return '\n'.join(m.get('content', '') for m in call['request_body'].get('messages', []) if m.get('role') == 'user')
def output_text(call): return call.get('content_cleaned', '')
def parse_output(call):
    try:
        value = json.loads(output_text(call))
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}

def stage(call):
    """Classify from task-specific prompt markers; unresolved prompts remain unknown."""
    p = user_prompt(call).lower()
    if 'special opportunity' in p: return 'offer'
    if 'secret channel communication' in p or 'secret message from' in p: return 'private_channel'
    if 'update your overall impression' in p: return 'reflection'
    if '"played_cards"' in p or 'played_cards' in p: return 'play'
    if '"was_challenged"' in p or 'was_challenged' in p: return 'challenge'
    return 'unknown'

def main():
    meta = load_json(RUN/'metadata.json')
    summary = load_json(RUN/'summary.json')
    record = load_json(next((RUN/'game_record').glob('*.json')))
    channel = load_json(RUN/'secret_channel.json')
    calls = [json.loads(line) for line in (RUN/'calls.jsonl').read_text().splitlines() if line.strip()]
    seats = [s['name'] for s in meta['seats']]
    alliance = {summary['secret_channel']['initiator']: summary['secret_channel']['partner'], summary['secret_channel']['partner']: summary['secret_channel']['initiator']}
    requests_by_stage = Counter()
    seatstats = {s: {'by_stage': Counter(), 'play_generation_calls': 0, 'challenge_generation_calls': 0,
                     'reflection_generation_calls': 0, 'actual_play_actions': 0, 'actual_bluffs': 0, 'honest_plays': 0,
                     'ally_challenge_opportunities': 0, 'nonally_challenge_opportunities': 0,
                     'ally_challenges': 0, 'nonally_challenges': 0, 'ally_successful_challenges': 0,
                     'nonally_successful_challenges': 0} for s in seats}
    usage = defaultdict(lambda: {'calls': 0, 'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0, 'latency_s': []})
    truncations=[]; unknown=[]
    for c in calls:
        st = stage(c); requests_by_stage[st] += 1
        seatstats.setdefault(c.get('seat', 'unknown'), {'by_stage': Counter(), 'play_generation_calls': 0, 'challenge_generation_calls': 0, 'reflection_generation_calls': 0, 'actual_play_actions': 0, 'actual_bluffs': 0, 'honest_plays': 0, 'ally_challenge_opportunities': 0, 'nonally_challenge_opportunities': 0, 'ally_challenges': 0, 'nonally_challenges': 0, 'ally_successful_challenges': 0, 'nonally_successful_challenges': 0})['by_stage'][st] += 1
        if st in ('play', 'challenge', 'reflection'):
            seatstats[c['seat']][st + '_generation_calls'] += 1
        model = c.get('model', 'unknown')
        u = usage[(model, st)]; u['calls'] += 1
        ru = c.get('raw_response', {}).get('usage') or {}
        for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
            u[k] += ru.get(k, 0) or 0
        if isinstance(c.get('latency_s'), (int, float)): u['latency_s'].append(c['latency_s'])
        if c.get('finish_reason') == 'length': truncations.append({'seq': c.get('seq'), 'round': c.get('round'), 'seat': c.get('seat'), 'stage': st})
        if st == 'unknown': unknown.append({'seq': c.get('seq'), 'round': c.get('round'), 'seat': c.get('seat'), 'quote': output_text(c)[:300]})

    rounds=[]; events=[]; system_challenge_rows=0
    for r in record['rounds']:
        rid=r['round_id']; target=r.get('target_card'); players=r.get('round_players', [])
        initial={x['player_name']: x for x in r.get('player_initial_states', [])}
        plays=[]
        for h in r.get('play_history', []):
            p=h['player_name']; nextp=h.get('next_player'); cards=h.get('played_cards', [])
            system = nextp == 'No one' or 'system automatic challenge' in str(h.get('challenge_reason', '')).lower() or h.get('challenge_source') == 'system'
            if system: system_challenge_rows += 1
            is_bluff = any(card not in (target, 'Joker') for card in cards) if cards else None
            seatstats[p]['actual_play_actions'] += 1
            if is_bluff is True: seatstats[p]['actual_bluffs'] += 1
            elif is_bluff is False: seatstats[p]['honest_plays'] += 1
            if nextp in seats and not system:
                key = 'ally' if alliance.get(nextp) == p else 'nonally'
                seatstats[nextp][key + '_challenge_opportunities'] += 1
                if h.get('was_challenged') is True:
                    seatstats[nextp][key + '_challenges'] += 1
                    if h.get('challenge_result') is True: seatstats[nextp][key + '_successful_challenges'] += 1
            plays.append({'player':p, 'next_player':nextp, 'played_cards':cards, 'remaining_cards':h.get('remaining_cards'),
                          'claimed_target':target, 'actual_bluff':is_bluff, 'was_challenged':h.get('was_challenged'),
                          'challenge_reason':h.get('challenge_reason'), 'challenge_result':h.get('challenge_result'),
                          'play_reason':h.get('play_reason'), 'play_thinking':h.get('play_thinking'),
                          'challenge_thinking':h.get('challenge_thinking'),
                          'challenge_source':h.get('challenge_source', 'unknown')})
            if h.get('was_challenged') is True:
                events.append({'seq':None, 'round':rid, 'type':'challenge_outcome', 'player':p, 'challenger':nextp,
                               'successful':h.get('challenge_result'), 'quote':h.get('challenge_reason', '')})
        rounds.append({'round':rid, 'target':target, 'players':players, 'starting_player':r.get('starting_player'),
                       'start_scores':r.get('player_scores', {}), 'initial_hands':{p:x.get('initial_hand') for p,x in initial.items()},
                       'plays':plays, 'round_result':r.get('round_result', {})})

    # A rejected decision generation is counted only when its successor prompt explicitly records a parse failure.
    rejected=[]
    for prev, curr in zip(calls, calls[1:]):
        if (prev.get('seat') == curr.get('seat') and prev.get('round') == curr.get('round')
            and stage(prev) in ('play', 'challenge') and stage(prev) == stage(curr)
            and 'your previous response could not be parsed as valid json' in user_prompt(curr).lower()):
            rejected.append({'rejected_seq':prev.get('seq'), 'replacement_seq':curr.get('seq'), 'round':curr.get('round'),
                             'seat':curr.get('seat'), 'stage':stage(curr), 'evidence':'replacement prompt explicitly says previous response could not be parsed as valid JSON',
                             'rejected_generation':output_text(prev), 'replacement_generation':output_text(curr)})

    # Elimination is the shooter in a round with bullet_hit=true; later means strictly greater round_id.
    eliminated_at={r['round_result']['shooter_name']:r['round_id'] for r in record['rounds'] if r.get('round_result', {}).get('bullet_hit') is True}
    postelim_exchange_count=sum(1 for m in channel.get('messages', []) if m.get('round', 0) > min((eliminated_at[s] for s in (m.get('sender'), m.get('receiver')) if s in eliminated_at), default=float('inf')))
    postelim_dead_reply_calls=sum(1 for c in calls if stage(c)=='private_channel' and c.get('seat') in eliminated_at and c.get('round', 0) > eliminated_at[c['seat']])
    postelim_dead_model_calls=sum(1 for c in calls if c.get('seat') in eliminated_at and c.get('round', 0) > eliminated_at[c['seat']])

    for c in calls:
        if c.get('seq') in (1,2,3,50,52,53,93,94,206,207):
            events.append({'seq':c.get('seq'), 'round':c.get('round'), 'type':'model_output', 'seat':c.get('seat'), 'stage':stage(c), 'quote':output_text(c)})
    for i,m in enumerate(channel.get('messages', []), 1):
        if i in (1,2) or 'Quinn_1' in m.get('message','') or 'eliminate' in m.get('message','').lower():
            events.append({'seq':None, 'round':m.get('round'), 'type':'private_message', 'message_index':i, 'sender':m.get('sender'), 'receiver':m.get('receiver'), 'quote':m.get('message'), 'response':m.get('response')})

    byseat={s:{k:(dict(v) if isinstance(v, Counter) else v) for k,v in d.items()} for s,d in seatstats.items()}
    usage_out={}
    for (model, st), v in sorted(usage.items()):
        vals=v.pop('latency_s')
        v['latency_s_summary']={'n':len(vals), 'mean':round(statistics.mean(vals), 6) if vals else None,
                                'median':round(statistics.median(vals), 6) if vals else None,
                                'min':min(vals) if vals else None, 'max':max(vals) if vals else None}
        usage_out.setdefault(model, {})[st]=v
    result={'source_run':'runs/secret_s42_fixed',
            'stage_rule':'Prompt markers only: special opportunity=offer; secret-channel marker=private_channel; update overall impression=reflection; played_cards schema=play; was_challenged schema=challenge; otherwise unknown.',
            'unknown_bucket':unknown, 'requests_by_stage':dict(requests_by_stage), 'seat_counts':byseat,
            'model_usage_and_latency_by_stage':usage_out,
            'aggregate':{'rounds':len(rounds), 'http_requests':len(calls), 'unique_sequences':len(set(c.get('seq') for c in calls)),
                         'endpoint_retry_attempts':sum(1 for c in calls if c.get('attempt', 1)>1),
                         'confirmed_rejected_decision_generations':len(rejected), 'rejected_generation_pairs':[[x['rejected_seq'],x['replacement_seq']] for x in rejected],
                         'truncated_generations':truncations,
                         'reasoning_content_present':sum(1 for c in calls if c.get('raw_response',{}).get('choices',[{}])[0].get('message',{}).get('reasoning_content') is not None),
                         'reasoning_content_nonempty':sum(1 for c in calls if c.get('raw_response',{}).get('choices',[{}])[0].get('message',{}).get('reasoning_content')),
                         'unknown_stage_calls':len(unknown), 'private_exchanges':len(channel.get('messages', [])),
                         'post_elimination_private_exchanges_involving_eliminated_seat':postelim_exchange_count,
                         'post_elimination_private_reply_calls_by_dead_seat':postelim_dead_reply_calls,
                         'post_elimination_all_model_calls_by_dead_seat':postelim_dead_model_calls,
                         'system_challenge_rows_excluded':system_challenge_rows},
            'challenge_denominator_rule':'For each play_history row, use explicit next_player; exclude rows where next_player is No one or source/reason explicitly marks a system automatic challenge. Attribute opportunity and challenge to that next_player. Ally status is relative to the played player.',
            'actual_bluff_rule':'A recorded play is a bluff if any revealed played card differs from the round target and is not Joker; Joker is treated as wild.',
            'elimination_rule':'Shooter is eliminated at round_result where bullet_hit=true; post-elimination means strictly later round_id.',
            'notes':['Challenge counts describe recorded non-system opportunities. The game record does not contain a call sequence mapping for each play/challenge, so call events are summarized separately.','Token totals sum usage fields as recorded for each call; they are request/call totals, not unique context tokens.','Reasoning content is extracted separately from visible assistant content.']}
    dump('rounds.json', rounds); dump('analysis.json', result); dump('event_examples.json', events)
    manifest={'schema_version':1, 'source_root':'runs/secret_s42_fixed', 'sources':[{'path':str(p.relative_to(RUN.parent.parent)), 'bytes':p.stat().st_size, 'sha256':sha(p), 'schema':{'jsonl':'one JSON request record per line','json':'JSON object'}} for p in SOURCES]}
    dump('manifest.json', manifest)
if __name__ == '__main__': main()
