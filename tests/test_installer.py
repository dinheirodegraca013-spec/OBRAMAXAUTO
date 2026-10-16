from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from install_into_project import install, validate_target


class InstallerTests(unittest.TestCase):
    def test_install_is_idempotent_and_preserves_existing_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp).resolve()
            subprocess.run(["git", "init", str(target)], check=True, capture_output=True)
            (target / "AGENTS.md").write_text("# Política anterior\n", encoding="utf-8")
            root = validate_target(str(target))
            install(root)
            first = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("# Política anterior", first)
            self.assertIn("OBRAMAXAUTO:BEGIN", first)
            self.assertTrue((target / ".agents" / "skills" / "continuous-improvement" / "SKILL.md").is_file())
            install(root)
            second = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(first, second)

    def test_scope_example_created_only_if_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp).resolve()
            subprocess.run(["git", "init", str(target)], check=True, capture_output=True)
            (target / "ESCOPO.md").write_text("ESCOPO PREEXISTENTE", encoding="utf-8")
            install(validate_target(str(target)))
            self.assertEqual((target / "ESCOPO.md").read_text(encoding="utf-8"), "ESCOPO PREEXISTENTE")


if __name__ == "__main__":
    unittest.main()
