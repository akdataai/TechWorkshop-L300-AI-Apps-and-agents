import asyncio
import json
import os
from pathlib import Path
from typing import Any

from azure.ai.evaluation.red_team import AttackStrategy, RedTeam, RiskCategory
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

SRC_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = SRC_ROOT / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def get_required_env(name: str, fallback: str | None = None) -> str:
    value = os.getenv(name, fallback)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def to_jsonable(data: Any) -> Any:
    if hasattr(data, "model_dump"):
        return to_jsonable(data.model_dump())

    if hasattr(data, "as_dict"):
        return to_jsonable(data.as_dict())

    if isinstance(data, dict):
        return {key: to_jsonable(value) for key, value in data.items()}

    if isinstance(data, (list, tuple, set)):
        return [to_jsonable(item) for item in data]

    if isinstance(data, (str, int, float, bool)) or data is None:
        return data

    return str(data)


def parse_attack_strategies() -> list[Any]:
    configured = os.getenv("RED_TEAM_ATTACK_STRATEGIES", "").strip()
    if not configured:
        return [AttackStrategy.EASY]

    strategies: list[Any] = []
    for raw_name in configured.split(","):
        name = raw_name.strip()
        if not name:
            continue
        strategy = getattr(AttackStrategy, name, None)
        if strategy is None:
            raise ValueError(f"Unknown attack strategy: {name}")
        strategies.append(strategy)

    return strategies or [AttackStrategy.EASY]


def create_red_team_agent() -> RedTeam:
    azure_ai_project = get_required_env("FOUNDRY_ENDPOINT")
    custom_seed_prompts = os.getenv("RED_TEAM_CUSTOM_ATTACK_PROMPTS", "").strip()

    if custom_seed_prompts:
        return RedTeam(
            azure_ai_project=azure_ai_project,
            credential=DefaultAzureCredential(),
            custom_attack_seed_prompts=custom_seed_prompts,
        )

    return RedTeam(
        azure_ai_project=azure_ai_project,
        credential=DefaultAzureCredential(),
        risk_categories=[
            RiskCategory.Violence,
            RiskCategory.HateUnfairness,
            RiskCategory.Sexual,
            RiskCategory.SelfHarm,
        ],
        num_objectives=int(os.getenv("RED_TEAM_NUM_OBJECTIVES", "5")),
    )


async def main() -> int:
    red_team_agent = create_red_team_agent()

    azure_openai_config = {
        "azure_endpoint": get_required_env("gpt_endpoint"),
        "api_key": get_required_env("gpt_api_key", os.getenv("FOUNDRY_KEY")),
        "azure_deployment": get_required_env("gpt_deployment"),
    }

    scan_name = os.getenv("RED_TEAM_SCAN_NAME", "workshop-red-team-scan")
    attack_strategies = parse_attack_strategies()

    result = await red_team_agent.scan(
        target=azure_openai_config,
        scan_name=scan_name,
        attack_strategies=attack_strategies,
    )

    output_file = Path(
        os.getenv(
            "RED_TEAM_OUTPUT_FILE",
            str(ARTIFACT_DIR / "red_team_result.json"),
        )
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    serialized = to_jsonable(result)
    with output_file.open("w", encoding="utf-8") as result_file:
        json.dump(serialized, result_file, indent=2)

    print(f"Red team scan completed. Results saved to: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
