import argparse
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_agent import parse_status, acceptance_gate, build_prompt, run_cycle, fingerprint, acquire_lock, verify_task


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

    def test_progress_ignores_housekeeping_only(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "app.py"], check=True)
            subprocess.run([
                "git", "-C", str(root), "-c", "user.name=Test",
                "-c", "user.email=test@example.invalid", "commit", "-qm", "init"
            ], check=True)
            baseline = fingerprint(root)
            (root / "ESTADO.md").write_text("Ciclo 1\n", encoding="utf-8")
            (root / "BACKLOG.md").write_text("Próximo\n", encoding="utf-8")
            self.assertEqual(baseline, fingerprint(root))
            (root / "ESTADO.md").write_text("Ciclo 2\n", encoding="utf-8")
            self.assertEqual(baseline, fingerprint(root))
            (root / "app.py").write_text("print('corrigido')\n", encoding="utf-8")
            self.assertNotEqual(baseline, fingerprint(root))

    def test_progress_counts_new_project_files_not_reports(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            baseline = fingerprint(root)
            (root / "TESTES.md").write_text("Testes planejados\n", encoding="utf-8")
            self.assertEqual(baseline, fingerprint(root))
            (root / "src").mkdir()
            (root / "src" / "new.py").write_text("answer = 42\n", encoding="utf-8")
            self.assertNotEqual(baseline, fingerprint(root))

    def test_lock_blocks_concurrent_runner_and_recovers_after_close(self):
        with tempfile.TemporaryDirectory() as temp:
            lockfile = Path(temp) / "runner.lock"
            first = acquire_lock(lockfile)
            try:
                with self.assertRaisesRegex(RuntimeError, "Outro runner"):
                    acquire_lock(lockfile)
            finally:
                first.close()
            # O arquivo permanece no disco, mas a trava termina ao fechar.
            self.assertTrue(lockfile.exists())
            second = acquire_lock(lockfile)
            second.close()

    def test_lock_recovers_from_stale_pid_file(self):
        with tempfile.TemporaryDirectory() as temp:
            lockfile = Path(temp) / "runner.lock"
            lockfile.write_text("PID=999999999\\n", encoding="utf-8")
            handle = acquire_lock(lockfile)
            try:
                self.assertIn("PID=", lockfile.read_text(encoding="utf-8"))
            finally:
                handle.close()

    def test_gate_requires_operator_command(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(verify_task(Path(folder), None))
            with self.assertRaises(ValueError):
                verify_task(Path(folder), "sh -c true")
            with self.assertRaises(ValueError):
                verify_task(Path(folder), "python -c print(1)")

    def test_prompt_has_constraints(self):
        prompt = build_prompt(Path("/tmp/sample"), 3)
        self.assertIn("STATUS: BLOCKED", prompt)
        self.assertIn("Não faça push", prompt)


if __name__ == "__main__":
    unittest.main()
