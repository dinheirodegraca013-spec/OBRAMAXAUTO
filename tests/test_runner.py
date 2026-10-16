import argparse
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_agent import parse_status, acceptance_gate, build_prompt, run_cycle


class RunnerTests(unittest.TestCase):
    def test_status_last_valid_line(self):
        self.assertEqual(parse_status("STATUS: CONTINUE\nobservação\nSTATUS: READY\n"), "READY")

    def test_status_ignores_informal_words(self):
        self.assertEqual(parse_status("ready, tudo ok\n"), "UNKNOWN")
        self.assertEqual(parse_status("STATUS: INDEFINIDO\n"), "UNKNOWN")

    def test_status_only_valid_on_final_nonblank_line(self):
        self.assertEqual(parse_status("STATUS: READY\nMas não terminou.\n"), "UNKNOWN")
        self.assertEqual(parse_status("STATUS: READY\nSTATUS: CONTINUE\n"), "CONTINUE")
        self.assertEqual(parse_status("O texto cita STATUS: READY\n"), "UNKNOWN")
        self.assertEqual(parse_status("STATUS: BLOCKED\n\n"), "BLOCKED")

    def test_run_cycle_ignores_stale_status_file(self):
        import stat
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            fake = target / "codex-fake.py"
            fake.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            output = target / "cycle-00001-last.txt"
            output.write_text("STATUS: READY\n", encoding="utf-8")
            code, status, log = run_cycle(str(fake), target, target, 1, 10)
            self.assertEqual(code, 0)
            self.assertEqual(status, "UNKNOWN")
            self.assertFalse(output.exists())
            self.assertTrue(Path(log).exists())

    def test_run_cycle_discards_status_on_failure(self):
        import stat
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            fake = target / "codex-fake.py"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "p = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])\n"
                "p.write_text('STATUS: READY\\n')\n"
                "sys.exit(2)\n", encoding="utf-8"
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            code, status, _ = run_cycle(str(fake), target, target, 1, 10)
            self.assertEqual(code, 2)
            self.assertEqual(status, "UNKNOWN")

    def test_gate_rejects_unchecked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ACEITE.md").write_text("- [ ] tarefa\n", encoding="utf-8")
            (root / "TESTES.md").write_text("PASS\n", encoding="utf-8")
            (root / "AUDITORIA.md").write_text("Parecer final: PASS\n", encoding="utf-8")
            self.assertFalse(acceptance_gate(root)[0])

    def test_gate_accepts_documented_finish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ACEITE.md").write_text("- [x] requisito\n", encoding="utf-8")
            (root / "TESTES.md").write_text("Caso 1: PASS\n", encoding="utf-8")
            (root / "AUDITORIA.md").write_text("Parecer final: PASS\n", encoding="utf-8")
            self.assertTrue(acceptance_gate(root)[0])

    def test_prompt_has_constraints(self):
        prompt = build_prompt(Path("/tmp/sample"), 3)
        self.assertIn("STATUS: BLOCKED", prompt)
        self.assertIn("Não faça push", prompt)


if __name__ == "__main__":
    unittest.main()
