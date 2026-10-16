#!/usr/bin/env python3
"""Instala skills e contexto sem sobrescrever conteúdo de outro projeto."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKER = "\n\n<!-- OBRAMAXAUTO:BEGIN -->\nLeia também OBRAMAXAUTO.md e use as skills de .agents/skills/ quando relevantes. Não ignore políticas locais mais restritivas.\n<!-- OBRAMAXAUTO:END -->\n"


def validate_target(raw: str) -> Path:
    target = Path(raw).expanduser().resolve()
    if not target.is_dir():
        raise ValueError("Diretório do projeto não encontrado: " + str(target))
    if target == ROOT or ROOT in target.parents:
        raise ValueError("Escolha outro repositório para o aplicativo, separado do kit OBRAMAXAUTO.")
    proc = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        text=True, capture_output=True, check=False,
    )
    if proc.returncode:
        raise ValueError("O destino precisa ser um repositório Git.")
    if Path(proc.stdout.strip()).resolve() != target:
        raise ValueError("Aponte para a raiz do repositório Git, não uma subpasta.")
    return target


def install(target: Path, dry_run: bool = False) -> tuple[int, int]:
    created = skipped = 0

    def copy_new(source: Path, dest: Path) -> None:
        nonlocal created, skipped
        if dest.exists() or dest.is_symlink():
            skipped += 1
            print("Preservado:", dest.relative_to(target))
            return
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        created += 1
        print("Criado:", dest.relative_to(target))

    source_skills = ROOT / ".agents" / "skills"
    for source in sorted(source_skills.glob("*/SKILL.md")):
        copy_new(source, target / ".agents" / "skills" / source.parent.name / "SKILL.md")

    copy_new(ROOT / "templates" / "PROJECT_AGENTS.md", target / "OBRAMAXAUTO.md")
    mapping = {
        "ESCOPO.md": "ESCOPO.example.md",
        "ESTADO.md": "ESTADO.example.md",
        "BACKLOG.md": "BACKLOG.example.md",
        "TESTES.md": "TESTES.example.md",
        "AUDITORIA.md": "AUDITORIA.example.md",
        "ACEITE.md": "ACEITE.example.md",
    }
    for dest, source in mapping.items():
        copy_new(ROOT / "templates" / source, target / dest)

    agents = target / "AGENTS.md"
    if not agents.exists():
        copy_new(ROOT / "templates" / "PROJECT_AGENTS.md", agents)
    elif agents.is_file():
        existing = agents.read_text(encoding="utf-8")
        if "<!-- OBRAMAXAUTO:BEGIN -->" not in existing:
            if not dry_run:
                with agents.open("a", encoding="utf-8") as stream:
                    stream.write(MARKER)
            created += 1
            print("Adicionada referência em AGENTS.md (conteúdo original preservado).")
    else:
        raise ValueError("AGENTS.md não é arquivo regular.")

    print(f"Instalação {'simulada' if dry_run else 'concluída'}: {created} criações/adições, {skipped} preservados.")
    return created, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Raiz do repositório de APLICATIVO")
    parser.add_argument("--dry-run", action="store_true", help="Somente mostrar mudanças")
    args = parser.parse_args()
    try:
        install(validate_target(args.target), args.dry_run)
        return 0
    except (OSError, ValueError) as exc:
        print("ERRO:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
