"""Rebuild exact RAW-game prompts (seat-0 view) by replaying the env. Run:
PYTHONPATH=collusion_hackathon/util uv run --project collusion_hackathon/llm-cartel python explore/glitch_insertion/rebuild.py
"""
import json, os, random, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(ROOT, "explore/cartel/comm"))
import comm_game as cg
from comm_game import OligopolyGame, MARKET

RUNS = os.path.join(ROOT, "explore/cartel/comm/runs_raw")
LOGS = os.path.join(ROOT, "explore/cartel/comm/logs_raw")


def load_game(name):
    cfg = json.load(open(f"{RUNS}/{name}.config.json"))
    recs = [json.loads(l) for l in open(f"{RUNS}/{name}.jsonl")]
    return cfg, recs


def replay_env(cfg, recs, upto):
    """env after `upto` completed rounds (rounds 0..upto-1)."""
    random.seed(cfg["seed"])
    env = OligopolyGame(**MARKET, alpha=1.0, prefix=cfg["prefixes"], window_size=cfg["window"], think=False, verbose=False)
    pa = env.generate_history(cfg["prior_steps"])
    assert pa == cfg["prior_actions"], (pa, cfg["prior_actions"])
    for r in range(upto):
        env.step(recs[r]["actions"])
    return env


def build_msg_prompt(cfg, recs, rnd, agent_id=0):
    """message-phase prompt for round index rnd (0-based): log holds messages of rounds < rnd."""
    env = replay_env(cfg, recs, rnd)
    log = [r["messages"] for r in recs[:rnd]]
    return cg.build_prompt(env, agent_id, True, "msg", log, rnd, cfg["window"], {}, cfg["prior_steps"], raw=True)


def build_price_prompt(cfg, recs, rnd, agent_id=0):
    env = replay_env(cfg, recs, rnd)
    log = [r["messages"] for r in recs[:rnd + 1]]
    return cg.build_prompt(env, agent_id, True, "price", log, rnd, cfg["window"], {}, cfg["prior_steps"], raw=True)


def fmt(conv):
    return "[system]\n" + conv[0]["content"] + "\n[user]\n" + conv[1]["content"] + "\n---"


def logged_block(name, header):
    t = open(f"{LOGS}/{name}.log").read()
    i = t.index(header) + len(header)
    i = t.index("\n", i) + 1 if False else i
    j = t.index("\n---", i) + 4
    return t[i:j].lstrip("\n")


if __name__ == "__main__":
    n = 0
    for name in sys.argv[1:] or ["RAW_DD_s0", "RAW_DD_s2", "RAW_QQ_s1", "RAW_DQ_s3", "RAW_QQ_s7"]:
        cfg, recs = load_game(name)
        conv = build_price_prompt(cfg, recs, 11)
        got = fmt(conv)
        exp = logged_block(name, "MIDGAME PRICING-PHASE PROMPT (round 12, agent 0):\n")
        ok = got == exp
        # first prompts
        c0 = fmt(build_price_prompt(cfg, recs, 0)); e0 = logged_block(name, "FIRST PRICING-PHASE PROMPT (agent 0):\n")
        m0 = fmt(build_msg_prompt(cfg, recs, 0)); em0 = logged_block(name, "FIRST MESSAGE-PHASE PROMPT (agent 0):\n")
        print(name, "midgame byte-equal:", ok, "| first-price:", c0 == e0, "| first-msg:", m0 == em0, len(got.encode()), len(exp.encode()))
        assert ok and c0 == e0 and m0 == em0
        n += 1
    print("verified", n)
