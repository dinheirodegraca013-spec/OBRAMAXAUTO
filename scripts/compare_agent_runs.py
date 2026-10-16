#!/usr/bin/env python3
"""Compara resultados documentados de POCs, sem inventar benchmarks.
Cada JSON deve conter run_id, tool, scenario, exit_code, duration_seconds,
tests_passed, tests_total, resumed, evidence_url. Não executa terceiros.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

REQUIRED={"run_id","tool","scenario","exit_code","duration_seconds",
          "tests_passed","tests_total","resumed","evidence_url"}
TOOLS={"obramaxauto","ralphex","symphony"}

def evaluate(records:list[dict])->list[dict]:
    clean=[]
    for i,r in enumerate(records):
        if not isinstance(r,dict) or not REQUIRED.issubset(r):
            raise ValueError(f"registro {i} incompleto")
        if r["tool"] not in TOOLS or not isinstance(r["exit_code"],int):
            raise ValueError(f"registro {i}: ferramenta/código inválido")
        if any(not isinstance(r[k],int) or isinstance(r[k],bool) or r[k]<0 for k in ("tests_total","tests_passed")):
            raise ValueError("contagem inválida")
        if r["tests_passed"]>r["tests_total"] or r["tests_total"]==0:
            raise ValueError("testes inconsistentes")
        if not isinstance(r["duration_seconds"],(int,float)) or isinstance(r["duration_seconds"],bool) or r["duration_seconds"]<0:
            raise ValueError("duração inválida")
        if not isinstance(r["resumed"],bool) or not isinstance(r["evidence_url"],str) or not r["evidence_url"].startswith("https://"):
            raise ValueError("sem evidência HTTPS ou campo de retomada inválido")
        clean.append({k:r[k] for k in sorted(REQUIRED)})
    return clean

def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",help="JSON array de resultados reais, com evidência")
    a=p.parse_args()
    try:
        rows=evaluate(json.loads(Path(a.input).read_text(encoding="utf-8")))
    except (OSError,ValueError,TypeError) as e:
        print("ERRO:",e,file=sys.stderr);return 2
    for r in rows:
        pct=round(100*r["tests_passed"]/r["tests_total"],1)
        print(f"{r['tool']} | {r['scenario']} | {pct}% testes | {r['duration_seconds']}s | "
              f"retomou={r['resumed']} | rc={r['exit_code']} | {r['evidence_url']}")
    if not rows: print("Nenhuma execução real registrada: comparação ainda pendente.")
    return 0
if __name__=="__main__":raise SystemExit(main())
