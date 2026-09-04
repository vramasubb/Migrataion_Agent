from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable


TEXT_SUFFIXES = {
    ".feature",
    ".java",
    ".json",
    ".md",
    ".properties",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
}


def text_metrics(paths: Iterable[Path]) -> dict[str, int]:
    files = 0
    characters = 0
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            characters += len(path.read_text(encoding="utf-8"))
            files += 1
        except UnicodeDecodeError:
            continue
    return {
        "files": files,
        "characters": characters,
        "estimatedTokens": math.ceil(characters / 4),
    }


def build_token_report(
    source_paths: Iterable[Path],
    generated_paths: Iterable[Path],
    agent_input_tokens: int = 0,
    agent_output_tokens: int = 0,
    model: str = "claude-sonnet",
    input_rate_per_million: float = 3.0,
    output_rate_per_million: float = 15.0,
) -> dict[str, Any]:
    if agent_input_tokens < 0 or agent_output_tokens < 0:
        raise ValueError("Agent token counts cannot be negative")
    if input_rate_per_million < 0 or output_rate_per_million < 0:
        raise ValueError("Token rates cannot be negative")

    agent_cost = (
        agent_input_tokens * input_rate_per_million
        + agent_output_tokens * output_rate_per_million
    ) / 1_000_000
    return {
        "migrationConversion": {
            "execution": "local-python",
            "modelInvoked": False,
            "billableInputTokens": 0,
            "billableOutputTokens": 0,
            "estimatedCostUsd": 0.0,
        },
        "textEquivalentWorkload": {
            "source": text_metrics(source_paths),
            "generated": text_metrics(generated_paths),
            "estimationMethod": "characters/4",
            "billable": False,
        },
        "optionalAgentAssistance": {
            "model": model,
            "inputTokens": agent_input_tokens,
            "outputTokens": agent_output_tokens,
            "totalTokens": agent_input_tokens + agent_output_tokens,
            "inputRateUsdPerMillion": input_rate_per_million,
            "outputRateUsdPerMillion": output_rate_per_million,
            "estimatedCostUsd": round(agent_cost, 6),
            "usageSource": "user-supplied" if agent_input_tokens or agent_output_tokens else "not-supplied",
        },
        "totalKnownBillableTokens": agent_input_tokens + agent_output_tokens,
        "totalEstimatedCostUsd": round(agent_cost, 6),
        "note": "Text-equivalent workload is an estimate, not provider-billed token usage. Actual agent usage must come from the provider/API response.",
    }


def print_token_summary(report: dict[str, Any]) -> None:
    workload = report["textEquivalentWorkload"]
    assistance = report["optionalAgentAssistance"]
    print("Token usage summary")
    print("  Python migration model tokens: 0 input, 0 output ($0.000000)")
    print(
        "  Text-equivalent workload: "
        f"{workload['source']['estimatedTokens']} source + "
        f"{workload['generated']['estimatedTokens']} generated tokens "
        "(estimated, non-billable)"
    )
    print(
        "  Optional agent assistance: "
        f"{assistance['inputTokens']} input + {assistance['outputTokens']} output = "
        f"{assistance['totalTokens']} tokens (${assistance['estimatedCostUsd']:.6f})"
    )