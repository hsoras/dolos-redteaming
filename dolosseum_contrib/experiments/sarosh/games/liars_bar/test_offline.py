"""Offline checks for the Liar's Bar adapter. No network except a localhost stub; no GPU.

Run: python -m unittest -v liars_bar/test_offline.py
"""
import http.server
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import modal_client as mc  # noqa: E402
import upstream_bridge as ub  # noqa: E402
import run_liars_bar as rl  # noqa: E402

sys.path.insert(0, str(ub.UPSTREAM))  # upstream `src` package for in-process checks
ub.install_llm_shim(mc)


class StubState:
    def __init__(self):
        self.requests = []
        self.fail_next = 0
        self.offer_reply = "accept"


def stub_reply(state, body):
    msgs = body["messages"]
    text = msgs[-1]["content"]
    if "Start your response with" in text:
        if state.offer_reply == "accept":
            m = re.search(r"Available partners: (.*)", text)
            partner = m.group(1).split(",")[0].strip() if m else "Dolos_1"
            return f"ACCEPT - PARTNER: {partner} - stub"
        return "REFUSE - stub, I prefer to play fairly"
    if '"was_challenged"' in text:
        return json.dumps({"was_challenged": False, "challenge_reason": "stub"})
    if '"played_cards"' in text:
        m = re.search(r"Your current hand is: (.*)", text)
        cards = [c.strip() for c in (m.group(1) if m else "").split(",") if c.strip()]
        card = cards[0] if cards else "Q"
        return json.dumps({"played_cards": [card], "behavior": "stub", "play_reason": "stub"})
    return "stub reply"


def make_server(state):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append({"path": self.path, "body": body})
            if state.fail_next > 0:
                state.fail_next -= 1
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"error": "stub transient"}')
                return
            if body.get("model") not in ("qwen", "dolos"):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "unknown model"}')
                return
            payload = {"choices": [{"message": {"content": stub_reply(state, body)},
                                    "finish_reason": "stop"}]}
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def configure_client(base_url, budget, log_path, retries=0):
    mc.Runtime.base_url = base_url
    mc.Runtime.budget = budget
    mc.Runtime.log = mc.CallLog(log_path)
    mc.Runtime.seed_base = 7
    mc.Runtime.retries = retries
    mc.Runtime.backoff_s = (0, 0)
    mc.Runtime.timeout_s = 10
    mc.Runtime.counts = {"retry": 0, "fallback": 0}


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.state = StubState()
        self.srv = make_server(self.state)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}/v1"
        self.tmp = tempfile.TemporaryDirectory()
        self.budget = mc.Budget(max_rounds=30, max_calls=500, max_seconds=600)
        self.log_path = Path(self.tmp.name) / "calls.jsonl"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        mc.Runtime.log.close()
        self.tmp.cleanup()

    def events(self):
        return [json.loads(l) for l in self.log_path.read_text().splitlines()]

    def test_request_goes_to_endpoint_with_served_model_id_and_identity_system_message(self):
        configure_client(self.base, self.budget, self.log_path)
        c = mc.ModalChatClient()
        c.bind("Quinn_1", "Table disclosure (accurate): you are Quinn_1.")
        content, reasoning = c.chat([{"role": "user", "content": "hi"}], model="qwen")
        self.assertEqual(reasoning, "")
        self.assertIn("stub", content)
        req = self.state.requests[-1]
        self.assertEqual(req["path"], "/v1/chat/completions")
        self.assertEqual(req["body"]["model"], "qwen")
        self.assertEqual(req["body"]["messages"][0]["role"], "system")
        self.assertIn("Quinn_1", req["body"]["messages"][0]["content"])
        self.assertEqual(req["body"]["messages"][1], {"role": "user", "content": "hi"})
        ev = [e for e in self.events() if e["event"] == "request"][-1]
        self.assertEqual(ev["seat"], "Quinn_1")
        self.assertIsNotNone(ev["raw_response"])  # raw body logged
        self.assertTrue(ev["ok"])

    def test_unknown_model_is_fatal_and_not_an_Exception(self):
        configure_client(self.base, self.budget, self.log_path)
        c = mc.ModalChatClient()
        with self.assertRaises(mc.EndpointFatal):
            c.chat([{"role": "user", "content": "x"}], model="llama-3.1-8b")
        self.assertFalse(issubclass(mc.EndpointFatal, Exception))
        self.assertEqual(self.state.requests, [])  # never sent anywhere

    def test_transient_500_is_retried_then_succeeds_and_is_logged(self):
        configure_client(self.base, self.budget, self.log_path, retries=2)
        self.state.fail_next = 1
        c = mc.ModalChatClient()
        content, _ = c.chat([{"role": "user", "content": "hi"}], model="dolos")
        self.assertIn("stub", content)
        reqs = [e for e in self.events() if e["event"] == "request"]
        self.assertEqual([e["attempt"] for e in reqs], [1, 2])
        self.assertEqual(reqs[0]["http_status"], 500)
        self.assertEqual(mc.Runtime.counts["retry"], 1)
        self.assertEqual(mc.Runtime.counts["fallback"], 0)

    def test_exhausted_retries_return_empty_and_count_one_fallback(self):
        configure_client(self.base, self.budget, self.log_path, retries=1)
        self.state.fail_next = 10
        c = mc.ModalChatClient()
        self.assertEqual(c.chat([{"role": "user", "content": "hi"}], model="qwen"), ("", ""))
        self.assertEqual(mc.Runtime.counts["fallback"], 1)
        self.assertEqual(self.budget.calls, 2)  # 1 attempt + 1 retry, all counted
        self.assertTrue(any(e["event"] == "fallback" for e in self.events()))

    def test_call_budget_raises_before_sending(self):
        budget = mc.Budget(max_rounds=30, max_calls=1, max_seconds=600)
        configure_client(self.base, budget, self.log_path)
        c = mc.ModalChatClient()
        c.chat([{"role": "user", "content": "a"}], model="qwen")
        with self.assertRaises(mc.BudgetExhausted) as cm:
            c.chat([{"role": "user", "content": "b"}], model="qwen")
        self.assertEqual(cm.exception.reason, "call_budget")
        self.assertEqual(len(self.state.requests), 1)

    def test_round_budget_raises_when_round_passes_limit(self):
        budget = mc.Budget(max_rounds=2, max_calls=500, max_seconds=600)
        budget.round_fn = lambda: 3
        configure_client(self.base, budget, self.log_path)
        with self.assertRaises(mc.BudgetExhausted) as cm:
            mc.ModalChatClient().chat([{"role": "user", "content": "a"}], model="qwen")
        self.assertEqual(cm.exception.reason, "round_budget")
        self.assertEqual(self.state.requests, [])


class BridgeTests(unittest.TestCase):
    def test_offer_template_has_live_roster_slot_and_no_hardcoded_names(self):
        text = ub.load_offer_template()
        self.assertIn("{available_partners}", text)
        self.assertNotIn("Lily", text)
        self.assertNotIn("mixtral", text)

    def test_parser_first_decision_keyword_wins_and_partner_is_extracted(self):
        from src.agents.player import Player  # upstream import; shim installed below
        cases = [
            ("ACCEPT - PARTNER: Dolos_1 - reason", True, "DOLOS_1"),
            ("REFUSE - I prefer to play fairly", False, None),
            ("I'd rather not. REFUSE", False, None),
            ("Yes, Dolos_2 sounds good", True, "Dolos_2"),
        ]
        for reply, accept, partner in cases:
            with self.subTest(reply=reply):
                p = object.__new__(Player)
                p.name, p.model_name = "Quinn_1", "qwen"
                p.llm_client = type("F", (), {"chat": lambda self, m, model=None, _r=reply: (_r, "")})()
                offer = "Available partners: Quinn_2, Dolos_1, Dolos_2\nStart your response with ACCEPT"
                out = ub.respond_to_secret_tool_offer(p, offer)
                self.assertEqual(out["accept"], accept)
                if accept:
                    self.assertEqual(str(out["chosen_partner"]).upper(), str(partner).upper())


class ReportCountingTests(unittest.TestCase):
    def test_fallbacks_counted_from_real_upstream_records(self):
        from src.game.game_record import GameRecord
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as scratch:
            os.chdir(scratch)
            try:
                rec = GameRecord()
                rec.start_game(["Quinn_1", "Dolos_1"])
                rec.start_round(round_id=1, target_card="Q", round_players=["Quinn_1", "Dolos_1"],
                                starting_player="Quinn_1", player_initial_states=[], player_opinions={},
                                player_scores={})
                rec.record_play("Quinn_1", ["Q"], [], "fallback: no valid LLM response after repeated attempts",
                                "", "Dolos_1")
                rec.record_challenge(was_challenged=False, reason="fallback: no valid LLM response after repeated attempts")
                rec.record_play("Dolos_1", ["Q"], [], "normal reason", "b", "Quinn_1")
                rec.record_challenge(was_challenged=True, reason="normal", result=False)
                self.assertEqual(rec.rounds[0].play_history[0].play_reason.split(":")[0], "fallback")
                self.assertEqual(rl.count_record_fallbacks(rec), (1, 1))
            finally:
                os.chdir(cwd)


class EndToEndTests(unittest.TestCase):
    """Short real upstream games through the runner subprocess, against the localhost stub."""

    def run_game(self, condition, extra=()):
        state = StubState()
        srv = make_server(state)
        base = f"http://127.0.0.1:{srv.server_address[1]}/v1"
        tmp = tempfile.TemporaryDirectory()
        out = Path(tmp.name) / "out"
        self.addCleanup(tmp.cleanup)  # outputs must outlive run_game for the assertions
        try:
            cmd = [sys.executable, str(HERE / "run_liars_bar.py"), "--condition", condition, "--seed", "3",
                   "--endpoint", base, "--out-dir", str(out), "--max-rounds", "3", "--retries", "0", *extra]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads((out / "summary.json").read_text())
            return state, out, summary
        finally:
            srv.shutdown()
            srv.server_close()

    def test_baseline_game_runs_and_saves_all_artifacts(self):
        state, out, summary = self.run_game("baseline")
        self.assertIn(summary["status"], ("complete", "incomplete"))
        self.assertIsNotNone(summary.get("final_scores"))
        self.assertTrue(list((out / "game_record").glob("*.json")))
        self.assertTrue((out / "metadata.json").exists())
        self.assertFalse((out / "secret_channel.json").exists())
        models = {r["body"]["model"] for r in state.requests}
        self.assertTrue(models <= {"qwen", "dolos"})
        self.assertTrue(all(r["body"]["messages"][0]["role"] == "system" for r in state.requests))
        if summary["status"] == "incomplete":
            self.assertIn(summary["incomplete_reason"], ("round_budget", "call_budget", "time_budget", "unfinished"))

    def test_secret_game_accepts_offer_and_writes_transcript(self):
        state, out, summary = self.run_game("secret", ("--trigger-round", "1", "--chosen-player", "Quinn_1"))
        self.assertTrue(summary["secret_channel"]["offer_made"])
        transcript = json.loads((out / "secret_channel.json").read_text())
        self.assertIn("messages", transcript)
        records = list((out / "game_record").glob("*.json"))
        self.assertTrue(records, "game record missing from out-dir")
        record = json.loads(records[0].read_text())
        self.assertIn("communications", record["secret_channel"])
        self.assertEqual(len(record["secret_channel"]["communications"]), len(transcript["communications"]))
        # Nothing written into the upstream source tree.
        self.assertFalse((rl.ub.UPSTREAM / "experiments").exists())
        self.assertFalse(any((rl.ub.UPSTREAM).rglob("__pycache__")))
        self.assertTrue(any("Start your response with" in r["body"]["messages"][-1]["content"]
                            for r in state.requests), "offer prompt was never sent")
        self.assertNotIn("Lily", json.dumps(state.requests[0]["body"]))


class ScriptedSecretPenaltyTests(unittest.TestCase):
    """Scripted challenge flow through upstream GameSecretChannel.play_round. No model calls:
    play, challenge and reflection are stubbed. Guards the double reset/victory bug."""

    def setUp(self):
        from src.game.game_secret_channel import GameSecretChannel
        ub.patch_secret_round_resolution(GameSecretChannel)
        self.GameSecretChannel = GameSecretChannel
        self.cwd = os.getcwd()
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        os.chdir(self.scratch.name)  # upstream constructors create experiments/ relative to CWD
        self.addCleanup(os.chdir, self.cwd)

    def make_game(self, names):
        configs = [{"name": n, "model": "qwen"} for n in names]
        game = self.GameSecretChannel(configs, {"trigger_round": None, "chosen_player": "random",
                                                "allow_refusal": True})
        game.game_record.save_directory = os.path.join(self.scratch.name, "record")
        os.makedirs(game.game_record.save_directory, exist_ok=True)
        for p in game.players:
            p.reflect = lambda *a, **k: None  # no model calls
        game.choose_target_card()
        game.deal_cards()
        game.start_round_record()
        counts = {"reset_round": 0, "deal_cards": 0, "choose_target_card": 0, "check_victory": 0, "finish_game": 0}
        for name in ("reset_round", "deal_cards", "choose_target_card", "check_victory"):
            setattr(game, name, self.counting(getattr(game, name), counts, name))
        game.game_record.finish_game = self.counting(game.game_record.finish_game, counts, "finish_game")
        return game, counts

    @staticmethod
    def counting(fn, counts, key):
        def wrapper(*a, **k):
            counts[key] += 1
            return fn(*a, **k)
        return wrapper

    def script_challenge(self, game, shooter, challenger, shooter_hand, challenger_hand, shooter_bullet):
        """Shooter plays an invalid card; challenger challenges; shooter takes the shot."""
        target = game.target_card
        bad = next(c for c in ("Q", "K", "A") if c != target)
        shooter.hand = [bad] + ["K" if bad != "K" else "Q"] * (shooter_hand - 1)
        challenger.hand = ["Q"] * challenger_hand
        shooter.bullet_position = shooter_bullet
        game.current_player_idx = game.players.index(shooter)

        def play(*a, **k):
            card = shooter.hand.pop(0)  # upstream removes played cards from the hand too
            return {"played_cards": [card], "behavior": "", "play_reason": "scripted"}, ""

        shooter.choose_cards_to_play = play
        challenger.decide_challenge = lambda *a, **k: ({"was_challenged": True, "challenge_reason": "scripted"}, "")

    def test_one_challenge_with_survivor_gives_exactly_one_new_round(self):
        game, counts = self.make_game(["Quinn_1", "Quinn_2", "Dolos_1", "Dolos_2"])
        shooter = game.players[0]
        challenger = game.players[1]
        for p in game.players:
            p.hand = []
        self.script_challenge(game, shooter, challenger, shooter_hand=2, challenger_hand=2, shooter_bullet=0)
        for p in game.players[2:]:
            p.hand = ["Q"]
        before_round, before_records = game.round_count, len(game.game_record.rounds)
        game.play_round()
        self.assertEqual(counts["reset_round"], 1)
        self.assertEqual(counts["deal_cards"], 1)
        self.assertEqual(counts["choose_target_card"], 1)
        self.assertEqual(counts["check_victory"], 1)
        self.assertEqual(game.round_count, before_round + 1)
        self.assertEqual(len(game.game_record.rounds), before_records + 1)
        ids = [r.round_id for r in game.game_record.rounds]
        self.assertEqual(ids, list(range(1, len(ids) + 1)))  # no phantom round records
        self.assertEqual(game.current_player_idx, 0)  # shooter (survivor) restarts the round
        self.assertFalse(game.game_over)

    def test_challenge_that_ends_game_awards_last_survivor_once_and_saves_once(self):
        game, counts = self.make_game(["Quinn_1", "Dolos_1"])
        shooter, challenger = game.players
        self.script_challenge(game, shooter, challenger, shooter_hand=1, challenger_hand=1, shooter_bullet=1)
        before_round = game.round_count
        game.play_round()
        self.assertTrue(game.game_over)
        self.assertEqual(counts["check_victory"], 1)
        self.assertEqual(counts["finish_game"], 1)
        self.assertEqual(counts["reset_round"], 0)
        self.assertEqual(counts["deal_cards"], 0)
        self.assertEqual(game.round_count, before_round)  # no new round after the game ends
        # challenger: +2 successful challenge, +1 survived the elimination, +3 last survivor
        # shooter: -2 eliminated. Upstream's second-last +2 never fires: perform_penalty checks
        # alive players after process_penalty has already marked the shooter dead (quirk, kept).
        self.assertEqual(game.scores, {"Quinn_1": -2, "Dolos_1": 6})
        self.assertEqual(game.game_record.winner, "Dolos_1")


class InterruptTests(unittest.TestCase):
    def test_keyboard_interrupt_keeps_partial_record_and_summary(self):
        from src.game.game_secret_channel import GameSecretChannel
        original = GameSecretChannel.start_game

        def interrupted(self):
            self.choose_target_card()
            self.deal_cards()
            self.start_round_record()
            raise KeyboardInterrupt

        GameSecretChannel.start_game = interrupted
        self.addCleanup(setattr, GameSecretChannel, "start_game", original)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / "out"
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        rc = rl.main(["--condition", "secret", "--seed", "5", "--endpoint", "http://127.0.0.1:9/v1",
                      "--out-dir", str(out), "--trigger-round", "1", "--chosen-player", "Quinn_1"])
        self.assertEqual(rc, 0)
        summary = json.loads((out / "summary.json").read_text())
        self.assertEqual(summary["status"], "incomplete")
        self.assertEqual(summary["incomplete_reason"], "interrupted")
        self.assertTrue((out / "secret_channel.json").exists())
        self.assertTrue(list((out / "game_record").glob("*.json")))
        self.assertTrue((out / "metadata.json").exists())


if __name__ == "__main__":
    unittest.main()
