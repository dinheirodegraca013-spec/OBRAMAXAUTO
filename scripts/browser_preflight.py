#!/usr/bin/env python3
"""Diagnóstico de browser CLIs sem instalar pacotes ou abrir sites."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from pathlib import Path

TOOLS={"playwright-cli":"microsoft/playwright-cli",
       "agent-browser":"vercel-labs/agent-browser"}

def detect() -> list[dict]:
    output=[]
    for binary,source in TOOLS.items():
        executable=shutil.which(binary)
        item={"tool":binary,"source":source,"installed":bool(executable),
              "version":None,"working":False}
        if executable:
            try:
                run=subprocess.run([executable,"--version"],text=True,capture_output=True,timeout=12)
                item["version"]=(run.stdout or run.stderr).strip()[:240]
                item["working"]=run.returncode==0
            except (OSError,subprocess.TimeoutExpired): pass
        output.append(item)
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    result=detect()
    if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        for item in result:
            print(f"{item['tool']}: "+("disponível" if item["working"] else "não disponível")+
                  (f" — {item['version']}" if item["version"] else ""))
        print("Nenhum navegador/site foi aberto. Para E2E use somente ambiente preview e dados sintéticos.")
    return 0

if __name__=="__main__":raise SystemExit(main())
