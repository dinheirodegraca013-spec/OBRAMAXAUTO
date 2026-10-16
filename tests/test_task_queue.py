import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from task_queue import add,claim,complete,load,next_task,recover,save

class TaskQueueTests(unittest.TestCase):
    def test_dependency_and_human_review(self):
        q={"version":1,"tasks":[]}
        add(q,"A","Criar API",[])
        add(q,"B","Testar API",["A"])
        self.assertEqual(next_task(q)["id"],"A")
        a=q["tasks"][0];claim(a,3)
        self.assertIsNone(next_task(q))
        complete(a,"READY",0,"cycle.log",True,verified=True)
        self.assertEqual(a["status"],"review")
        self.assertIsNone(next_task(q))
        a["status"]="done"
        self.assertEqual(next_task(q)["id"],"B")

    def test_resume_and_attempt_limit(self):
        q={"version":1,"tasks":[]};add(q,"A","Tarefa",[])
        t=q["tasks"][0];self.assertTrue(claim(t,1))
        recover(q);self.assertEqual(t["status"],"blocked")
        self.assertFalse(claim(t,1));self.assertEqual(t["status"],"blocked")

    def test_no_false_review_after_failure(self):
        q={"version":1,"tasks":[]};add(q,"A","Tarefa",[])
        t=q["tasks"][0];claim(t,3)
        complete(t,"READY",1,"error.log",True)
        self.assertEqual(t["status"],"pending")

    def test_ready_without_verified_evidence_remains_pending(self):
        q={"version":1,"tasks":[]}
        add(q,"A","Implementar",[])
        task=q["tasks"][0]
        claim(task,3)
        complete(task,"READY",0,"cycle.log",True)
        self.assertEqual(task["status"],"pending")
        self.assertFalse(task["verification_passed"])

    def test_load_rejects_indirect_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "queue.json"
            q = {"version": 1, "tasks": [
                {"id": "A", "title": "A", "status": "pending", "deps": ["B"]},
                {"id": "B", "title": "B", "status": "pending", "deps": ["C"]},
                {"id": "C", "title": "C", "status": "pending", "deps": ["A"]},
            ]}
            save(path, q)
            with self.assertRaisesRegex(ValueError, "circulares"):
                load(path)

    def test_load_accepts_valid_dependency_dag(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "queue.json"
            q = {"version": 1, "tasks": []}
            add(q, "A", "A", [])
            add(q, "B", "B", ["A"])
            add(q, "C", "C", ["A", "B"])
            save(path, q)
            self.assertEqual(len(load(path)["tasks"]), 3)

    def test_cli_refuses_write_during_runner_lock(self):
        import subprocess
        from run_agent import acquire_lock
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/".obramaxauto"/"tasks.json"
            path.parent.mkdir()
            script=Path(__file__).resolve().parents[1]/"scripts"/"task_queue.py"
            with acquire_lock(path.parent/"runner.lock"):
                proc=subprocess.run([sys.executable,str(script),"--queue",str(path),
                    "add","A","Primeira tarefa"],capture_output=True,text=True)
                self.assertNotEqual(proc.returncode,0)
                self.assertFalse(path.exists())
            proc=subprocess.run([sys.executable,str(script),"--queue",str(path),
                "add","A","Primeira tarefa"],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(load(path)["tasks"][0]["id"],"A")

    def test_recovery_blocks_running_and_does_not_approve(self):
        q={"version":1,"tasks":[]}
        add(q,"A","Efeito externo",[])
        t=q["tasks"][0]
        claim(t,3)
        recover(q)
        self.assertEqual(t["status"],"blocked")
        self.assertFalse(t["verification_passed"])
        self.assertIn("revisar",t["note"])
        self.assertIsNone(next_task(q))

    def test_cli_retry_requires_explicit_acknowledgement(self):
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/".obramaxauto"/"tasks.json"
            q={"version":1,"tasks":[]}
            add(q,"A","Tarefa",[])
            q["tasks"][0]["status"]="blocked"
            q["tasks"][0]["attempts"]=3
            q["tasks"][0]["baseline_fingerprint"]="a"*64
            q["tasks"][0]["net_progress"]=True
            save(path,q)
            cli=Path(__file__).resolve().parents[1]/"scripts"/"task_queue.py"
            command=[sys.executable,str(cli),"--queue",str(path),"retry","A"]
            no_ack=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(no_ack.returncode,0)
            self.assertEqual(load(path)["tasks"][0]["status"],"blocked")
            yes=subprocess.run(command+["--ack-reviewed","--reset-attempts"],
                               capture_output=True,text=True)
            self.assertEqual(yes.returncode,0,yes.stderr)
            task=load(path)["tasks"][0]
            self.assertEqual((task["status"],task["attempts"]),("pending",0))
            self.assertNotIn("baseline_fingerprint",task)
            self.assertNotIn("net_progress",task)

    def test_save_load_and_bad_deps(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state"/"queue.json"
            q={"version":1,"tasks":[]};add(q,"A","Tarefa",[]);save(path,q)
            self.assertEqual(load(path)["tasks"][0]["id"],"A")
            with self.assertRaises(ValueError):add(q,"B","Inválida",["X"])
            q["tasks"][0]["deps"]=["missing"];save(path,q)
            with self.assertRaises(ValueError):load(path)

if __name__=="__main__":unittest.main()
