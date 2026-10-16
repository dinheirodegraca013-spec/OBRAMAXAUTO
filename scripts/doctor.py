#!/usr/bin/env python3
"""Diagnóstico de pré-requisitos para execução do OBRAMAXAUTO sem alterar arquivos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from run_agent import verify_target, validate_scope, git


def inspect(target: str) -> tuple[list[dict], bool]:
    checks: list[dict] = []
    def record(name: str, ok: bool, detail: str, required: bool = True) -> None:
        checks.append({"item": name, "ok": ok, "required": required, "detail": detail})

    record("Python", sys.version_info >= (3, 10),
           "Requer Python 3.10 ou superior; instalado: " + sys.version.split()[0])
    record("Git", shutil.which("git") is not None,
           "Instale Git e confirme que está no PATH.")
    codex = shutil.which("codex")
    record("Codex CLI", codex is not None,
           "Instale Codex CLI (npm install -g @openai/codex) e teste codex --version.")
    if codex:
        for args, title, required in [
            (["--version"], "Codex CLI versão", True),
            (["login", "status"], "Autenticação Codex", True),
        ]:
            try:
                run = subprocess.run([codex, *args], capture_output=True, text=True, timeout=15)
                record(title, run.returncode == 0,
                       "OK" if run.returncode == 0 else "Falhou: execute codex login e teste novamente.",
                       required)
            except (subprocess.TimeoutExpired, OSError):
                record(title, False, "Codex não respondeu ou não conseguiu iniciar.", required)
    try:
        path = verify_target(target)
        record("Repositório-alvo", True, "Aplicativo separado do repositório OBRAMAXAUTO.")
        try:
            validate_scope(path)
            record("ESCOPO.md", True, "Escopo preenchido (revisão manual ainda necessária).")
        except (OSError, ValueError) as exc:
            record("ESCOPO.md", False, str(exc))
        current = git(path, "branch", "--show-current")
        record("Branch", True, "Atual: " + (current or "HEAD destacado") +
               "; o runner usa uma branch obramax/* própria.", False)
    except (OSError, RuntimeError, ValueError) as exc:
        record("Repositório-alvo", False, str(exc))
    return checks, all(item["ok"] for item in checks if item["required"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Caminho do repositório do aplicativo (não o OBRAMAXAUTO)")
    parser.add_argument("--json", action="store_true", help="Saída para sistemas automatizados")
    args = parser.parse_args()
    checks, ok = inspect(args.target)
    if args.json:
        print(json.dumps({"ready": ok, "checks": checks}, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            label = "OK" if item["ok"] else ("FALHA" if item["required"] else "AVISO")
            print(f"[{label}] {item['item']}: {item['detail']}")
        print("RESULTADO:", "pré-requisitos presentes" if ok else "há bloqueios para resolver")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
