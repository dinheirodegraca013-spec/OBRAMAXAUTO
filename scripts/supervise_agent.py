#!/usr/bin/env python3
"""Supervisor finito e conservador para reabrir sessões do runner local.

Reinicia apenas após LIMIT_REACHED com progresso. Nunca autoaprova revisão,
reexecuta falhas/bloqueios nem remove travas de segurança.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
from run_agent import verify_target


def state_at(path: Path) -> dict:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Estado do runner inválido.")
    return obj


def supervise(args: argparse.Namespace, invoke=None, sleeper=None) -> int:
    invoke = invoke or subprocess.run
    sleeper = sleeper or time.sleep
    target = verify_target(args.target)
    folder = target / ".obramaxauto"
    if folder.is_symlink():
        raise ValueError("Pasta de estado não pode ser symlink.")
    folder.mkdir(exist_ok=True)
    state_file = folder / "runner-state.json"
    deadline = time.monotonic() + args.max_hours * 3600
    final_reason = "MAX_SESSIONS"
    for index in range(1, args.max_sessions + 1):
        if (folder / "STOP").exists():
            final_reason = "STOP_REQUESTED"
            break
        remaining = deadline - time.monotonic()
        if remaining < 60:
            final_reason = "TIME_LIMIT"
            break
        before = state_at(state_file)
        if before.get("inflight"):
            final_reason = "INTERRUPTED_NEEDS_REVIEW"
            break
        # A previous terminal state must never be silently restarted.
        # Only LIMIT_REACHED with prior progress is eligible for resumption.
        prior_reason = before.get("last_exit_reason")
        if prior_reason and prior_reason != "LIMIT_REACHED":
            final_reason = "NEEDS_OPERATOR_REVIEW"
            break
        previous = int(before.get("total_cycles", 0))
        command = [
            sys.executable, str(Path(__file__).with_name("run_agent.py")),
            "--target", str(target),
            "--max-cycles", str(args.cycles_per_session),
            "--max-hours", str(min(args.hours_per_session, remaining / 3600)),
        ]
        if args.queue:
            command.append("--queue")
        if args.worktree:
            command.append("--worktree")
        if args.verify_command:
            command.extend(["--verify-command", args.verify_command])
        logfile = folder / ("supervisor-" + uuid4().hex + ".log")
        with logfile.open("w", encoding="utf-8") as output:
            proc = invoke(command, stdout=output, stderr=subprocess.STDOUT,
                          check=False)
        after = state_at(state_file)
        reason = after.get("last_exit_reason", "UNKNOWN")
        cycles = int(after.get("total_cycles", 0))
        entry = dict(
            date=datetime.now(timezone.utc).isoformat(),
            session=index, exit_code=proc.returncode,
            reason=reason, cycles_before=previous, cycles_after=cycles,
            log_file=logfile.name,
        )
        with (folder / "supervisor-history.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        print("Sessão", index, "retorno:", proc.returncode, "motivo:", reason,
              "novos ciclos:", cycles - previous)
        if after.get("inflight"):
            final_reason = "INTERRUPTED_NEEDS_REVIEW"
            break
        if proc.returncode == 0 and reason in ("TASK_REVIEW", "READY_FOR_HUMAN_REVIEW"):
            final_reason = "HUMAN_REVIEW"
            break
        if not (proc.returncode == 1 and reason == "LIMIT_REACHED"
                and cycles > previous):
            final_reason = "NEEDS_OPERATOR_REVIEW"
            break
        sleeper(min(args.cooldown, max(0, deadline - time.monotonic())))
    print("Supervisor finalizado:", final_reason)
    return 1 if final_reason in ("INTERRUPTED_NEEDS_REVIEW",
                                 "NEEDS_OPERATOR_REVIEW") else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True)
    p.add_argument("--max-hours", type=float, default=12)
    p.add_argument("--hours-per-session", type=float, default=1)
    p.add_argument("--cycles-per-session", type=int, default=20)
    p.add_argument("--max-sessions", type=int, default=24)
    p.add_argument("--cooldown", type=float, default=10)
    p.add_argument("--queue", action="store_true")
    p.add_argument("--worktree", action="store_true")
    p.add_argument("--verify-command")
    args = p.parse_args()
    if (args.max_hours <= 0 or args.hours_per_session <= 0 or
            args.cycles_per_session < 1 or args.max_sessions < 1 or
            args.cooldown < 0):
        p.error("Os limites devem ser positivos, exceto cooldown que aceita zero.")
    try:
        return supervise(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print("ERRO DO SUPERVISOR:", error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
