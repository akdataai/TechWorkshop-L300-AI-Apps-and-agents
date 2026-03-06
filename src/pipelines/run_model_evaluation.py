import contextlib
import json
import multiprocessing
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

try:
    from azure.ai.evaluation import (
        CoherenceEvaluator,
        RelevanceEvaluator,
        SimilarityEvaluator,
        evaluate,
    )
except ImportError as import_error:  # pragma: no cover
    raise RuntimeError(
        "Missing Azure AI Evaluation dependencies. Install requirements from src/requirements.txt"
    ) from import_error


SRC_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = SRC_ROOT / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def get_required_env(name: str, fallback: str | None = None) -> str:
    value = os.getenv(name, fallback)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_model_config() -> Dict[str, str]:
    return {
        "azure_endpoint": get_required_env("gpt_endpoint"),
        "api_key": get_required_env("gpt_api_key", os.getenv("FOUNDRY_KEY")),
        "azure_deployment": get_required_env("gpt_deployment"),
        "api_version": get_required_env("gpt_api_version", "2025-01-01-preview"),
    }


def build_openai_client(model_config: Dict[str, str]) -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=model_config["azure_endpoint"],
        api_key=model_config["api_key"],
        api_version=model_config["api_version"],
    )


def target_factory(client: AzureOpenAI, deployment: str):
    def model_target(query: str, context: str = "") -> Dict[str, str]:
        user_prompt = (
            f"Context:\n{context}\n\nQuestion:\n{query}\n\n"
            "Respond concisely and use the context when relevant."
        )
        completion = client.chat.completions.create(
            model=deployment,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful retail AI assistant.",
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        response = completion.choices[0].message.content or ""
        return {
            "response": response,
            "context": context,
        }

    return model_target


def main() -> int:
    with contextlib.suppress(RuntimeError):
        multiprocessing.set_start_method("spawn", force=True)

    model_config = build_model_config()
    client = build_openai_client(model_config)

    data_path = Path(os.getenv("MODEL_EVAL_DATASET", str(SRC_ROOT / "data" / "model_eval_dataset.jsonl")))
    output_path = Path(os.getenv("MODEL_EVAL_OUTPUT", str(ARTIFACT_DIR / "model_evaluation_results.json")))

    relevance_eval = RelevanceEvaluator(model_config=model_config)
    coherence_eval = CoherenceEvaluator(model_config=model_config)
    similarity_eval = SimilarityEvaluator(model_config=model_config)

    result = evaluate(
        data=str(data_path),
        target=target_factory(client=client, deployment=model_config["azure_deployment"]),
        evaluators={
            "relevance": relevance_eval,
            "coherence": coherence_eval,
            "similarity": similarity_eval,
        },
        evaluator_config={
            "relevance": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${outputs.response}",
                }
            },
            "coherence": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${outputs.response}",
                }
            },
            "similarity": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${outputs.response}",
                    "ground_truth": "${data.ground_truth}",
                }
            },
        },
        output_path=str(output_path),
        azure_ai_project=os.getenv("FOUNDRY_ENDPOINT"),
        evaluation_name="workshop-model-evaluation",
    )

    metrics = result.get("metrics", {})
    metrics_output = ARTIFACT_DIR / "model_evaluation_metrics.json"
    with metrics_output.open("w", encoding="utf-8") as metrics_file:
        json.dump(metrics, metrics_file, indent=2)

    print("Model evaluation metrics:")
    print(json.dumps(metrics, indent=2))
    print(f"Detailed results: {output_path}")

    threshold_raw = os.getenv("MODEL_EVAL_MIN_MEAN_SCORE", "")
    if threshold_raw:
        threshold = float(threshold_raw)
        numeric_metrics = [float(value) for value in metrics.values() if isinstance(value, (int, float))]
        if not numeric_metrics:
            raise RuntimeError("Model evaluation did not return numeric metrics for threshold checking")

        mean_score = sum(numeric_metrics) / len(numeric_metrics)
        print(f"Average numeric metric: {mean_score:.4f}")
        if mean_score < threshold:
            print(f"Model evaluation failed threshold {threshold}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
