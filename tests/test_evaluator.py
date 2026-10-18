"""Fast Hill contract checks. A separate organizer run tests all five HotSpot cases."""

from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval import eval as evaluate
from verify_submission import verify


class HillContract(unittest.TestCase):
    def test_baseline_constraints(self):
        report = verify(ROOT / "examples/baseline/submission.json")
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["links"]), 8)


    def test_broken_submission_is_rejected(self):
        report = evaluate(ROOT / "examples/invalid")
        self.assertFalse(report["passed"])
        self.assertIn("clearance", report["details"]["reason"])


if __name__ == "__main__":
    unittest.main()
