#!/usr/bin/env python3
"""Fila local durável de tarefas. Nunca executa comandos próprios do arquivo de fila."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

STATES={"pending","running","blocked","review","done"}
def utcnow(): return datetime.now(timezone.utc).isoformat()

def load(path: Path) -> dict:
    if not path.exists(): return {"version":1,"tasks":[]}
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict) or obj.get("version")!=1 or not isinstance(obj.get("tasks"),list):
        raise ValueError("Fila inválida")
    ids=set()
    for t in obj["tasks"]:
        if not isinstance(t,dict) or not isinstance(t.get("id"),str) or not t["id"].strip() or t["id"] in ids:
            raise ValueError("ID de tarefa ausente ou duplicado")
        ids.add(t["id"])
        if t.get("status") not in STATES or not isinstance(t.get("title"),str) or not t["title"].strip():
            raise ValueError("Tarefa inválida")
        if not isinstance(t.get("deps",[]),list) or any(not isinstance(d,str) for d in t["deps"]):
            raise ValueError("Dependências inválidas")
        if not isinstance(t.get("attempts",0),int) or isinstance(t.get("attempts",0),bool) or t.get("attempts",0)<0:
            raise ValueError("Tentativas inválidas")
    for t in obj["tasks"]:
        if t.get("id") in t.get("deps",[]) or any(dep not in ids for dep in t.get("deps",[])):
            raise ValueError("Dependência inexistente ou circular direta")
    return obj

def save(path:Path,obj:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(path)

def next_task(obj:dict):
    done={t["id"] for t in obj["tasks"] if t["status"]=="done"}
    for t in obj["tasks"]:
        if t["status"]=="pending" and all(d in done for d in t.get("deps",[])):
            return t
    return None

def recover(obj:dict):
    # Runner tem lock exclusivo: uma tarefa "running" é de sessão interrompida.
    for task in obj["tasks"]:
        if task["status"]=="running":
            task["status"]="pending"
            task["note"]="Retomada após execução interrompida; verifique evidências antes de marcar concluída."
            task["updated_at"]=utcnow()

def claim(task:dict,max_attempts:int):
    if task.get("attempts",0)>=max_attempts:
        task["status"]="blocked"
        task["note"]="Limite de tentativas atingido"
        task["updated_at"]=utcnow()
        return False
    task["attempts"]=task.get("attempts",0)+1
    task["status"]="running"
    task["updated_at"]=utcnow()
    return True

def complete(task:dict,status:str,exit_code:int,log:str,progress:bool):
    # Somente READY com execução bem-sucedida e progresso real vai para revisão humana.
    task["status"]="review" if status=="READY" and exit_code==0 and progress else ("blocked" if status=="BLOCKED" else "pending")
    task["last_exit_code"]=exit_code
    task["last_log"]=log
    task["last_status"]=status
    task["updated_at"]=utcnow()
    task["note"]="Revisão humana obrigatória antes de marcar done" if task["status"]=="review" else "Aguardando nova tentativa ou diagnóstico"

def add(obj:dict,task_id:str,title:str,deps:list[str]):
    if any(t["id"]==task_id for t in obj["tasks"]): raise ValueError("ID duplicado")
    if not task_id or not title or any(d not in {t["id"] for t in obj["tasks"]} for d in deps):
        raise ValueError("Título/ID/dependência inválido")
    obj["tasks"].append({"id":task_id,"title":title,"deps":deps,"status":"pending","attempts":0,"created_at":utcnow()})

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--queue",required=True)
    s=p.add_subparsers(dest="command",required=True)
    a=s.add_parser("add");a.add_argument("id");a.add_argument("title");a.add_argument("--deps",nargs="*",default=[])
    s.add_parser("list")
    d=s.add_parser("approve");d.add_argument("id")
    args=p.parse_args();path=Path(args.queue);obj=load(path)
    if args.command=="add":
        add(obj,args.id,args.title,args.deps);save(path,obj)
    elif args.command=="approve":
        t=next((t for t in obj["tasks"] if t["id"]==args.id),None)
        if t is None or t["status"]!="review":raise SystemExit("Apenas tarefas review podem ser aprovadas")
        t["status"]="done";t["updated_at"]=utcnow();save(path,obj)
    print(json.dumps(obj,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
