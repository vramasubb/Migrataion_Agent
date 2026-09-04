from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from mapper_loader import MapperLoader
from token_usage import build_token_report, print_token_summary


@dataclass
class ConversionResult:
    source: str
    output: str
    mapped_actions: int
    skipped_lines: int
    unmatched_lines: int
    action_ids: list[str]


def _typescript_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "").replace("\n", " ")


def convert_file(
    source_path: Path,
    output_path: Path,
    loader: MapperLoader,
    engine: str = "web",
    strict: bool = False,
) -> ConversionResult:
    mapped: list[str] = []
    unmatched: list[tuple[int, str]] = []
    skipped = 0
    action_ids: list[str] = []

    for line_number, source_line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = source_line.strip()
        if not stripped or loader.should_skip(source_line, engine):
            skipped += 1
            continue
        action = loader.match_action(engine, source_line, {"source": str(source_path), "line": line_number})
        if action:
            mapped.append(action["rendered"])
            action_ids.append(action["id"])
        else:
            unmatched.append((line_number, stripped))

    if strict and unmatched:
        details = "\n".join(f"  {line}: {text}" for line, text in unmatched)
        raise ValueError(f"Unmapped source lines in {source_path}:\n{details}")

    title = _typescript_string(source_path.stem)
    body = "\n".join(f"    {line}" for line in mapped) or "    // No mapped Selenium actions found."
    todo = "\n".join(
        f"    // TODO source line {line}: {_typescript_string(text)}" for line, text in unmatched
    )
    if todo:
        body = f"{body}\n\n{todo}"
    generated = (
        "import { test, expect } from '@playwright/test';\n\n"
        f"test.describe('{title}', () => {{\n"
        "  test('migrated Selenium flow', async ({ page }) => {\n"
        f"{body}\n"
        "  });\n"
        "});\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated, encoding="utf-8")
    return ConversionResult(
        source=str(source_path),
        output=str(output_path),
        mapped_actions=len(mapped),
        skipped_lines=skipped,
        unmatched_lines=len(unmatched),
        action_ids=action_ids,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Selenium Java statements to Playwright TypeScript")
    parser.add_argument("input", type=Path, help="Selenium Java source file")
    parser.add_argument("-o", "--output", type=Path, help="Generated Playwright spec path")
    parser.add_argument("--client", help="Client mapper overlay name")
    parser.add_argument("--engine", default="web", help="Technology engine (default: web)")
    parser.add_argument("--strict", action="store_true", help="Fail when any non-skipped line is unmapped")
    parser.add_argument("--report", type=Path, help="Write compact JSON conversion report")
    parser.add_argument("--agent-input-tokens", type=int, default=0)
    parser.add_argument("--agent-output-tokens", type=int, default=0)
    parser.add_argument("--model", default="claude-sonnet")
    parser.add_argument("--input-rate", type=float, default=3.0)
    parser.add_argument("--output-rate", type=float, default=15.0)
    args = parser.parse_args()

    loader = MapperLoader(client=args.client)
    errors = loader.validate()
    if errors:
        raise SystemExit("Mapper validation failed:\n- " + "\n- ".join(errors))
    output = args.output or Path("output") / f"{args.input.stem}.spec.ts"
    result = convert_file(args.input, output, loader, args.engine, args.strict)
    token_usage = build_token_report(
        [args.input],
        [output],
        args.agent_input_tokens,
        args.agent_output_tokens,
        args.model,
        args.input_rate,
        args.output_rate,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"file": asdict(result), "tokenUsage": token_usage}, indent=2) + "\n", encoding="utf-8")
    print(
        f"Converted {result.source} -> {result.output} "
        f"({result.mapped_actions} mapped, {result.unmatched_lines} unmatched)"
    )
    print_token_summary(token_usage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())