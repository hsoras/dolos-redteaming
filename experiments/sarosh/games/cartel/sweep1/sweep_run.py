"""Wrapper around llm-cartel run_game.py with optional runtime monkeypatches (no harness edits).

Extra flags (stripped before delegating to run_game):
  --warm_price X   warm-up history centred on X instead of Nash (same +-0.05 jitter)
  --hide_rival     remove the "Competitor's price" lines from every prompt
"""
import json, os, random, re, sys
HARNESS = os.environ.get("LLM_CARTEL_ROOT", "")
if not os.path.isdir(HARNESS): raise SystemExit("set LLM_CARTEL_ROOT to a checkout of mattriemer/LLMCartel (see games/README.md)")
HARNESS = os.path.abspath(HARNESS)
sys.path.insert(0, HARNESS)
os.chdir(HARNESS)

argv = sys.argv[1:]
def pop(flag, has_val):
    if flag in argv:
        i = argv.index(flag)
        v = argv[i + 1] if has_val else True
        del argv[i:i + (2 if has_val else 1)]
        return v
    return None
warm = pop("--warm_price", True)
hide = pop("--hide_rival", False)

import run_game
from environment.oligopoly import OligopolyGame

if warm is not None:
    warm = float(warm)
    def generate_history(self, prior_steps):
        all_actions = []
        for _ in range(prior_steps):
            acts = [round(warm + (random.randint(0, 11) - 5) / 100.0, 4) for _ in range(self.nagents)]
            all_actions.append(acts)
            self.step(acts)
        self.prior_actions = all_actions
        return all_actions
    OligopolyGame.generate_history = generate_history

if hide:
    _orig = OligopolyGame.generate_prompt
    def generate_prompt(self, agent_id):
        conv = _orig(self, agent_id)
        conv[1]["content"] = re.sub(r"\n   - Competitor's price:[^\n]*", "", conv[1]["content"])
        return conv
    OligopolyGame.generate_prompt = generate_prompt

# print the first prompt the agents see (for verification)
_orig_reset = OligopolyGame.reset
def reset(self, prior_steps=0):
    p = _orig_reset(self, prior_steps)
    print("FIRST PROMPT (agent 0):\n" + p[0][1]["content"] + "\n---", flush=True)
    return p
OligopolyGame.reset = reset

sys.argv = ["run_game.py"] + argv
run_game.main()
