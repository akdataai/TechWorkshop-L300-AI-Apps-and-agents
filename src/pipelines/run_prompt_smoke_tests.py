import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AzureOpenAI
from opentelemetry import trace
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

try:
    from azure.monitor.opentelemetry import configure_azure_monitor
except ImportError:
    configure_azure_monitor = None


load_dotenv()

SRC_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = SRC_ROOT / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def get_required_env(name: str, fallback: str | None = None) -> str:
    value = os.getenv(name, fallback)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def configure_tracing() -> None:
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if connection_string and configure_azure_monitor:
        configure_azure_monitor(connection_string=connection_string)
        OpenAIInstrumentor().instrument()


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as test_file:
        data = json.load(test_file)

    if not isinstance(data, list):
        raise ValueError("Prompt test file must contain a JSON array")

    return data


def call_model(client: AzureOpenAI, deployment: str, prompt: str) -> str:
    completion = client.chat.completions.create(
        model=deployment,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are Zava's shopping assistant.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    return completion.choices[0].message.content or ""


def run_case(client: AzureOpenAI, deployment: str, tracer: trace.Tracer, case: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(case.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Each prompt smoke test case requires a non-empty 'prompt'")

    expected_contains = case.get("expected_contains", [])
    if expected_contains is None:
        expected_contains = []

    if not isinstance(expected_contains, list):
        raise ValueError("'expected_contains' must be a list when provided")

    start = perf_counter()
    with tracer.start_as_current_span("prompt_smoke_test") as span:
        span.set_attribute("prompt.test_name", str(case.get("name", "unnamed")))
        span.set_attribute("prompt.length", len(prompt))

        response = call_model(client=client, deployment=deployment, prompt=prompt)
        response_lower = response.lower()

        checks = []
        for expected in expected_contains:
            expected_text = str(expected)
            checks.append(
                {
                    "expected": expected_text,
                    "matched": expected_text.lower() in response_lower,
                }
            )

        passed = bool(response.strip()) and all(item["matched"] for item in checks)
        duration = round(perf_counter() - start, 3)

        span.set_attribute("prompt.passed", passed)
        span.set_attribute("prompt.duration_seconds", duration)

    return {
        "name": case.get("name", "unnamed"),
        "prompt": prompt,
        "response": response,
        "checks": checks,
        "passed": passed,
        "duration_seconds": duration,
    }


def main() -> int:
    configure_tracing()
    tracer = trace.get_tracer(__name__)

    model_config = {
        "azure_endpoint": get_required_env("gpt_endpoint"),
        "api_key": get_required_env("gpt_api_key", os.getenv("FOUNDRY_KEY")),
        "azure_deployment": get_required_env("gpt_deployment"),
        "api_version": get_required_env("gpt_api_version", "2025-01-01-preview"),
    }

    test_file = Path(
        os.getenv(
            "PROMPT_TEST_DATASET",
            str(SRC_ROOT / "data" / "prompt_smoke_tests.json"),
        )
    )

    test_cases = load_test_cases(test_file)
    client = AzureOpenAI(
        azure_endpoint=model_config["azure_endpoint"],
        api_key=model_config["api_key"],
        api_version=model_config["api_version"],
    )

    results = [run_case(client, model_config["azure_deployment"], tracer, case) for case in test_cases]

    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    failed = total - passed

    report = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    report_path = ARTIFACT_DIR / "prompt_smoke_test_report.json"
    with report_path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)

    print(f"Prompt smoke test report written to: {report_path}")
    print(f"Passed: {passed}/{total}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
