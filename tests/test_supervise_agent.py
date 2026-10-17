import argparse
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import supervise_agent


def config(target):
    return argparse.Namespace(target=str(target), max_hours=2,
        hours_per_session=0.1, cycles_per_session=2,
        max_sessions=4, cooldown=0, queue=True, worktree=True,
        verify_command="python -m unittest discover -s tests")


class SupervisorTests(unittest.TestCase):
    def test_continues_only_after_limit_and_stops_for_review(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            commands = []
            def invoke(cmd, **kw):
                commands.append(cmd)
                n = len(commands)
                result = dict(total_cycles=n,
                    last_exit_reason="LIMIT_REACHED" if n == 1 else "TASK_REVIEW")
                (target / ".obramaxauto" / "runner-state.json").write_text(
                    json.dumps(result), encoding="utf-8")
                return SimpleNamespace(returncode=1 if n == 1 else 0)
            with patch.object(supervise_agent, "verify_target", return_value=target):
                self.assertEqual(supervise_agent.supervise(
                    config(target), invoke=invoke, sleeper=lambda _: None), 0)
            self.assertEqual(len(commands), 2)
            self.assertIn("--queue", commands[0])
            self.assertIn("--worktree", commands[0])
            events = (target / ".obramaxauto" / "supervisor-history.jsonl").read_text()
            self.assertEqual(len(events.splitlines()), 2)

    def test_never_retries_blocked_or_stagnant_result(self):
        for reason in ("NO_PROGRESS", "QUEUE_BLOCKED", "BLOCKED", "LIMIT_REACHED"):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder:
                target = Path(folder)
                calls = []
                def invoke(cmd, **kw):
                    calls.append(cmd)
                    (target / ".obramaxauto" / "runner-state.json").write_text(
                        json.dumps(dict(total_cycles=0, last_exit_reason=reason)),
                        encoding="utf-8")
                    return SimpleNamespace(returncode=1)
                with patch.object(supervise_agent, "verify_target", return_value=target):
                    self.assertEqual(supervise_agent.supervise(
                        config(target), invoke=invoke, sleeper=lambda _: None), 1)
                self.assertEqual(len(calls), 1)

    def test_does_not_resume_interrupted_cycle_automatically(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            state = target / ".obramaxauto"
            state.mkdir()
            (state / "runner-state.json").write_text(
                json.dumps(dict(total_cycles=3, inflight={"cycle": 4})),
                encoding="utf-8")
            with patch.object(supervise_agent, "verify_target", return_value=target):
                self.assertEqual(supervise_agent.supervise(
                    config(target), invoke=lambda *a, **kw: self.fail("executou"),
                    sleeper=lambda _: None), 1)

    def test_terminal_state_is_not_restarted(self):
        for reason in ("TASK_REVIEW", "READY_FOR_HUMAN_REVIEW", "BLOCKED", "NO_PROGRESS", "QUEUE_BLOCKED"):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder:
                target = Path(folder)
                state = target / ".obramaxauto"
                state.mkdir()
                (state / "runner-state.json").write_text(
                    json.dumps(dict(total_cycles=3, last_exit_reason=reason)), encoding="utf-8")
                with patch.object(supervise_agent, "verify_target", return_value=target):
                    self.assertEqual(supervise_agent.supervise(
                        config(target), invoke=lambda *a, **kw: self.fail("executou"),
                        sleeper=lambda _: None), 1)

    def test_stop_file_prevents_any_session(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            state = target / ".obramaxauto"
            state.mkdir()
            (state / "STOP").touch()
            with patch.object(supervise_agent, "verify_target", return_value=target):
                self.assertEqual(supervise_agent.supervise(
                    config(target), invoke=lambda *a, **kw: self.fail("executou"),
                    sleeper=lambda _: None), 0)


if __name__ == "__main__":
    unittest.main()
