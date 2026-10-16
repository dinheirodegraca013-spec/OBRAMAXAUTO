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
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
VALID_STATUS = {"CONTINUE", "READY", "BLOCKED"}
STATUS_RE = re.compile(r"STATUS:\s*(CONTINUE|READY|BLOCKED)")


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
    digest = hashlib.sha256()
    for command in [("rev-parse", "HEAD"), ("diff", "HEAD", "--binary"), ("status", "--porcelain")]:
        digest.update(git(target, *command).encode("utf-8", errors="replace"))
    p = subprocess.run(
        ["git", "-C", str(target), "ls-files", "--others", "--exclude-standard", "-z"],
        capture_output=True, check=True,
    )
    for raw in sorted(part for part in p.stdout.split(b"\x00") if part):
        path = (target / os.fsdecode(raw))
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


def acquire_lock(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("Já existe lock. Verifique outro runner em operação antes de apagar " + str(path)) from exc
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(str(os.getpid()) + "\n")


def build_prompt(target: Path, cycle: int) -> str:
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
    )


def run_cycle(codex: str, target: Path, logdir: Path, cycle: int, timeout: int) -> tuple[int, str, str]:
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
    prompt = build_prompt(target, cycle)
    try:
        with logfile.open("w", encoding="utf-8") as handle:
            completed = subprocess.run(
                command, input=prompt, text=True,
                stdout=handle, stderr=subprocess.STDOUT,
                cwd=target, timeout=timeout, check=False,
            )
        message = answer.read_text(encoding="utf-8") if completed.returncode == 0 and answer.is_file() else ""
        return completed.returncode, parse_status(message), str(logfile)
    except subprocess.TimeoutExpired:
        with logfile.open("a", encoding="utf-8") as handle:
            handle.write("\nTIMEOUT: ciclo excedeu limite.\n")
        return 124, "UNKNOWN", str(logfile)


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
    acquire_lock(lockfile)
    try:
        state = load_state(statefile)
        branch = ensure_branch(target, state)
        state["branch"] = branch
        state["target"] = str(target)
        state["last_run_start"] = datetime.now(timezone.utc).isoformat()
        save_state(statefile, state)
        print("OBRAMAXAUTO", "| branch:", branch, "| máximo de ciclos:", args.max_cycles)
        start = time.monotonic()
        end_reason = "LIMIT_REACHED"
        for _ in range(args.max_cycles):
            remaining = args.max_hours * 3600 - (time.monotonic() - start)
            if remaining < 10:
                break
            cycle = int(state.get("total_cycles", 0)) + 1
            before = fingerprint(target)
            print(f"Iniciando ciclo {cycle}...")
            code, status, log = run_cycle(
                codex, target, state_dir, cycle,
                max(1, min(args.cycle_timeout, int(remaining))),
            )
            after = fingerprint(target)
            progressed = before != after
            if code:
                state["consecutive_errors"] = int(state.get("consecutive_errors", 0)) + 1
            else:
                state["consecutive_errors"] = 0
            state["stagnant_cycles"] = 0 if progressed else int(state.get("stagnant_cycles", 0)) + 1
            if status == "READY":
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
            if status == "READY" and code == 0:
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
        return 0 if end_reason == "READY_FOR_HUMAN_REVIEW" else 1
    finally:
        lockfile.unlink(missing_ok=True)


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
    args = parser.parse_args()
    if (args.max_cycles < 1 or args.max_hours <= 0 or args.cycle_timeout < 1
            or args.cooldown < 0 or args.max_errors < 1 or args.max_stagnant < 1):
        parser.error("Todos os limites devem ser positivos (cooldown pode ser zero).")
    try:
        return loop(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("ERRO:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
