"""Frozen Autolab Hill entry point. The submission contains data, never code to run."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from verify_high_accuracy import PINNED_HOTSPOT_SHA256, judge
from verify_submission import verify


def eval(submission: Path, *, final: bool = False, **params) -> dict:
    submission_file = Path(submission) / "submission.json"
    validity = verify(submission_file, ROOT / "challenge_spec.json")
    grid = 128 if final else 64
    common_config = [{"name": "thermal_grid", "value": f"{grid}x{grid}", "primary": True},
                     {"name": "hotspot_sha256", "value": PINNED_HOTSPOT_SHA256, "primary": True}]
    if not validity["passed"]:
        invalid_metrics = [{"name": name, "value": 1_000_000.0, "direction": "min"}
                           for name in ("score", "worst_gpu_c", "worst_hbm_c")]
        return {"passed": False, "metrics": invalid_metrics, "config": common_config,
                "details": {"reason": validity["reason"]}}
    result = judge(submission_file, ROOT / "vendor/HotSpot/hotspot", grid=grid,
                   reference_file=ROOT / f"reference_{grid}.json")
    return {"passed": True,
            "metrics": [{"name": "score", "value": result["score"], "direction": "min"},
                        {"name": "worst_gpu_c", "value": result["worst_gpu_c"], "direction": "min"},
                        {"name": "worst_hbm_c", "value": result["worst_hbm_c"], "direction": "min"}],
            "config": common_config,
            "details": {"constraint_report": validity,
                        "per_workload": result["workloads"],
                        "reference": result["reference_c"],
                        "final": final}}
