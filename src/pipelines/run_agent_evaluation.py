import json
import os
import re
import uuid
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Tuple

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

from services.handoff_service import HandoffService

try:
    from azure.monitor.opentelemetry import configure_azure_monitor
except ImportError:
    configure_azure_monitor = None


load_dotenv()

SRC_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = SRC_ROOT / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def setup_tracing() -> None:
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if connection_string and configure_azure_monitor:
        configure_azure_monitor(connection_string=connection_string)
        OpenAIInstrumentor().instrument()


def get_required_env(name: str, fallback: str | None = None) -> str:
    value = os.getenv(name, fallback)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_case(raw_case: Dict[str, Any]) -> Tuple[str, str, str]:
    query_text = str(raw_case.get("query", "")).strip()
    expected_raw = str(raw_case.get("expected_domain", "")).strip()

    expected_domain = expected_raw.split(":")[-1].strip() if ":" in expected_raw else expected_raw

    domain_match = re.search(r"Current\s+domain:\s*([a-zA-Z_]+)", query_text, re.IGNORECASE)
    user_match = re.search(r"User\s+message:\s*(.+)$", query_text, re.IGNORECASE | re.DOTALL)

    current_domain = domain_match.group(1).strip() if domain_match else "cora"
    user_message = user_match.group(1).strip() if user_match else query_text

    return current_domain, user_message, expected_domain


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as data_file:
        for line in data_file:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    setup_tracing()
    tracer = trace.get_tracer(__name__)

    dataset_path = Path(
        os.getenv(
            "AGENT_EVAL_DATASET",
            str(SRC_ROOT / "data" / "handoff_service_evaluation_grounded.jsonl"),
        )
    )

    endpoint = get_required_env("FOUNDRY_ENDPOINT")
    deployment = get_required_env("gpt_deployment")

    test_cases = load_jsonl(dataset_path)
    results: List[Dict[str, Any]] = []
    started = perf_counter()

    with AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential()) as project_client:
        openai_client = project_client.get_openai_client()
        handoff_service = HandoffService(
            azure_openai_client=openai_client,
            deployment_name=deployment,
            default_domain="cora",
            lazy_classification=True,
        )

        for index, case in enumerate(test_cases, start=1):
            current_domain, user_message, expected_domain = parse_case(case)
            session_id = str(uuid.uuid4())
            handoff_service.set_domain(session_id=session_id, domain=current_domain)

            with tracer.start_as_current_span("agent_evaluation_case") as span:
                span.set_attribute("eval.case_index", index)
                span.set_attribute("eval.expected_domain", expected_domain)
                span.set_attribute("eval.current_domain", current_domain)

                classification = handoff_service.classify_intent(
                    user_message=user_message,
                    session_id=session_id,
                    chat_history=None,
                )

            predicted_domain = str(classification.get("domain", "")).strip()
            is_correct = predicted_domain == expected_domain

            results.append(
                {
                    "id": case.get("id", str(index)),
                    "expected_domain": expected_domain,
                    "predicted_domain": predicted_domain,
                    "confidence": classification.get("confidence"),
                    "is_correct": is_correct,
                    "query": user_message,
                    "reasoning": classification.get("reasoning", ""),
                }
            )

    duration = round(perf_counter() - started, 2)
    total = len(results)
    correct = sum(1 for item in results if item["is_correct"])
    accuracy = (correct / total) if total else 0.0

    report = {
        "dataset": str(dataset_path),
        "total": total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracy": accuracy,
        "duration_seconds": duration,
        "results": results,
    }

    report_path = ARTIFACT_DIR / "agent_evaluation_report.json"
    with report_path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)

    print(f"Agent evaluation accuracy: {accuracy:.4f} ({correct}/{total})")
    print(f"Detailed report: {report_path}")

    threshold_raw = os.getenv("AGENT_EVAL_MIN_ACCURACY", "")
    if threshold_raw:
        threshold = float(threshold_raw)
        if accuracy < threshold:
            print(f"Agent evaluation failed threshold {threshold}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
