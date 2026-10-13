import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "seed_cp67_trial_budget.py"


class SeedTrialBudgetTests(unittest.TestCase):
    def test_cp71_seed_includes_single_context_generation_and_unstarted_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "budget.json"
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--state", str(state_path),
                "--limit-per-harness", "3", "--limit-total", "10",
                "--include-context-probe",
            ], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(state_path.read_text())
            self.assertIsNone(state["deadline_epoch"])
            self.assertEqual(state["generation_counts"], {
                "context": 0, "hermes": 0, "lean": 0, "pydantic": 0,
            })

    def test_existing_trial_seed_still_accepts_fixed_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "budget.json"
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--state", str(state_path),
                "--deadline-epoch", "1234567890", "--limit-per-harness", "3",
                "--limit-total", "9",
            ], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(state_path.read_text())
            self.assertEqual(state["deadline_epoch"], 1234567890.0)
            self.assertEqual(set(state["generation_counts"]), {"pydantic", "hermes", "lean"})

    def test_context_budget_cannot_be_seeded_above_one(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "budget.json"
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--state", str(state_path),
                "--limit-per-harness", "3", "--limit-total", "10",
                "--include-context-probe", "--context-used", "2",
            ], capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(state_path.exists())


if __name__ == "__main__":
    unittest.main()
