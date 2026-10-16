import argparse
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_agent import parse_status, acceptance_gate, build_prompt, run_cycle, fingerprint, acquire_lock, verify_task, write_cycle_evidence, prepare_worktree


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

    @unittest.skipIf(sys.platform == "win32", "Teste de grupo de processos POSIX")
    def test_timeout_kills_descendant_process(self):
        import os
        import stat
        import time
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            agent = root / "fake-agent.py"
            pidfile = root / "child.pid"
            agent.write_text(
                "#!/usr/bin/env python3\n"
                "import subprocess,sys,time,pathlib\n"
                "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)'])\n"
                "pathlib.Path('child.pid').write_text(str(child.pid))\n"
                "time.sleep(120)\n", encoding="utf-8")
            agent.chmod(agent.stat().st_mode | stat.S_IXUSR)
            rc,status,_ = run_cycle(str(agent), root, root, 1, 1)
            self.assertEqual((rc,status),(124,"UNKNOWN"))
            self.assertTrue(pidfile.exists())
            pid=int(pidfile.read_text())
            # Em Linux, descendentes mortos podem estar zumbis ou já recolhidos.
            if sys.platform.startswith("linux"):
                state_file = Path(f"/proc/{pid}/stat")
                state = state_file.read_text().split()[2] if state_file.exists() else "gone"
                self.assertIn(state, {"Z", "gone"})
            else:
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)

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

    def test_queue_ready_without_verified_tests_does_not_end_project(self):
        # O runner deve impedir que READY encerre a fila quando o gate falhar.
        from unittest.mock import patch
        import argparse
        import subprocess
        import run_agent
        from task_queue import add, save as save_queue, load as load_queue
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "AGENTS.md").write_text("# Regras", encoding="utf-8")
            (root / "ESCOPO.md").write_text("Requisito aceito. " * 25, encoding="utf-8")
            state_dir = root / ".obramaxauto"
            state_dir.mkdir()
            q = {"version": 1, "tasks": []}
            add(q, "RF-01", "Implementar", [])
            save_queue(state_dir / "tasks.json", q)
            args = argparse.Namespace(target=str(root), dry_run=False, queue=True, worktree=False,
                max_cycles=1, max_hours=1, cycle_timeout=10, cooldown=0,
                max_errors=3, max_stagnant=3, max_task_attempts=3,
                verify_command=None)
            def fake_cycle(codex, target, logdir, cycle, timeout, task):
                (target / "app.py").write_text("print('ok')", encoding="utf-8")
                return 0, "READY", str(logdir / "cycle-00001.log")
            with patch.object(run_agent.shutil, "which", return_value="/usr/bin/fake-codex"):
                with patch.object(run_agent, "run_cycle", side_effect=fake_cycle):
                    self.assertEqual(run_agent.loop(args), 1)
            saved = load_queue(state_dir / "tasks.json")
            self.assertEqual(saved["tasks"][0]["status"], "pending")
            self.assertNotEqual(
                run_agent.load_state(state_dir / "runner-state.json")["last_exit_reason"],
                "READY_FOR_HUMAN_REVIEW")

    def test_cycle_evidence_records_verification_without_log_contents(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            record = {"cycle": 7, "date": "2026-10-16T00:00:00Z",
                      "status": "CONTINUE", "returncode": 0,
                      "progressed": True, "log": "cycle-00007.log"}
            task = {"id": "RF-007", "verification_passed": False}
            evidence = write_cycle_evidence(base, record, task)
            saved = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(saved["task_id"], "RF-007")
            self.assertEqual(saved["log_file"], "cycle-00007.log")
            self.assertFalse(saved["tests_verified"])
            self.assertTrue(saved["review_required"])
            self.assertFalse(evidence.with_suffix(".tmp").exists())

    def test_worktree_isolates_source_and_supports_resume(self):
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "project"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "AGENTS.md").write_text("# Regras\n", encoding="utf-8")
            (repo / "ESCOPO.md").write_text("Escopo aprovado. " * 25, encoding="utf-8")
            (repo / "app.py").write_text("original = 1\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test",
                            "-c", "user.email=test@example.invalid",
                            "commit", "-qm", "base"], check=True)
            state_dir = repo / ".obramaxauto"
            state_dir.mkdir()
            with (repo / ".git" / "info" / "exclude").open("a") as file:
                file.write("\n.obramaxauto/\n")
            original_branch = subprocess.check_output(
                ["git", "-C", str(repo), "branch", "--show-current"], text=True).strip()
            state = {}
            isolated = prepare_worktree(repo, state, state_dir)
            self.assertEqual(isolated, prepare_worktree(repo, state, state_dir))
            self.assertTrue(state["branch"].startswith("obramax/"))
            (isolated / "app.py").write_text("changed = 2\n", encoding="utf-8")
            self.assertEqual((repo / "app.py").read_text(encoding="utf-8"), "original = 1\n")
            self.assertEqual(subprocess.check_output(
                ["git", "-C", str(repo), "branch", "--show-current"],
                text=True).strip(), original_branch)
            self.assertEqual(subprocess.check_output(
                ["git", "-C", str(repo), "status", "--porcelain"], text=True).strip(), "")

    def test_worktree_refuses_dirty_original_and_path_tampering(self):
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "project"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "AGENTS.md").write_text("# regras", encoding="utf-8")
            (repo / "ESCOPO.md").write_text("Escopo aprovado. " * 25, encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test",
                            "-c", "user.email=test@example.invalid",
                            "commit", "-qm", "base"], check=True)
            state_dir = repo / ".obramaxauto"
            state_dir.mkdir()
            (repo / ".git" / "info" / "exclude").write_text(".obramaxauto/\n", encoding="utf-8")
            (repo / "AGENTS.md").write_text("modified", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "limpo"):
                prepare_worktree(repo, {}, state_dir)
            (repo / "AGENTS.md").write_text("# regras", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fora do diretório"):
                prepare_worktree(repo, {"worktree_path": str(repo.parent)}, state_dir)

    def test_queue_continues_unrelated_tasks_while_review_pending(self):
        import argparse
        import subprocess
        from unittest.mock import patch
        import run_agent
        from task_queue import add, load as load_queue, save as save_queue
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "AGENTS.md").write_text("# regras", encoding="utf-8")
            (repo / "ESCOPO.md").write_text("Escopo válido. " * 30, encoding="utf-8")
            state_dir = repo / ".obramaxauto"
            state_dir.mkdir()
            queue = {"version": 1, "tasks": []}
            add(queue, "A", "Criar API", [])
            add(queue, "B", "Criar frontend", [])
            add(queue, "C", "Conectar API ao frontend", ["A"])
            save_queue(state_dir / "tasks.json", queue)
            args = argparse.Namespace(target=str(repo), dry_run=False, queue=True,
                worktree=False, max_cycles=3, max_hours=1, cycle_timeout=10,
                cooldown=0, max_errors=3, max_stagnant=3, max_task_attempts=3,
                verify_command="python -m unittest discover -s tests")
            executed = []
            def fake_cycle(codex, target, logdir, cycle, timeout, task):
                executed.append(task["id"])
                (target / (task["id"] + ".py")).write_text("change", encoding="utf-8")
                return 0, "READY", str(logdir / "test.log")
            with patch.object(run_agent.shutil, "which", return_value="codex"):
                with patch.object(run_agent, "run_cycle", side_effect=fake_cycle):
                    with patch.object(run_agent, "verify_task", return_value=True):
                        self.assertEqual(run_agent.loop(args), 0)
            self.assertEqual(executed, ["A", "B"])
            states = {task["id"]: task["status"] for task in load_queue(state_dir / "tasks.json")["tasks"]}
            self.assertEqual(states, {"A": "review", "B": "review", "C": "pending"})

    def test_queue_skips_exhausted_task_and_handles_independent_blocked(self):
        import argparse
        import subprocess
        from unittest.mock import patch
        import run_agent
        from task_queue import add, load as load_queue, save as save_queue
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "AGENTS.md").write_text("# regras", encoding="utf-8")
            (repo / "ESCOPO.md").write_text("Escopo válido. " * 30, encoding="utf-8")
            state_dir = repo / ".obramaxauto"
            state_dir.mkdir()
            queue = {"version": 1, "tasks": []}
            add(queue, "A", "Esgotada", [])
            add(queue, "B", "Independente", [])
            queue["tasks"][0]["attempts"] = 3
            save_queue(state_dir / "tasks.json", queue)
            args = argparse.Namespace(target=str(repo), dry_run=False, queue=True,
                worktree=False, max_cycles=3, max_hours=1, cycle_timeout=10,
                cooldown=0, max_errors=3, max_stagnant=3, max_task_attempts=3,
                verify_command=None)
            executed = []
            def fake_cycle(codex, target, logdir, cycle, timeout, task):
                executed.append(task["id"])
                return 0, "BLOCKED", str(logdir / "test.log")
            with patch.object(run_agent.shutil, "which", return_value="codex"):
                with patch.object(run_agent, "run_cycle", side_effect=fake_cycle):
                    self.assertEqual(run_agent.loop(args), 1)
            self.assertEqual(executed, ["B"])
            self.assertEqual([item["status"] for item in load_queue(state_dir / "tasks.json")["tasks"]],
                             ["blocked", "blocked"])

    def test_prompt_has_constraints(self):
        prompt = build_prompt(Path("/tmp/sample"), 3)
        self.assertIn("STATUS: BLOCKED", prompt)
        self.assertIn("Não faça push", prompt)


if __name__ == "__main__":
    unittest.main()
