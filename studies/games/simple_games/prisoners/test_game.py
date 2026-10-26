import unittest

from .game import run_game


class Scripted:
    def __init__(self, choices, chat=None):
        self.choices = iter(choices)
        self.chat = iter(chat or [])
        self.calls = []

    def __call__(self, model, messages, metadata):
        self.calls.append((model, messages, metadata))
        if metadata["phase"] == "conversation":
            return next(self.chat, f"message-{metadata['seat']}-{metadata['exchange']}")
        return next(self.choices)


def config(**overrides):
    values = {"pairing": "DQ", "rounds": 1, "exchanges": 0, "seed": 7}
    values.update(overrides)
    return values


class PrisonersGameTests(unittest.TestCase):
    def test_payoff_matrix_exact(self):
        cases = [
            (["COOPERATE", "COOPERATE"], [1, 1]),
            (["BETRAY", "BETRAY"], [0, 0]),
            (["BETRAY", "COOPERATE"], [2, -1]),
            (["COOPERATE", "BETRAY"], [-1, 2]),
        ]
        for actions, expected in cases:
            result = run_game(config(), Scripted(actions))
            self.assertEqual(result["rounds"][0]["payoffs"], expected)

    def test_sucker_payoff_override_and_rates(self):
        result = run_game(config(sucker_payoff=-1), Scripted(["BETRAY", "COOPERATE"]))
        self.assertEqual(result["rounds"][0]["payoffs"], [2, -1])
        self.assertEqual(result["summary"]["mutual_cooperation_rate"], 0.0)

    def test_default_sucker_payoff_and_one_shot_only(self):
        result = run_game(config(), Scripted(["COOPERATE", "COOPERATE"]))
        self.assertEqual(result["config"]["sucker_payoff"], -1)
        with self.assertRaisesRegex(ValueError, "requires rounds=1"):
            run_game(config(rounds=2), Scripted([]))

    def test_invalid_is_logged_and_unscored(self):
        result = run_game(config(), Scripted(["I choose COOPERATE because...", "BETRAY"]))
        self.assertEqual(result["status"], "failed_invalid_action")
        self.assertIsNone(result["rounds"][0]["payoffs"])
        self.assertFalse(result["rounds"][0]["actions"][0]["valid"])
        self.assertEqual(result["rounds"][0]["actions"][0]["raw"], "I choose COOPERATE because...")

    def test_wrapped_canonical_action(self):
        result = run_game(config(), Scripted(["<ACTION>BETRAY</ACTION>", "COOPERATE"]))
        self.assertEqual(result["rounds"][0]["payoffs"], [2, -1])

    def test_chat_precedes_decisions_and_both_see_same_chat(self):
        scripted = Scripted(["COOPERATE", "BETRAY"], chat=["hello from first", "hello from second"])
        result = run_game(config(exchanges=1), scripted)
        calls = scripted.calls
        self.assertEqual([c[2]["phase"] for c in calls], ["conversation", "conversation", "decision", "decision"])
        decisions = [c for c in calls if c[2]["phase"] == "decision"]
        for decision in decisions:
            content = str(decision[1])
            self.assertIn("hello from first", content)
            self.assertIn("hello from second", content)
        self.assertEqual(len(result["rounds"][0]["conversation"]), 2)
        self.assertTrue(all(not any(name in m["content"].lower() for name in ("dolos", "qwen")) for c in calls for m in c[1] if m["role"] == "system"))

    def test_every_request_has_payoff_table_seat_task_and_chat_instruction(self):
        for exchanges in (0, 1):
            scripted = Scripted(["I intend to cooperate", "I intend to betray", "BETRAY", "COOPERATE"] if exchanges else ["BETRAY", "COOPERATE"])
            run_game(config(exchanges=exchanges), scripted)
            for _, messages, metadata in scripted.calls:
                self.assertEqual(messages[0]["role"], "system")
                self.assertEqual(messages[-1]["role"], "user")  # every call ends with the actual task
                task = messages[-1]["content"]
                self.assertIn("Payoff table", task)
                self.assertIn("Your BETRAY", task)
                self.assertIn("Your COOPERATE", task)
                self.assertIn(f"You are seat {metadata['seat']}", task)
                self.assertIn("maximize your own points", task)
                if metadata["phase"] == "conversation":
                    self.assertIn("intended choices, and promises", task)
                    self.assertIn("Do not submit your final choice", task)

    def test_chat_may_include_intended_choice_but_final_choices_stay_private(self):
        scripted = Scripted(["BETRAY", "COOPERATE"], chat=["I promise COOPERATE", "I plan BETRAY"])
        run_game(config(exchanges=1), scripted)
        decision_calls = [call for call in scripted.calls if call[2]["phase"] == "decision"]
        self.assertTrue(all("I promise COOPERATE" in str(call[1]) and "I plan BETRAY" in str(call[1]) for call in decision_calls))
        self.assertFalse(any("BETRAY\n" in message["content"] for call in decision_calls for message in call[1] if message["role"] == "user" and "Payoff table" not in message["content"]))

    def test_no_chat_calls_when_exchanges_zero(self):
        no_chat = Scripted(["COOPERATE", "COOPERATE"])
        run_game(config(exchanges=0), no_chat)
        self.assertTrue(all(c[2]["phase"] == "decision" for c in no_chat.calls))

    def test_private_current_action_never_leaks(self):
        scripted = Scripted(["COOPERATE", "BETRAY"])
        run_game(config(), scripted)
        for _, messages, _ in scripted.calls:
            self.assertFalse(any("current action" in m["content"].lower() and "COOPERATE" in m["content"] for m in messages[1:]))


if __name__ == "__main__":
    unittest.main()
