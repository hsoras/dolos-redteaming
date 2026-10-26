import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import modal_supervisor as ms

ROWS = [
    {"App ID": "ap-AAAAAAAA11", "Description": "simple-games-x", "State": "deployed"},
    {"App ID": "ap-BBBBBBBB22", "Description": "dolos-qwen-vllm", "State": "deployed"},
    {"App ID": "ap-CCCCCCCC33", "Description": "simple-games-x", "State": "stopped"},
]


class T(unittest.TestCase):
    def test_parse_ids_urls(self):
        t = "created ap-AAAAAAAA11 and fu-123; https://ws--simple-games-x-serve.modal.run."
        self.assertEqual(ms.parse_app_ids(t), ["ap-AAAAAAAA11"])
        self.assertEqual(ms.parse_urls(t), ["https://ws--simple-games-x-serve.modal.run"])

    def test_owned_app(self):
        self.assertEqual(ms.find_owned_app(ROWS, "simple-games-x", ["ap-AAAAAAAA11"])["id"], "ap-AAAAAAAA11")
        with self.assertRaises(RuntimeError):
            ms.find_owned_app(ROWS, "simple-games-x", ["ap-BBBBBBBB22"])
        with self.assertRaises(RuntimeError):
            ms.find_owned_app(ROWS, "nope")

    def test_is_stopped(self):
        self.assertTrue(ms.is_stopped(ROWS, "ap-CCCCCCCC33"))
        self.assertFalse(ms.is_stopped(ROWS, "ap-AAAAAAAA11"))
        self.assertTrue(ms.is_stopped(ROWS, "ap-ZZZZZZZZ99"))

    def test_names_and_budget(self):
        ms.validate_app_name("simple-games-20261025-010203")
        for bad in ("dolos-qwen-vllm", "Bad_Name", "x"):
            with self.assertRaises(ValueError):
                ms.validate_app_name(bad)
        self.assertLess(ms.reserve_usd(3000), 5.2)
        self.assertLess(ms.reserve_usd(ms.MAX_SECONDS_CEILING), 10)

    def test_env_cmd_url(self):
        e = ms.deploy_env({"A": "1"}, "n-name-1")
        self.assertEqual((e["MODAL_GPU"], e["MODAL_MAX_CONTAINERS"], e["MAX_MODEL_LEN"]), ("H100", "1", "16384"))
        c = ms.runner_cmd("py", "https://u", "/o", 48)
        self.assertIn("https://u/v1", c)
        self.assertEqual(c[c.index("--concurrency") + 1], "48")
        self.assertEqual(ms.pick_web_url("https://a/", [], "x"), "https://a")
        self.assertEqual(ms.pick_web_url(None, ["https://q--x-serve.modal.run"], "x"), "https://q--x-serve.modal.run")


def write_run(d, planned, recs, manifest_episodes=None):
    d = Path(d)
    (d / "manifest.json").write_text(json.dumps({"episodes": planned if manifest_episodes is None else manifest_episodes}))
    (d / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    return d


class Config(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def parse(self, *extra):
        # Fresh, nonexistent run-output and ready-marker paths so only the flags under test matter.
        argv = ["--out", str(self.dir / "meta"), "--ready-marker", str(self.dir / "ready"),
                "--run-output", str(self.dir / "run"), "--app-name", "simple-games-test-1", *extra]
        with contextlib.redirect_stderr(io.StringIO()):
            return ms.parse_config(argv)

    def test_defaults_match_old_sweep(self):
        a = self.parse()
        self.assertEqual(a.games, ["prisoners", "door_relay"])
        self.assertEqual(a.exchanges, [1, 3, 5])
        self.assertEqual(a.episodes, 10)
        self.assertEqual(a.max_model_len, 16384)

    def test_overrides_parse(self):
        a = self.parse("--games", "door_relay", "--exchanges", "20", "50", "--episodes", "10",
                       "--max-model-len", "32768")
        self.assertEqual(a.games, ["door_relay"])
        self.assertEqual(a.exchanges, [20, 50])
        self.assertEqual(a.max_model_len, 32768)

    def test_existing_run_defaults_none_and_validates_dir(self):
        self.assertIsNone(self.parse().existing_run)
        existing = self.dir / "prior"
        existing.mkdir()
        self.assertEqual(self.parse("--existing-run", str(existing)).existing_run, existing)
        with self.assertRaises(SystemExit):
            self.parse("--existing-run", str(self.dir / "missing"))

    def test_invalid_values_rejected(self):
        for bad in (["--games", "chess"], ["--episodes", "0"], ["--exchanges", "-1"],
                    ["--max-model-len", "8192"]):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                self.parse(*bad)

    def test_state_records_config(self):
        a = self.parse("--exchanges", "20", "50", "--max-model-len", "32768")
        sup = ms.Supervisor(a)
        self.addCleanup(sup.log_f.close)
        cfg = sup.state["config"]
        self.assertEqual((cfg["games"], cfg["exchanges"], cfg["episodes"]),
                         (["prisoners", "door_relay"], [20, 50], 10))
        self.assertEqual((cfg["max_model_len"], sup.state["max_model_len"]), (32768, 32768))
        self.assertEqual(cfg["pairings"], ["DD", "QQ", "DQ", "QD"])


class Forwarding(unittest.TestCase):
    def test_runner_cmd_default_is_old_sweep(self):
        c = ms.runner_cmd("py", "https://u", "/o", 48)
        self.assertEqual(c[c.index("--games") + 1:c.index("--games") + 3], ["prisoners", "door_relay"])
        self.assertEqual(c[c.index("--exchanges") + 1:c.index("--exchanges") + 4], ["1", "3", "5"])
        self.assertEqual(c[c.index("--episodes") + 1], "10")
        self.assertEqual(c[c.index("--max-calls") + 1], "3000")

    def test_runner_cmd_forwards_overrides(self):
        c = ms.runner_cmd("py", "https://u", "/o", 48, 512, 9000, games=["door_relay"], exchanges=[20, 50],
                          episodes=7)
        self.assertEqual(c[c.index("--games") + 1], "door_relay")
        self.assertEqual(c[c.index("--games") + 2], "--episodes")  # only one game, no leakage of defaults
        self.assertEqual(c[c.index("--exchanges") + 1:c.index("--exchanges") + 3], ["20", "50"])
        self.assertEqual(c[c.index("--episodes") + 1], "7")
        self.assertEqual(c[c.index("--max-calls") + 1], "9000")
        self.assertEqual(c[c.index("--pairings") + 1:c.index("--pairings") + 5], ["DD", "QQ", "DQ", "QD"])

    def test_existing_run_forwarded_only_when_set(self):
        self.assertNotIn("--existing-run", ms.runner_cmd("py", "https://u", "/o", 48))
        c = ms.runner_cmd("py", "https://u", "/o", 48, existing_run="/prior/run")
        self.assertEqual(c[c.index("--existing-run") + 1], "/prior/run")
        self.assertEqual(c[c.index("--out") + 1], "/o")

    def test_deploy_env_model_len(self):
        self.assertEqual(ms.deploy_env({"A": "1"}, "n-name-1")["MAX_MODEL_LEN"], "16384")
        self.assertEqual(ms.deploy_env({}, "n-name-1", 32768)["MAX_MODEL_LEN"], "32768")
        self.assertEqual(ms.deploy_env({}, "n-name-1", 32768)["MODAL_GPU"], "H100")


class Outcome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def rec(self, i, status):
        return {"job_index": i, "status": status}

    def test_clean_exit_is_finished(self):
        self.assertEqual(ms.classify_run(0, self.dir), "finished")

    def test_invalid_only_is_completed_with_invalid(self):
        d = write_run(self.dir, 3, [self.rec(0, "completed"), self.rec(1, "invalid_action"),
                                    self.rec(2, "failed_invalid_action")])
        self.assertEqual(ms.classify_run(1, d), "completed_with_invalid")

    def test_http_error_is_runner_failed(self):
        d = write_run(self.dir, 2, [self.rec(0, "completed"), self.rec(1, "error")])
        self.assertEqual(ms.classify_run(1, d), "runner_failed")

    def test_exception_mixed_with_invalid_is_runner_failed(self):
        d = write_run(self.dir, 3, [self.rec(0, "invalid_action"), self.rec(1, "failed_exception"),
                                    self.rec(2, "completed")])
        self.assertEqual(ms.classify_run(1, d), "runner_failed")

    def test_missing_planned_episode_is_runner_failed(self):
        d = write_run(self.dir, 3, [self.rec(0, "invalid_action"), self.rec(1, "completed")])
        self.assertEqual(ms.classify_run(1, d), "runner_failed")

    def test_no_records_is_runner_failed(self):
        self.assertEqual(ms.classify_run(1, self.dir / "absent"), "runner_failed")

    def test_zero_records_with_nonzero_exit_is_runner_failed(self):
        d = write_run(self.dir, 0, [])
        self.assertEqual(ms.classify_run(1, d), "runner_failed")


if __name__ == "__main__":
    unittest.main()
