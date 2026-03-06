import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

SRC_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = SRC_ROOT / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_INITIALIZERS = [
    "app/agents/shopperAgent_initializer.py",
    "app/agents/inventoryAgent_initializer.py",
    "app/agents/interiorDesignAgent_initializer.py",
    "app/agents/customerLoyaltyAgent_initializer.py",
    "app/agents/cartManagerAgent_initializer.py",
    "app/agents/handoffAgent_initializer.py",
]


def resolve_initializers() -> List[str]:
    configured = os.getenv("AGENT_INITIALIZERS", "").strip()
    if not configured:
        return DEFAULT_INITIALIZERS
    return [item.strip() for item in configured.split(",") if item.strip()]


def run_initializer(initializer: str) -> dict:
    start = time.time()
    script_path = SRC_ROOT / initializer
    command = [sys.executable, str(script_path)]

    result = subprocess.run(
        command,
        cwd=str(SRC_ROOT),
        capture_output=True,
        text=True,
    )

    duration = round(time.time() - start, 2)
    succeeded = result.returncode == 0

    return {
        "initializer": initializer,
        "status": "success" if succeeded else "failed",
        "return_code": result.returncode,
        "duration_seconds": duration,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    initializers = resolve_initializers()
    if not initializers:
        raise ValueError("No agent initializers configured")

    print("Deploying/updating agents with initializers:")
    for item in initializers:
        print(f"- {item}")

    results = [run_initializer(initializer) for initializer in initializers]

    report = {
        "total": len(results),
        "succeeded": sum(1 for item in results if item["status"] == "success"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "results": results,
    }

    report_path = ARTIFACT_DIR / "agent_deployment_report.json"
    with report_path.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2)

    print(f"Wrote agent deployment report: {report_path}")

    failed_initializers = [item["initializer"] for item in results if item["status"] == "failed"]
    if failed_initializers:
        print("Failed initializers:")
        for initializer in failed_initializers:
            print(f"- {initializer}")
        return 1

    print("All agent initializers completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
