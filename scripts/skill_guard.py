#!/usr/bin/env python3
"""Triagem conservadora de SKILL.md externos. Não executa o material analisado.
Resultado LIMPO não implica segurança; revisão humana obrigatória.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

PATTERNS = {
    "remote-shell": r"\b(?:curl|wget)\b[^\n]{0,160}\|\s*(?:ba)?sh\b",
    "dangerous-delete": r"\b(?:rm\s+-rf|DROP\s+TABLE|TRUNCATE\s+TABLE)\b",
    "secrets": r"(?:\.env\b|API_KEY|SECRET_KEY|access.token)[^\n]{0,120}(?:send|upload|post|exfiltrat)",
    "approval-bypass": r"(?:danger-full-access|bypass.approval|disable.sandbox|ignore.previous.instructions)",
    "shell-eval": r"\b(?:eval|exec)\s*\(.*(?:input|request|response)",
}
MAX_BYTES=200_000

def scan(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Forneça arquivo regular, não link simbólico.")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Arquivo excede limite de inspeção.")
    data=path.read_text(encoding="utf-8")
    findings=[]
    for label,expression in PATTERNS.items():
        for match in re.finditer(expression,data,re.I):
            findings.append({"rule":label,"line":data.count("\n",0,match.start())+1})
    return {"file":str(path),"findings":findings,"review_required":True,
            "risk":"REVIEW" if findings else "UNKNOWN",
            "notice":"Triagem por padrões; nunca é autorização para executar ou instalar."}

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--json",action="store_true")
    a=p.parse_args()
    try: result=scan(Path(a.path))
    except (OSError,UnicodeError,ValueError) as err:
        print("ERRO:",err,file=sys.stderr);return 2
    if a.json:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print("Arquivo:",result["file"],"| achados:",len(result["findings"]))
        for f in result["findings"]:print("  ",f["rule"],"linha",f["line"])
        print(result["notice"])
    return 1 if result["findings"] else 0

if __name__=="__main__":raise SystemExit(main())
