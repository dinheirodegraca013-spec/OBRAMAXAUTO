#!/usr/bin/env python3
"""Executa vários ciclos Codex CLI em um repositório Git local e isolado.

Nunca faz push, deploy, merge, acesso irrestrito ou publicação de produção.
O usuário deve configurar autenticação da CLI, quotas e monitoramento externo.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
from task_queue import load as load_queue, save as save_queue, recover as recover_queue, next_task, claim, complete

ROOT = Path(__file__).resolve().parents[1]
VALID_STATUS = {"CONTINUE", "READY", "BLOCKED"}
STATUS_RE = re.compile(r"STATUS:\s*(CONTINUE|READY|BLOCKED)")
# Arquivos de coordenação podem mudar todo ciclo, sem progresso na entrega.
HOUSEKEEPING_FILES = frozenset({
    "ESTADO.md", "BACKLOG.md", "TESTES.md", "AUDITORIA.md", "ACEITE.md"
})


def parse_status(message: str) -> str:
    """O status só é válido como ÚLTIMA linha não vazia, nunca no meio da resposta."""
    last = next((line.strip() for line in reversed(message.splitlines()) if line.strip()), "")
    match = STATUS_RE.fullmatch(last)
    return match.group(1) if match else "UNKNOWN"


def git(target: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(
        ["git", "-C", str(target), *args],
        text=True, capture_output=True, check=False,
    )
    if check and p.returncode:
        raise RuntimeError("Falha Git (" + " ".join(args) + "): " + p.stderr.strip())
    return p.stdout.strip()


def verify_target(raw: str) -> Path:
    target = Path(raw).expanduser().resolve()
    if not target.is_dir():
        raise ValueError("Repositório alvo não encontrado.")
    if target == ROOT or ROOT in target.parents:
        raise ValueError("O repositório do kit não pode ser alvo da execução.")
    root = git(target, "rev-parse", "--show-toplevel")
    if Path(root).resolve() != target:
        raise ValueError("Aponte --target para a raiz exata do repositório Git.")
    if not (target / "AGENTS.md").is_file() or not (target / "ESCOPO.md").is_file():
        raise ValueError("Instale as instruções e preencha ESCOPO.md antes de executar.")
    return target


def validate_scope(target: Path) -> None:
    """Impede que o agente execute usando o template de escopo ainda não preenchido."""
    contents = (target / "ESCOPO.md").read_text(encoding="utf-8").strip()
    placeholders = ("[descrever]", "[teste reproduzível]", "Descreva o propósito")
    if len(contents) < 200 or any(item in contents for item in placeholders):
        raise ValueError(
            "ESCOPO.md ainda é um modelo ou está incompleto. "
            "Preencha requisitos, ambientes e critérios de aceite antes de iniciar."
        )


def ensure_branch(target: Path, state: dict) -> str:
    current = git(target, "branch", "--show-current")
    previous = state.get("branch")
    if previous:
        if not previous.startswith("obramax/"):
            raise ValueError("Estado antigo aponta para branch não autorizada (" + previous + "); corrija o estado manualmente.")
        if current != previous:
            raise ValueError("Branch mudou desde a execução anterior; volte para " + previous + " ou arquive .obramaxauto/runner-state.json após revisão.")
        return current
    if current.startswith("obramax/"):
        return current
    branch = "obramax/auto-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + str(os.getpid())
    git(target, "switch", "-c", branch)
    return branch


def fingerprint(target: Path) -> str:
    """Resume alterações no produto, ignorando relatórios que o agente reescreve.

    Atualizar apenas BACKLOG/ESTADO/TESTES/AUDITORIA/ACEITE não reinicia
    artificialmente o watchdog de progresso. Alterações reais em arquivos
    rastreados ou novos arquivos não rastreados continuam contando.
    """
    digest = hashlib.sha256()
    # Repositórios novos podem ainda não ter HEAD: aceite o primeiro ciclo.
    head = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--verify", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    pathspecs = ["."] + [":(exclude)" + name for name in sorted(HOUSEKEEPING_FILES)]
    if head.returncode == 0:
        digest.update(head.stdout.strip().encode("utf-8"))
        # git diff HEAD cobre index + worktree, inclusive alterações staged.
        changes = [("diff", "HEAD", "--binary", "--", *pathspecs)]
    else:
        digest.update(b"unborn-git-history")
        # Sem commit inicial: considerar arquivos staged e worktree.
        changes = [
            ("diff", "--cached", "--binary", "--", *pathspecs),
            ("diff", "--binary", "--", *pathspecs),
        ]
    for command in changes:
        digest.update(git(target, *command).encode("utf-8", errors="replace"))
    p = subprocess.run(
        ["git", "-C", str(target), "ls-files", "--others", "--exclude-standard", "-z"],
        capture_output=True, check=True,
    )
    for raw in sorted(part for part in p.stdout.split(b"\x00") if part):
        relative = os.fsdecode(raw).replace("\\", "/")
        if relative in HOUSEKEEPING_FILES:
            continue
        path = target / os.fsdecode(raw)
        digest.update(raw)
        # Nunca seguir symlink de arquivo não rastreado para fora do projeto.
        if path.is_file() and not path.is_symlink():
            try:
                with path.open("rb") as stream:
                    digest.update(stream.read(256 * 1024))
                digest.update(str(path.stat().st_size).encode())
            except OSError:
                pass
    return digest.hexdigest()

def acceptance_gate(target: Path) -> tuple[bool, str]:
    acceptance = target / "ACEITE.md"
    tests = target / "TESTES.md"
    audit = target / "AUDITORIA.md"
    if not all(path.is_file() for path in (acceptance, tests, audit)):
        return False, "ACEITE.md, TESTES.md e AUDITORIA.md são obrigatórios."
    text = acceptance.read_text(encoding="utf-8")
    checklist = re.findall(r"^\s*[-*]\s*\[([ xX])\]", text, re.MULTILINE)
    if not checklist or any(x == " " for x in checklist):
        return False, "Critérios em ACEITE.md ausentes ou ainda pendentes."
    test_text = tests.read_text(encoding="utf-8")
    audit_text = audit.read_text(encoding="utf-8")
    # Uma menção isolada a PASS não é evidência; exigir linha de teste concluído.
    def documented_pass(line: str) -> bool:
        if line.lstrip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            return (len(cells) >= 5 and cells[3].upper() in {"PASS", "APROVADO"}
                    and cells[1] not in {"", "-"} and cells[2] not in {"", "-"})
        return bool(re.fullmatch(r"\s*(?:Caso|Teste|Test)\s+[^:]+:\s*(?:PASS|APROVADO)\s*", line, re.I))

    if (not any(documented_pass(line) for line in test_text.splitlines())
            or re.search(r"\bNÃO\s+(?:EXECUTADO|APROVADO)\b", test_text, re.I)):
        return False, "TESTES.md sem evidência explícita de teste aprovado."
    if not re.search(r"^Parecer final:\s*PASS\s*$", audit_text, re.I | re.M):
        return False, "Falta parecer PASS em AUDITORIA.md."
    return True, "Gates documentais presentes; revisão humana independente ainda necessária."


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"total_cycles": 0, "consecutive_errors": 0, "stagnant_cycles": 0, "history": []}
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Estado inválido; revise manualmente o arquivo.")
    return obj


def save_state(path: Path, data: dict) -> None:
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def acquire_lock(path: Path):
    """Trava pelo sistema operacional; o lock libera mesmo após queda do processo.

    Não remova o arquivo ao sair: desvincular um inode bloqueado criaria
    uma janela onde outro processo poderia abrir um arquivo novo sem lock.
    """
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o600)
    handle = os.fdopen(fd, "r+", encoding="utf-8")
    try:
        if os.name == "nt":
            import msvcrt
            # Lock de um byte requer pelo menos um byte no Windows.
            handle.seek(0)
            if not handle.read(1):
                handle.seek(0)
                handle.write(" ")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # O conteúdo do arquivo é apenas diagnóstico, não define a exclusão.
        handle.seek(0)
        handle.write(("PID=" + str(os.getpid()) + "\n").ljust(80))
        handle.flush()
        return handle
    except OSError as exc:
        handle.close()
        raise RuntimeError("Outro runner mantém a trava do projeto: " + str(path)) from exc


def build_prompt(target: Path, cycle: int, task: dict | None = None) -> str:
    return (
        "Atue apenas neste repositório local autorizado: " + str(target) + "\n"
        "Ciclo " + str(cycle) + ". Leia AGENTS.md, OBRAMAXAUTO.md (se houver), "
        "ESCOPO.md, ESTADO.md, BACKLOG.md, TESTES.md, AUDITORIA.md e ACEITE.md. "
        "Selecione e leia as skills relevantes da pasta .agents/skills/. "
        "Faça trabalho concreto, mínimo e testável; sem pedir 'continue'. "
        "Se houver tarefa liberada, execute, teste e registre evidências. "
        "Não faça push, merge, deployment de produção, exclusões destrutivas, "
        "alterações fora do workspace nem tentativas de contornar limites de rede. "
        "Se depender de ações proibidas, registre o bloqueio e procure tarefa independente. "
        "Ao encerrar, termine SUA ÚLTIMA LINHA com apenas STATUS: CONTINUE, "
        "STATUS: READY ou STATUS: BLOCKED. "
        "READY só após ACEITE.md todo marcado, evidências de testes e "
        "AUDITORIA.md contendo Parecer final: PASS. "
        "Nunca fabrique testes ou resultados."
        + ("\nTAREFA AUTORIZADA DA FILA: [" + task["id"] + "] " + task["title"]
           + ". Trabalhe especificamente nela; não mude o estado da fila diretamente. "
           + "Se faltar condição de autorização, declare BLOCKED." if task else "")
    )


def run_cycle(codex: str, target: Path, logdir: Path, cycle: int, timeout: int, task: dict | None = None) -> tuple[int, str, str]:
    logfile = logdir / f"cycle-{cycle:05d}.log"
    answer = logdir / f"cycle-{cycle:05d}-last.txt"
    # Falhas, quedas e ciclos reexecutados não podem reaproveitar STATUS antigo.
    answer.unlink(missing_ok=True)
    command = [
        codex, "exec",
        "--sandbox", "workspace-write",
        "--ask-for-approval", "never",
        "--output-last-message", str(answer),
        "-",
    ]
    prompt = build_prompt(target, cycle, task)
    try:
        with logfile.open("w", encoding="utf-8") as handle:
            # Sessão/grupo próprio para interromper subprocessos do agente.
            group_kwargs = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                            if os.name == "nt" else {"start_new_session": True})
            proc = subprocess.Popen(
                command, stdin=subprocess.PIPE,
                stdout=handle, stderr=subprocess.STDOUT,
                cwd=target, text=True, **group_kwargs,
            )
            try:
                proc.communicate(input=prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    # taskkill /T encerra descendentes no Windows.
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   capture_output=True, check=False, timeout=15)
                else:
                    import signal
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                proc.communicate(timeout=15)
                handle.write("\nTIMEOUT: ciclo e subprocessos encerrados.\n")
                return 124, "UNKNOWN", str(logfile)
        message = answer.read_text(encoding="utf-8") if proc.returncode == 0 and answer.is_file() else ""
        return proc.returncode, parse_status(message), str(logfile)


def verify_task(target: Path, command: str | None, timeout: int = 300) -> bool:
    """Verifica tarefa por comando configurado explicitamente pelo operador.

    Sem shell; sem comando -> sem gate e sem promoção para revisão.
    """
    if not command:
        print("Verificação não configurada: tarefa permanece pendente.")
        return False
    argv = shlex.split(command)
    if not argv or Path(argv[0]).name not in {"python", "python3", "pytest", "npm", "pnpm", "bun"}:
        raise ValueError("Use comando de teste permitido (python/pytest/npm/pnpm/bun).")
    if any(a in {"-c", "--eval", "-e"} for a in argv[1:]):
        raise ValueError("Comando de avaliação inline não permitido.")
    try:
        result = subprocess.run(argv, cwd=target, timeout=timeout, check=False)
        print("Verificação:", argv[0], "exit_code=", result.returncode)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as error:
        print("Verificação não concluída:", error)
        return False


def loop(args: argparse.Namespace) -> int:
    target = verify_target(args.target)
    codex = shutil.which("codex")
    if not codex and not args.dry_run:
        raise RuntimeError("CLI codex não encontrada no PATH.")
    # Dry-run realmente somente leitura: não cria branch, estado, lock ou excludes.
    if args.dry_run:
        branch = git(target, "branch", "--show-current")
        print("DRY RUN (nenhuma alteração):", "repo=", target,
              "branch=", branch, "codex=", codex or "não instalado")
        return 0
    validate_scope(target)
    state_dir = target / ".obramaxauto"
    state_dir.mkdir(exist_ok=True)
    # Dados locais (inclusive logs de ferramentas) não devem entrar no Git.
    exclude = target / ".git" / "info" / "exclude"
    if exclude.is_file():
        existing = exclude.read_text(encoding="utf-8")
        if ".obramaxauto/" not in existing:
            with exclude.open("a", encoding="utf-8") as stream:
                stream.write("\n.obramaxauto/\n")
    statefile = state_dir / "runner-state.json"
    lockfile = state_dir / "runner.lock"
    lock_handle = acquire_lock(lockfile)
    try:
        state = load_state(statefile)
        branch = ensure_branch(target, state)
        state["branch"] = branch
        state["target"] = str(target)
        state["last_run_start"] = datetime.now(timezone.utc).isoformat()
        save_state(statefile, state)
        queue_path = state_dir / "tasks.json"
        if args.queue:
            q = load_queue(queue_path)
            if not q["tasks"]:
                raise ValueError("Fila vazia: adicione tarefas com scripts/task_queue.py antes de --queue.")
            recover_queue(q)
            save_queue(queue_path, q)
        print("OBRAMAXAUTO", "| branch:", branch, "| máximo de ciclos:", args.max_cycles)
        start = time.monotonic()
        end_reason = "LIMIT_REACHED"
        for _ in range(args.max_cycles):
            remaining = args.max_hours * 3600 - (time.monotonic() - start)
            if remaining < 10:
                break
            task = None
            if args.queue:
                q = load_queue(queue_path)
                task = next_task(q)
                if task is None:
                    end_reason = "QUEUE_IDLE"
                    break
                if not claim(task, args.max_task_attempts):
                    save_queue(queue_path, q)
                    end_reason = "TASK_ATTEMPT_LIMIT"
                    break
                save_queue(queue_path, q)
            cycle = int(state.get("total_cycles", 0)) + 1
            before = fingerprint(target)
            print(f"Iniciando ciclo {cycle}...")
            code, status, log = run_cycle(
                codex, target, state_dir, cycle,
                max(1, min(args.cycle_timeout, int(remaining))), task,
            )
            after = fingerprint(target)
            progressed = before != after
            if args.queue:
                verified = verify_task(target, args.verify_command) if status == "READY" and code == 0 and progressed else False
                complete(task, status, code, Path(log).name, progressed, verified=verified)
                save_queue(queue_path, q)
                # A indicação READY do modelo não equivale a conclusão verificável.
                # Impedir que o estado global termine se a tarefa ficou pendente.
                if status == "READY" and task["status"] != "review":
                    print("READY rejeitado: tarefa sem progresso e/ou testes válidos.")
                    status = "CONTINUE"
            if code:
                state["consecutive_errors"] = int(state.get("consecutive_errors", 0)) + 1
            else:
                state["consecutive_errors"] = 0
            state["stagnant_cycles"] = 0 if progressed else int(state.get("stagnant_cycles", 0)) + 1
            if status == "READY" and not args.queue:
                ok, reason = acceptance_gate(target)
                if not ok:
                    print("READY não aceito:", reason)
                    status = "CONTINUE"
            record = {
                "cycle": cycle, "date": datetime.now(timezone.utc).isoformat(),
                "returncode": code, "status": status, "progressed": progressed,
                "log": Path(log).name,
            }
            state["total_cycles"] = cycle
            state["last_status"] = status
            state["history"] = (state.get("history", []) + [record])[-100:]
            save_state(statefile, state)
            print(f"Ciclo {cycle}: status={status}, rc={code}, mudou={progressed}, log={log}")
            if args.queue and task["status"] == "review":
                end_reason = "TASK_REVIEW"
                break
            if status == "READY" and code == 0 and not args.queue:
                end_reason = "READY_FOR_HUMAN_REVIEW"
                break
            if status == "BLOCKED" and code == 0:
                end_reason = "BLOCKED"
                break
            if state["consecutive_errors"] >= args.max_errors:
                end_reason = "ERROR_LIMIT"
                break
            if state["stagnant_cycles"] >= args.max_stagnant:
                end_reason = "NO_PROGRESS"
                break
            if status == "UNKNOWN" and code == 0:
                print("Sem linha STATUS válida; verificar o último resultado do Codex.")
            time.sleep(min(args.cooldown, max(0, args.max_hours * 3600 - (time.monotonic() - start))))
        state["last_exit_reason"] = end_reason
        save_state(statefile, state)
        print("Encerramento:", end_reason)
        print("Branch local:", branch)
        print("Revise alterações e testes antes de abrir PR ou publicar.")
        return 0 if end_reason in {"READY_FOR_HUMAN_REVIEW", "TASK_REVIEW"} else 1
    finally:
        lock_handle.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Raiz do repositório local do sistema-alvo")
    parser.add_argument("--max-cycles", type=int, default=20)
    parser.add_argument("--max-hours", type=float, default=4.0)
    parser.add_argument("--cycle-timeout", type=int, default=3600)
    parser.add_argument("--cooldown", type=int, default=5)
    parser.add_argument("--max-errors", type=int, default=3)
    parser.add_argument("--max-stagnant", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--queue", action="store_true", help="Consumir fila local persistente tasks.json")
    parser.add_argument("--max-task-attempts", type=int, default=3)
    parser.add_argument("--verify-command", help="Comando de testes configurado pelo operador; obrigatório para concluir tarefa da fila")
    args = parser.parse_args()
    if (args.max_cycles < 1 or args.max_hours <= 0 or args.cycle_timeout < 1
            or args.cooldown < 0 or args.max_errors < 1 or args.max_stagnant < 1 or args.max_task_attempts < 1):
        parser.error("Todos os limites devem ser positivos (cooldown pode ser zero).")
    try:
        return loop(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("ERRO:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
