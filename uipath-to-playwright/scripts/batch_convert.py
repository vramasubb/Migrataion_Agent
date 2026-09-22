from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from convert import convert_file
from mapper_loader import MapperError, MapperLoader
from token_usage import build_token_report, print_token_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch convert UiPath Studio (XAML) files")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--client")
    parser.add_argument("--engine", default="web")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--screenshots", help="Directory to capture a page.screenshot() after every UI action (evidence capture)")
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

    results = []
    failures = []
    source_paths = sorted(args.input_dir.rglob("*.xaml"))
    for source_path in source_paths:
        relative = source_path.relative_to(args.input_dir).with_suffix(".spec.ts")
        try:
            results.append(
                convert_file(source_path, args.output_dir / relative, loader, args.engine, args.strict, args.screenshots)
            )
        except (ET.ParseError, MapperError, ValueError) as error:
            failures.append({"source": str(source_path), "error": str(error)})

    token_usage = build_token_report(
        source_paths,
        (Path(result.output) for result in results),
        args.agent_input_tokens,
        args.agent_output_tokens,
        args.model,
        args.input_rate,
        args.output_rate,
    )
    report_path = args.output_dir / "migration-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {"files": [asdict(result) for result in results], "failures": failures, "tokenUsage": token_usage},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Converted {len(results)} file(s), {len(failures)} failure(s); report: {report_path}")
    for failure in failures:
        print(f"  FAILED {failure['source']}: {failure['error']}")
    print_token_summary(token_usage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
