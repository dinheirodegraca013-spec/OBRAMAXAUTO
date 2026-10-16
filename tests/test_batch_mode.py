"""Garante que a política de execução em lote permaneça distribuída nas skills e prompts."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BatchModeContractTests(unittest.TestCase):
    def test_main_skill_has_no_intermediate_completion(self):
        content = (ROOT / ".agents/skills/master-orchestrator/SKILL.md").read_text(encoding="utf-8")
        for phrase in ("Modo de execução em lote", "relatório consolidado",
                       "não entregue um relatório final", 'Não solicite a palavra "continue"'):
            self.assertIn(phrase, content)

    def test_user_prompt_names_limits_and_human_gate(self):
        content = (ROOT / "prompts/EXECUTAR_EM_LOTE.txt").read_text(encoding="utf-8")
        for phrase in ('"continue"', "PR", "testes", "produção", "um único relatório consolidado",
                       "executor externo persistente"):
            self.assertIn(phrase, content)


if __name__ == "__main__":
    unittest.main()
