import argparse
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_agent import parse_status, acceptance_gate, build_prompt


class RunnerTests(unittest.TestCase):
    def test_status_last_valid_line(self):
        self.assertEqual(parse_status("STATUS: CONTINUE\nobservação\nSTATUS: READY\n"), "READY")

    def test_status_ignores_informal_words(self):
        self.assertEqual(parse_status("ready, tudo ok\n"), "UNKNOWN")
        self.assertEqual(parse_status("STATUS: INDEFINIDO\n"), "UNKNOWN")

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
