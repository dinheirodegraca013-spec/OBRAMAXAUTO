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
        complete(a,"READY",0,"cycle.log",True)
        self.assertEqual(a["status"],"review")
        self.assertIsNone(next_task(q))
        a["status"]="done"
        self.assertEqual(next_task(q)["id"],"B")

    def test_resume_and_attempt_limit(self):
        q={"version":1,"tasks":[]};add(q,"A","Tarefa",[])
        t=q["tasks"][0];self.assertTrue(claim(t,1))
        recover(q);self.assertEqual(t["status"],"pending")
        self.assertFalse(claim(t,1));self.assertEqual(t["status"],"blocked")

    def test_no_false_review_after_failure(self):
        q={"version":1,"tasks":[]};add(q,"A","Tarefa",[])
        t=q["tasks"][0];claim(t,3)
        complete(t,"READY",1,"error.log",True)
        self.assertEqual(t["status"],"pending")

    def test_save_load_and_bad_deps(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state"/"queue.json"
            q={"version":1,"tasks":[]};add(q,"A","Tarefa",[]);save(path,q)
            self.assertEqual(load(path)["tasks"][0]["id"],"A")
            with self.assertRaises(ValueError):add(q,"B","Inválida",["X"])
            q["tasks"][0]["deps"]=["missing"];save(path,q)
            with self.assertRaises(ValueError):load(path)

if __name__=="__main__":unittest.main()
