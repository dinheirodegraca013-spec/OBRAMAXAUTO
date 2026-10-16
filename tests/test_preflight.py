import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from run_agent import ensure_branch, validate_scope, acceptance_gate


class PreflightTests(unittest.TestCase):
    def _repo(self, root):
        repo = root / "app"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "AGENTS.md").write_text("# regras\\n", encoding="utf-8")
        (repo / "ESCOPO.md").write_text(
            "# Escopo\\n" + "Requisitos aprovados e ambiente DEV definido. " * 8,
            encoding="utf-8",
        )
        return repo

    def test_scope_placeholder_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._repo(root)
            (repo / "ESCOPO.md").write_text(
                "# ESCOPO DO PROJETO\\n- RF-001 — [descrever] — aceite: [teste reproduzível]\\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "modelo ou está incompleto"):
                validate_scope(repo)

    def test_dry_run_does_not_create_branch_or_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            before = subprocess.run(
                ["git", "-C", str(repo), "branch", "--show-current"],
                capture_output=True, text=True, check=True,
            ).stdout
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "run_agent.py"), "--target", str(repo), "--dry-run"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            after = subprocess.run(
                ["git", "-C", str(repo), "branch", "--show-current"],
                capture_output=True, text=True, check=True,
            ).stdout
            self.assertEqual(after, before)
            self.assertFalse((repo / ".obramaxauto").exists())
            self.assertNotIn(".obramaxauto/", (repo / ".git/info/exclude").read_text(encoding="utf-8"))

    def test_existing_state_cannot_resume_on_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            with self.assertRaisesRegex(ValueError, "não autorizada"):
                ensure_branch(repo, {"branch": "main"})

    def test_gate_rejects_pass_word_without_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "ACEITE.md").write_text("- [x] requisito\\n", encoding="utf-8")
            (repo / "TESTES.md").write_text("O teste poderia dar PASS, mas não foi executado.\\n", encoding="utf-8")
            (repo / "AUDITORIA.md").write_text("Parecer final: PASS\\n", encoding="utf-8")
            self.assertFalse(acceptance_gate(repo)[0])


if __name__ == "__main__":
    unittest.main()
