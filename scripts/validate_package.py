#!/usr/bin/env python3
"""Valida o pacote de skills sem instalar dependências."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", "AGENTS.md", "scripts/run_agent.py",
    "scripts/install_into_project.py", "templates/PROJECT_AGENTS.md",
    "templates/ACEITE.example.md",
]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for path in REQUIRED:
        if not (root / path).is_file():
            problems.append("Ausente: " + path)
    skills = sorted((root / ".agents" / "skills").glob("*/SKILL.md"))
    if len(skills) < 21:
        problems.append("Esperadas ao menos 21 skills; encontradas " + str(len(skills)))
    for path in skills:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            problems.append("Front matter ausente: " + str(path))
            continue
        metadata = content.split("---", 2)
        if len(metadata) < 3:
            problems.append("Front matter incompleto: " + str(path))
            continue
        match = re.search(r"^name:\s*(\S+)\s*$", metadata[1], re.MULTILINE)
        desc = re.search(r"^description:\s*(.+)$", metadata[1], re.MULTILINE)
        if not match or not NAME_RE.fullmatch(match.group(1)):
            problems.append("Nome inválido: " + str(path))
        elif match.group(1) != path.parent.name:
            problems.append("Nome não corresponde à pasta: " + str(path))
        if not desc or not desc.group(1).strip():
            problems.append("Descrição ausente: " + str(path))
        if "## Procedimento operacional" not in content:
            problems.append("Procedimento incompleto: " + str(path))
    return problems


if __name__ == "__main__":
    issues = validate()
    for issue in issues:
        print("ERRO:", issue)
    if issues:
        sys.exit(1)
    count = len(list((ROOT / ".agents" / "skills").glob("*/SKILL.md")))
    print(f"Pacote validado: {count} skills, arquivos essenciais presentes.")
