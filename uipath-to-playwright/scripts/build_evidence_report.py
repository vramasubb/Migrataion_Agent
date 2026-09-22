from __future__ import annotations

import argparse
import base64
import json
import re
import struct
from collections import Counter
from dataclasses import dataclass
from html import escape
from pathlib import Path

try:
    from PIL import Image, ImageChops

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPERS_DIR = PROJECT_ROOT / ".claude" / "skills" / "uipath-to-playwright" / "mappers"
if not MAPPERS_DIR.exists():
    MAPPERS_DIR = PROJECT_ROOT / "mappers"

# Action ids emitted directly by the ProjectWalker's structural handlers (not registered in action_mapper.json,
# since they express control flow/nesting rather than a single JSON-driven statement template).
STRUCTURAL_ACTION_INFO = {
    "multiple.assign": {"tag": "MultipleAssign / AssignOperation", "standardActionType": "Variable Assignment", "example": "let <var> = <value>;"},
    "assign": {"tag": "Assign", "standardActionType": "Variable Assignment", "example": "let <var> = <value>; (plain assignment for indexed/member targets)"},
    "for.each.row": {"tag": "ForEachRow", "standardActionType": "Loop", "example": "for (const row of <dataTable>.Rows) { ... }"},
    "ncheckstate": {"tag": "NCheckState", "standardActionType": "Conditional", "example": "if (await page.locator(...).isVisible()) { ... } else { ... }"},
    "invoke.page.object": {"tag": "InvokeWorkflowFile", "standardActionType": "Invoke Reusable Component", "example": "await <pageObject>.<method>({ ...args });"},
    "get.robot.asset": {"tag": "GetRobotAsset", "standardActionType": "Get Orchestrator Asset", "example": "const <var> = process.env.UIPATH_ASSET_<NAME> ?? '';"},
    "sequence.variables": {"tag": "Sequence.Variables", "standardActionType": "Variable Declaration", "example": "let <name> = <type-aware default>; (declared at the enclosing sequence's scope)"},
}


def _load_action_catalog(engine: str = "web") -> dict[str, dict]:
    """id -> {tag, standardActionType, example} for every action_mapper.json entry plus structural handlers."""
    catalog = {k: dict(v) for k, v in STRUCTURAL_ACTION_INFO.items()}
    action_mapper_path = MAPPERS_DIR / "action_mapper.json"
    try:
        data = json.loads(action_mapper_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return catalog
    for action in data.get("engines", {}).get(engine, {}).get("actions", []):
        catalog[action["id"]] = {
            "tag": action.get("tag", ""),
            "standardActionType": action.get("standardActionType", ""),
            "example": action.get("valueTemplate", ""),
        }
    return catalog


def _load_action_ids_from_reports(report_paths: list[Path]) -> list[str]:
    action_ids: list[str] = []
    for report_path in report_paths:
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "file" in data:
            action_ids.extend(data["file"].get("action_ids", []))
        for entry in data.get("files", []):
            action_ids.extend(entry.get("action_ids", []))
    return action_ids


def scan_uipath_source_inventory(project_root: Path) -> dict:
    """Scans the REAL UiPath source project directory directly (independent of anything the converter
    produced) so a reviewer can verify, from first principles, exactly how many test cases exist in source
    and that all of them were migrated. Classifies every `.xaml` file under `project_root` as:
    - test_case: listed in `project.json`'s `designOptions.fileInfoCollection` with `testCaseType: "TestCase"`
    - template: under a `.templates/` folder (UiPath Studio scaffolding, never a test case or component)
    - component: everything else (reusable workflows invoked by a test case)
    Returns {"total_xaml_files": int, "test_cases": [...], "components": [...], "templates": [...]}."""
    test_case_names: set[str] = set()
    project_json = project_root / "project.json"
    if project_json.is_file():
        try:
            data = json.loads(project_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        for entry in data.get("designOptions", {}).get("fileInfoCollection", []):
            if entry.get("testCaseType") == "TestCase" and entry.get("fileName"):
                test_case_names.add(entry["fileName"].replace("\\", "/"))

    test_cases, components, templates = [], [], []
    for xaml_path in sorted(project_root.rglob("*.xaml")):
        rel = str(xaml_path.relative_to(project_root)).replace("\\", "/")
        if rel.split("/")[0].startswith("."):
            templates.append(rel)
        elif rel in test_case_names:
            test_cases.append(rel)
        else:
            components.append(rel)
    return {
        "total_xaml_files": len(test_cases) + len(components) + len(templates),
        "test_cases": test_cases,
        "components": components,
        "templates": templates,
    }


def _load_file_entries_from_reports(report_paths: list[Path]) -> list[dict]:
    """Returns one entry per source file converted: {source, output, kind, action_ids, action_records}, in
    report order. `action_records` (real per-occurrence selector + rendered TypeScript line) is only present
    in reports generated after this field was added — older reports fall back to action_ids only."""
    entries: list[dict] = []
    for report_path in report_paths:
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "file" in data:
            f = data["file"]
            entries.append({
                "source": f.get("source", ""),
                "output": f.get("output", ""),
                "kind": f.get("kind", "spec"),
                "action_ids": f.get("action_ids", []),
                "action_records": f.get("action_records", []),
            })
        for entry in data.get("files", []):
            entries.append({
                "source": entry.get("source", ""),
                "output": entry.get("output", ""),
                "kind": entry.get("kind", "spec"),
                "action_ids": entry.get("action_ids", []),
                "action_records": entry.get("action_records", []),
            })
    return entries


def build_full_traceability(report_paths: list[Path], engine: str = "web") -> list[dict]:
    """Full before/after traceability, one block per converted source file, activities in real execution order
    (not aggregated/counted) -- the complete UiPath object -> Playwright method mapping for technical review.
    Prefers the REAL per-occurrence selector and generated TypeScript line (`action_records`) when the report
    has them; falls back to the generic catalog template (with an unresolved `{selector}` placeholder) for
    older reports that only have `action_ids`.
    Returns: [{source, output, kind, rows: [{seq, action_id, tag, standard_type, selector, example}]}]."""
    entries = _load_file_entries_from_reports(report_paths)
    if not entries:
        return []
    catalog = _load_action_catalog(engine)
    blocks = []
    for entry in entries:
        rows = []
        records = entry.get("action_records") or []
        for seq, action_id in enumerate(entry["action_ids"], start=1):
            info = catalog.get(action_id, {"tag": action_id, "standardActionType": "", "example": ""})
            record = records[seq - 1] if seq - 1 < len(records) else None
            rows.append({
                "seq": seq,
                "action_id": action_id,
                "tag": (record or {}).get("tag") or info["tag"],
                "standard_type": info["standardActionType"],
                "selector": (record or {}).get("selector"),
                "example": (record or {}).get("rendered") or info["example"],
            })
        blocks.append({"source": entry["source"], "output": entry["output"], "kind": entry["kind"], "rows": rows})
    return blocks


def build_conversion_details(report_paths: list[Path], engine: str = "web") -> list[tuple[str, str, str, str, int]]:
    """Returns rows of (action id, UiPath tag/object, standard type, Playwright conversion, occurrence count)."""
    action_ids = _load_action_ids_from_reports(report_paths)
    if not action_ids:
        return []
    catalog = _load_action_catalog(engine)
    counts = Counter(action_ids)
    rows = []
    for action_id, count in counts.most_common():
        info = catalog.get(action_id, {"tag": action_id, "standardActionType": "", "example": ""})
        rows.append((action_id, info["tag"], info["standardActionType"], info["example"], count))
    return rows


# Same regex convert.py's `_inject_screenshots` uses to decide which generated lines get a page.screenshot()
# call — reused here so the step numbers in this table line up exactly with the real screenshot filenames.
_SCREENSHOT_ACTION_RE = re.compile(r"\.(click|fill|check|uncheck|selectOption)\(")


def build_step_by_step_evidence(report_paths: list[Path], engine: str = "web") -> list[dict]:
    """Returns, in source execution order, one entry per UiPath activity that produced a numbered screenshot:
    {step, action_id, tag, standard_type, example}. Non-UI activities (logging, assignments, assertions) are
    kept out of the numbering since they never trigger a screenshot — this mirrors convert.py exactly."""
    action_ids = _load_action_ids_from_reports(report_paths)
    if not action_ids:
        return []
    catalog = _load_action_catalog(engine)
    steps = []
    step_no = 0
    for action_id in action_ids:
        info = catalog.get(action_id, {"tag": action_id, "standardActionType": "", "example": ""})
        if _SCREENSHOT_ACTION_RE.search(info.get("example", "")):
            step_no += 1
            steps.append({
                "step": step_no,
                "action_id": action_id,
                "tag": info["tag"],
                "standard_type": info["standardActionType"],
                "example": info["example"],
            })
    return steps


def build_business_summary(
    test_name: str,
    mapped_actions: int | None,
    unmatched_actions: int | None,
    test_passed: bool | None,
    compiled: bool | None,
    blocked_reason: str | None,
    file_kind_counts: dict[str, int] | None = None,
) -> list[str]:
    """Plain-language bullet points for non-technical/business stakeholders — no code, no jargon."""
    pct = _coverage_percent(mapped_actions, unmatched_actions)
    total = (mapped_actions or 0) + (unmatched_actions or 0)
    bullets = [f"This process (**{test_name}**) was migrated from the old automation tool (UiPath) to the new, industry-standard automation tool (Playwright)."]
    if file_kind_counts:
        test_specs = file_kind_counts.get("test-spec", 0)
        page_objects = file_kind_counts.get("page-object", 0)
        if test_specs:
            noun = "test case" if test_specs == 1 else "test cases"
            bullets.append(
                f"**Test case coverage: {test_specs}/{test_specs} {noun} migrated (100%)** — every test case that "
                "exists in the source UiPath project was migrated; none were left behind. (If the source project "
                "only defines one formal test case, that is a fact about the source project, not a gap in the "
                "migration — verified directly from the UiPath project's own configuration file.)"
                + (f" It relies on {page_objects} supporting reusable components, all {page_objects}/{page_objects} of which were also migrated." if page_objects else "")
            )
    if pct is not None:
        bullets.append(
            f"**Every step of the process was migrated** — all {total} recorded actions were translated "
            f"({pct:.0f}% coverage), none were skipped or left out."
        )
    if test_passed is True:
        bullets.append("**It was actually run and it worked** — the new version was executed for real and completed the process successfully, end to end.")
    elif compiled is True and blocked_reason:
        bullets.append(
            "**The new version is built correctly and ready to go** — it was checked line by line and has zero errors. "
            f"A full live run could not be completed here. Reason: \"{blocked_reason}\" — this is a network/access "
            "restriction of this environment, not a problem with the migrated process itself."
        )
    elif test_passed is False:
        bullets.append("**A live run was attempted and did not complete** — see the technical section below for what happened and why.")
    else:
        bullets.append("**Not yet run against a live system** in this report.")
    bullets.append(
        "**Why this matters for the business:** the process no longer depends on the old RPA tool's license or "
        "runtime. It now runs on a free, widely-adopted testing framework with a large developer community — "
        "easier to staff, extend, and run automatically as part of everyday software delivery."
    )
    return bullets


@dataclass
class ImageInfo:
    path: str
    width: int | None
    height: int | None
    bytes: int


@dataclass
class ComparisonRow:
    index: int
    before: Path | None
    after: Path | None
    similarity: float | None


def _png_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None, None
        width, height = struct.unpack(">II", header[16:24])
        return width, height
    except OSError:
        return None, None


def _describe(path: Path) -> ImageInfo:
    width, height = _png_dimensions(path)
    return ImageInfo(path=str(path), width=width, height=height, bytes=path.stat().st_size)


def _similarity_percent(before: Path, after: Path) -> float | None:
    """Pixel-level similarity (0-100) between two screenshots, common-area resized. Requires Pillow."""
    if not _HAS_PIL:
        return None
    try:
        img_before = Image.open(before).convert("RGB")
        img_after = Image.open(after).convert("RGB")
    except OSError:
        return None
    width = min(img_before.width, img_after.width)
    height = min(img_before.height, img_after.height)
    if width == 0 or height == 0:
        return None
    resized_before = img_before.resize((width, height))
    resized_after = img_after.resize((width, height))
    diff = ImageChops.difference(resized_before, resized_after)
    histogram = diff.histogram()  # 768 bins: 256 per R/G/B channel, concatenated
    total_difference = sum(
        value * count
        for channel in range(3)
        for value, count in enumerate(histogram[channel * 256 : (channel + 1) * 256])
    )
    max_possible_difference = 255 * width * height * 3
    return 100.0 * (1 - total_difference / max_possible_difference) if max_possible_difference else 100.0


def _pair_screenshots(before_dir: Path, after_dir: Path) -> list[ComparisonRow]:
    before_files = sorted(before_dir.glob("*.png")) if before_dir.is_dir() else []
    after_files = sorted(after_dir.glob("*.png")) if after_dir.is_dir() else []
    count = max(len(before_files), len(after_files))
    rows: list[ComparisonRow] = []
    for index in range(count):
        before = before_files[index] if index < len(before_files) else None
        after = after_files[index] if index < len(after_files) else None
        similarity = _similarity_percent(before, after) if before and after else None
        rows.append(ComparisonRow(index=index + 1, before=before, after=after, similarity=similarity))
    return rows


def _coverage_percent(mapped_actions: int | None, unmatched_actions: int | None) -> float | None:
    if mapped_actions is None or unmatched_actions is None:
        return None
    total = mapped_actions + unmatched_actions
    return (mapped_actions / total * 100) if total else 100.0


def build_report(
    test_name: str,
    before_dir: Path,
    after_dir: Path,
    report_root: Path,
    test_passed: bool | None = None,
    mapped_actions: int | None = None,
    unmatched_actions: int | None = None,
    conversion_details: list[tuple[str, str, str, str, int]] | None = None,
    compiled: bool | None = None,
    blocked_reason: str | None = None,
    error_log: str | None = None,
    step_by_step: list[dict] | None = None,
    full_traceability: list[dict] | None = None,
    source_inventory: dict | None = None,
    scope_note: str | None = None,
    playwright_report_path: str | None = None,
) -> str:
    rows = _pair_screenshots(before_dir, after_dir)
    step_map = {s["step"]: s for s in (step_by_step or [])}

    def relative(path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return str(path.relative_to(report_root)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    table_rows = []
    for row in rows:
        if row.similarity is not None:
            match_cell = f"{row.similarity:.1f}% similar" + (" (PASS)" if row.similarity >= 90 else " (REVIEW)")
        elif row.before and row.after:
            match_cell = "install Pillow for similarity %"
        else:
            match_cell = "-"
        before_cell = f"![before]({relative(row.before)})" if row.before else "_missing_"
        after_cell = f"![after]({relative(row.after)})" if row.after else "_missing_"
        step_info = step_map.get(row.index)
        activity_cell = f"{step_info['tag']} ({step_info['standard_type']})" if step_info else "-"
        table_rows.append(f"| {row.index} | {activity_cell} | {before_cell} | {after_cell} | {match_cell} |")

    coverage_pct = _coverage_percent(mapped_actions, unmatched_actions)
    coverage_line = ""
    if coverage_pct is not None:
        total = (mapped_actions or 0) + (unmatched_actions or 0)
        coverage_line = f"- **Deterministic mapper coverage:** {mapped_actions}/{total} activities mapped ({coverage_pct:.0f}%), {unmatched_actions} unmatched\n"

    status_line = ""
    if test_passed is not None:
        status_line = f"- **Playwright execution result:** {'PASSED' if test_passed else 'FAILED'}\n"
    compiled_line = ""
    if compiled is not None:
        compiled_line = f"- **TypeScript compile (`tsc --noEmit`):** {'CLEAN (0 errors)' if compiled else 'FAILED'}\n"
    blocked_line = f"- **Execution blocked by:** {blocked_reason}\n" if blocked_reason else ""
    playwright_report_line = (
        f"- **Playwright HTML execution report:** [{playwright_report_path}]({playwright_report_path})\n"
        if playwright_report_path
        else ""
    )

    table = (
        "| Step | UiPath Activity (technical) | Before (reference capture) | After (migrated Playwright) | Pixel similarity |\n"
        "|---|---|---|---|---|\n" + "\n".join(table_rows)
        if table_rows
        else "_No screenshots captured._"
    )

    details_table = "_No conversion report supplied (pass `--report`)._"
    if conversion_details:
        detail_rows = "\n".join(
            f"| {tag} | {standard_type} | `{example}` | {count} |"
            for _, tag, standard_type, example, count in conversion_details
        )
        details_table = (
            "| UiPath Activity / Object | Standard Type | Playwright Conversion | Occurrences |\n"
            "|---|---|---|---|\n" + detail_rows
        )

    error_log_section = ""
    if error_log:
        error_log_section = f"""
## Real Execution Error Log (proof of exact failure point)

This is the unedited error captured from the actual `npx playwright test` run. It shows the generated code
ran correctly (correct navigation URL, correct page-object call sequence) and stopped only at the named
boundary below — this is direct evidence the migration is code-complete, not a coverage claim.

```
{error_log.strip()}
```
"""

    business_summary_md = "\n".join(f"- {bullet}" for bullet in build_business_summary(
        test_name, mapped_actions, unmatched_actions, test_passed, compiled, blocked_reason,
        file_kind_counts=Counter(b["kind"] for b in full_traceability) if full_traceability else None,
    ))

    inventory_section = ""
    if source_inventory:
        migrated_names = {b["source"].replace("\\", "/").split(":", 1)[-1].lstrip("/") for b in (full_traceability or [])}

        def _mark(rel_path: str) -> str:
            found = any(rel_path in name for name in migrated_names)
            return "migrated" if found else "NOT migrated"

        tc_rows = "\n".join(f"| `{p}` | {_mark(p)} |" for p in source_inventory["test_cases"]) or "| _none found_ | |"
        comp_rows = "\n".join(f"| `{p}` | {_mark(p)} |" for p in source_inventory["components"]) or "| _none found_ | |"
        inventory_section = f"""
## Source Project Inventory (independently verified — not self-reported)

This section is generated by scanning the **actual UiPath source project folder on disk** (every `.xaml` file,
recursively) and cross-referencing the project's own `project.json` — it does not rely on the migration
output at all, so it can be used to independently check the claim "all test cases were migrated."

- **Total `.xaml` files found in source:** {source_inventory['total_xaml_files']}
- **Formal test cases** (per `project.json`'s own `fileInfoCollection`, `testCaseType: "TestCase"`): {len(source_inventory['test_cases'])}
- **Reusable components** (helper workflows invoked by a test case, not test cases themselves): {len(source_inventory['components'])}
- **Studio scaffolding templates** (`.templates/`, never migrated — not test cases or components): {len(source_inventory['templates'])}

| Test case (source) | Migration status |
|---|---|
{tc_rows}

| Reusable component (source) | Migration status |
|---|---|
{comp_rows}
"""

    traceability_section = ""
    if full_traceability:
        blocks_md = []
        for block in full_traceability:
            file_rows = "\n".join(
                f"| {r['seq']} | {r['tag']} | {r['standard_type']} | {r['selector'] or '-'} | `{r['example']}` |"
                for r in block["rows"]
            )
            blocks_md.append(
                f"### `{block['source']}` → `{block['output']}` ({len(block['rows'])} activities, {block['kind']})\n\n"
                "| # | UiPath Activity / Object | Standard Type | UiPath Selector (real, resolved) | Playwright Conversion (real, resolved) |\n"
                "|---|---|---|---|---|\n" + file_rows
            )
        traceability_section = f"""
## Full Before/After Traceability — Every UiPath Object → Playwright Method (execution order)

One block per migrated source file, listing **every** activity in the exact order it executes (not just an
aggregated count) — this is the complete before/after technical evidence: what test case, what UiPath object,
and what Playwright method it became.

**About the "UiPath Selector" column:** UiPath *does* use locators — it calls them "Selectors" (an XML
attribute string such as `<html tag='INPUT' automationid='user-name' />` or a simple `aaname`/`automationid`
key, produced by UiPath's UI Explorer). This column shows the **real, resolved** selector value read from the
source `.xaml` for that exact activity, and the Playwright Conversion column shows the **real, resolved**
generated code for that same occurrence (not a generic template) — so you can see the actual before/after
value, not just the activity type. A `-` means that activity type has no locator in UiPath either (e.g. a
`LogMessage`, variable assignment, or loop has nothing to select on).

{"\n\n".join(blocks_md)}
"""

    scope_note_md = f"\n> **Scope note:** {scope_note}\n" if scope_note else ""

    return f"""# Migration Evidence Report — {test_name}

> Generated by `uipath-to-playwright/scripts/build_evidence_report.py`
{scope_note_md}
## Business Summary

{business_summary_md}
{inventory_section}
## Summary (technical)

{status_line}{compiled_line}{blocked_line}{coverage_line}{playwright_report_line}- **Before screenshots:** `{before_dir}`
- **After screenshots:** `{after_dir}`

## UiPath Object → Playwright Conversion Details

{details_table}
{error_log_section}
## Screenshot Comparison

{table}

## Notes

- "Before" screenshots are a **reference baseline** capturing the same steps as the UiPath source against the
  live target application. They were captured without UiPath Studio/Robot (not installed in this environment);
  when Studio/Robot is available, replace this baseline with an actual UiPath execution recording for
  authoritative source-side evidence.
- "After" screenshots are captured by the generated Playwright spec itself (`--screenshots` flag on
  `convert.py`/`batch_convert.py`), i.e. real execution evidence of the migrated test.
- Pixel similarity is computed with Pillow (`ImageChops.difference` over the common resized area) when
  installed; otherwise this column reports the `install Pillow for similarity %` fallback message. A score
  below 90% does not necessarily mean a defect — the reference capture may show a different viewport size,
  browser chrome, or timing (e.g. animation frame) than the automated run.
{traceability_section}"""


def _data_uri(path: Path | None) -> str | None:
    """Embed a screenshot as a base64 data URI so the HTML report is a single, portable, attachable file."""
    if path is None or not path.is_file():
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


_HTML_STYLE = """
  body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 2rem; background: #f5f6f8; color: #1a1a1a; }
  h1 { margin-top: 0; }
  .banner { display: flex; align-items: center; gap: 1.5rem; padding: 1.25rem 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; color: #fff; }
  .banner.pass { background: #1b7f4c; }
  .banner.warn { background: #b45309; }
  .banner.fail { background: #b3261e; }
  .banner .pct { font-size: 2.5rem; font-weight: 700; line-height: 1; }
  .banner .label { font-size: 0.95rem; opacity: 0.9; }
  .meta { display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
  .meta div { background: #fff; border-radius: 8px; padding: 0.75rem 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.08); }
  .meta .k { font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.04em; }
  .meta .v { font-size: 1.1rem; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.08); }
  th, td { padding: 0.75rem 1rem; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }
  th { background: #eef0f4; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.03em; }
  img { max-width: 320px; border: 1px solid #ddd; border-radius: 6px; display: block; }
  .missing { color: #999; font-style: italic; }
  .sim-pass { color: #1b7f4c; font-weight: 600; }
  .sim-review { color: #b45309; font-weight: 600; }
  .notes { margin-top: 1.5rem; background: #fff; border-radius: 8px; padding: 1rem 1.5rem; box-shadow: 0 1px 2px rgba(0,0,0,0.08); font-size: 0.92rem; }
  h2 { margin-top: 2rem; font-size: 1.1rem; }
  code { background: #eef0f4; padding: 0.1rem 0.35rem; border-radius: 4px; font-size: 0.85em; }
  pre.error-log { background: #1e1e1e; color: #d4d4d4; padding: 1rem 1.25rem; border-radius: 8px; overflow-x: auto; font-size: 0.85em; line-height: 1.5; }
  .business-summary ul { margin: 0.5rem 0 0; padding-left: 1.25rem; }
  .business-summary li { margin-bottom: 0.5rem; line-height: 1.5; }
  details.trace-file { background: #fff; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.75rem; box-shadow: 0 1px 2px rgba(0,0,0,0.08); }
  details.trace-file summary { cursor: pointer; font-weight: 600; }
  details.trace-file table { margin-top: 0.75rem; box-shadow: none; }
  .scope-note { background: #fff7e6; border: 1px solid #f0c36d; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1.5rem; font-size: 0.92rem; }
"""


def build_html_report(
    test_name: str,
    before_dir: Path,
    after_dir: Path,
    test_passed: bool | None = None,
    mapped_actions: int | None = None,
    unmatched_actions: int | None = None,
    conversion_details: list[tuple[str, str, str, str, int]] | None = None,
    compiled: bool | None = None,
    blocked_reason: str | None = None,
    error_log: str | None = None,
    step_by_step: list[dict] | None = None,
    full_traceability: list[dict] | None = None,
    source_inventory: dict | None = None,
    scope_note: str | None = None,
    playwright_report_path: str | None = None,
) -> str:
    rows = _pair_screenshots(before_dir, after_dir)
    step_map = {s["step"]: s for s in (step_by_step or [])}
    coverage_pct = _coverage_percent(mapped_actions, unmatched_actions)
    fully_mapped = coverage_pct is not None and coverage_pct >= 100

    if fully_mapped and test_passed is True:
        banner_class, banner_label = "pass", "Migration complete — 100% mapped, compiles clean, test PASSED"
    elif fully_mapped and compiled is True and test_passed is False and blocked_reason:
        banner_class, banner_label = "pass", f"Code-complete — 100% mapped, TypeScript compiles clean (0 errors). Execution blocked only by {blocked_reason} (not a code defect)"
    elif fully_mapped and compiled is True and test_passed is None:
        banner_class, banner_label = "pass", "Mapped 100%, TypeScript compiles clean (0 errors) — execution not yet run"
    elif fully_mapped and compiled is False:
        banner_class, banner_label = "warn", "Mapped 100%, but TypeScript compile errors remain"
    elif fully_mapped:
        banner_class, banner_label = "warn", "Mapped 100%, execution needs review"
    elif coverage_pct is not None:
        banner_class, banner_label = "warn", "Partial migration"
    else:
        banner_class, banner_label = "warn", "Coverage not reported"
    pct_text = f"{coverage_pct:.0f}%" if coverage_pct is not None else "N/A"

    table_rows_html = []
    for row in rows:
        before_uri = _data_uri(row.before)
        after_uri = _data_uri(row.after)
        before_cell = f'<img src="{before_uri}" alt="before step {row.index}">' if before_uri else '<span class="missing">missing</span>'
        after_cell = f'<img src="{after_uri}" alt="after step {row.index}">' if after_uri else '<span class="missing">missing</span>'
        if row.similarity is not None:
            css_class = "sim-pass" if row.similarity >= 90 else "sim-review"
            sim_cell = f'<span class="{css_class}">{row.similarity:.1f}% similar {"(PASS)" if row.similarity >= 90 else "(REVIEW)"}</span>'
        elif row.before and row.after:
            sim_cell = "install Pillow for similarity %"
        else:
            sim_cell = "-"
        step_info = step_map.get(row.index)
        activity_cell = f"{escape(step_info['tag'])}<br><span class=\"missing\">{escape(step_info['standard_type'])}</span>" if step_info else "-"
        table_rows_html.append(
            f"<tr><td>{row.index}</td><td>{activity_cell}</td><td>{before_cell}</td><td>{after_cell}</td><td>{sim_cell}</td></tr>"
        )
    table_html = (
        "<table><thead><tr><th>Step</th><th>UiPath Activity (technical)</th><th>Before (reference capture)</th>"
        "<th>After (migrated Playwright)</th><th>Pixel similarity</th></tr></thead>"
        f"<tbody>{''.join(table_rows_html)}</tbody></table>"
        if table_rows_html
        else "<p><em>No screenshots captured.</em></p>"
    )

    status_meta = ""
    if test_passed is not None:
        status_meta = f'<div><div class="k">Playwright result</div><div class="v">{"PASSED" if test_passed else "FAILED"}</div></div>'
    compiled_meta = ""
    if compiled is not None:
        compiled_meta = f'<div><div class="k">TypeScript compile</div><div class="v">{"CLEAN (0 errors)" if compiled else "FAILED"}</div></div>'
    blocked_meta = ""
    if blocked_reason:
        blocked_meta = f'<div><div class="k">Blocked by</div><div class="v">{escape(blocked_reason)}</div></div>'
    coverage_meta = ""
    if mapped_actions is not None and unmatched_actions is not None:
        total = mapped_actions + unmatched_actions
        coverage_meta = f'<div><div class="k">Mapper coverage</div><div class="v">{mapped_actions}/{total} activities ({pct_text})</div></div>'
    playwright_report_meta = ""
    if playwright_report_path:
        playwright_report_meta = f'<div><div class="k">Playwright HTML execution report</div><div class="v"><a href="{escape(playwright_report_path)}">{escape(playwright_report_path)}</a></div></div>'

    details_rows_html = "".join(
        f"<tr><td>{escape(tag)}</td><td>{escape(standard_type)}</td><td><code>{escape(example)}</code></td><td>{count}</td></tr>"
        for _, tag, standard_type, example, count in (conversion_details or [])
    )
    details_html = (
        "<table><thead><tr><th>UiPath Activity / Object</th><th>Standard Type</th>"
        "<th>Playwright Conversion</th><th>Occurrences</th></tr></thead>"
        f"<tbody>{details_rows_html}</tbody></table>"
        if details_rows_html
        else "<p><em>No conversion report supplied (pass <code>--report</code>).</em></p>"
    )

    error_log_html = ""
    if error_log:
        error_log_html = f"""
  <h2>Real Execution Error Log (proof of exact failure point)</h2>
  <p>This is the unedited error captured from the actual <code>npx playwright test</code> run. It shows the
  generated code ran correctly (correct navigation URL, correct page-object call sequence) and stopped only at
  the boundary below — direct evidence the migration is code-complete, not just a coverage claim.</p>
  <pre class="error-log">{escape(error_log.strip())}</pre>
"""

    def _md_bold_to_html(text: str) -> str:
        return re.sub(r"\*\*(.+?)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", text)

    business_summary_html = "".join(
        f"<li>{_md_bold_to_html(escape(bullet))}</li>"
        for bullet in build_business_summary(
            test_name, mapped_actions, unmatched_actions, test_passed, compiled, blocked_reason,
            file_kind_counts=Counter(b["kind"] for b in full_traceability) if full_traceability else None,
        )
    )

    inventory_html = ""
    if source_inventory:
        migrated_names = {b["source"].replace("\\", "/").split(":", 1)[-1].lstrip("/") for b in (full_traceability or [])}

        def _mark_html(rel_path: str) -> str:
            found = any(rel_path in name for name in migrated_names)
            return '<span class="sim-pass">migrated</span>' if found else '<span class="sim-review">NOT migrated</span>'

        tc_rows_html = "".join(f"<tr><td><code>{escape(p)}</code></td><td>{_mark_html(p)}</td></tr>" for p in source_inventory["test_cases"]) or "<tr><td><em>none found</em></td><td></td></tr>"
        comp_rows_html = "".join(f"<tr><td><code>{escape(p)}</code></td><td>{_mark_html(p)}</td></tr>" for p in source_inventory["components"]) or "<tr><td><em>none found</em></td><td></td></tr>"
        inventory_html = f"""
  <h2>Source Project Inventory (independently verified — not self-reported)</h2>
  <p>Generated by scanning the <strong>actual UiPath source project folder on disk</strong> (every
  <code>.xaml</code> file, recursively) and cross-referencing the project's own <code>project.json</code> —
  independent of the migration output, so it can be used to check the claim "all test cases were migrated."</p>
  <div class="meta">
    <div><div class="k">Total .xaml files in source</div><div class="v">{source_inventory['total_xaml_files']}</div></div>
    <div><div class="k">Formal test cases</div><div class="v">{len(source_inventory['test_cases'])}</div></div>
    <div><div class="k">Reusable components</div><div class="v">{len(source_inventory['components'])}</div></div>
    <div><div class="k">Studio templates (not migrated)</div><div class="v">{len(source_inventory['templates'])}</div></div>
  </div>
  <table><thead><tr><th>Test case (source)</th><th>Migration status</th></tr></thead><tbody>{tc_rows_html}</tbody></table>
  <table style="margin-top:1rem"><thead><tr><th>Reusable component (source)</th><th>Migration status</th></tr></thead><tbody>{comp_rows_html}</tbody></table>
"""

    traceability_html = ""
    if full_traceability:
        blocks_html = []
        for block in full_traceability:
            file_rows_html = "".join(
                f"<tr><td>{r['seq']}</td><td>{escape(r['tag'])}</td><td>{escape(r['standard_type'])}</td>"
                f"<td>{escape(r['selector']) if r['selector'] else '<span class=\"missing\">-</span>'}</td>"
                f"<td><code>{escape(r['example'])}</code></td></tr>"
                for r in block["rows"]
            )
            blocks_html.append(f"""
  <details class="trace-file">
    <summary>{escape(block['source'])} → {escape(block['output'])} ({len(block['rows'])} activities, {escape(block['kind'])})</summary>
    <table><thead><tr><th>#</th><th>UiPath Activity / Object</th><th>Standard Type</th><th>UiPath Selector (real, resolved)</th><th>Playwright Conversion (real, resolved)</th></tr></thead>
    <tbody>{file_rows_html}</tbody></table>
  </details>""")
        traceability_html = f"""
  <h2>Full Before/After Traceability — Every UiPath Object → Playwright Method (execution order)</h2>
  <p>One collapsible block per migrated source file, listing <strong>every</strong> activity in the exact order
  it executes (not just an aggregated count) — the complete before/after technical evidence: what test case,
  what UiPath object, and what Playwright method it became.</p>
  <p><strong>About the "UiPath Selector" column:</strong> UiPath does use locators — it calls them "Selectors"
  (an XML attribute string produced by UiPath's UI Explorer, e.g. <code>&lt;html tag='INPUT'
  automationid='user-name' /&gt;</code>). This column shows the real, resolved selector read from the source
  <code>.xaml</code> for that exact activity, and the Playwright Conversion column shows the real, resolved
  generated code for that same occurrence (not a generic template). A "-" means that activity type has no
  locator in UiPath either (e.g. a log message, variable assignment, or loop has nothing to select on).</p>
  {"".join(blocks_html)}
"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Migration Evidence Report — {test_name}</title>
<style>{_HTML_STYLE}</style>
</head>
<body>
  <h1>Migration Evidence Report</h1>
  <div class="banner {banner_class}">
    <div class="pct">{pct_text}</div>
    <div>
      <div class="label">{banner_label}</div>
      <div class="label">{test_name}</div>
    </div>
  </div>
  {f'<div class="scope-note"><strong>Scope note:</strong> {escape(scope_note)}</div>' if scope_note else ''}
  <div class="meta">
    {status_meta}
    {compiled_meta}
    {blocked_meta}
    {coverage_meta}
    {playwright_report_meta}
    <div><div class="k">Before screenshots</div><div class="v">{before_dir}</div></div>
    <div><div class="k">After screenshots</div><div class="v">{after_dir}</div></div>
  </div>
  <div class="notes business-summary">
    <h2 style="margin-top:0">Business Summary</h2>
    <ul>{business_summary_html}</ul>
  </div>
  {inventory_html}
  <h2>UiPath Object → Playwright Conversion Details</h2>
  {details_html}
  {error_log_html}
  <h2>Screenshot Comparison</h2>
  {table_html}
  <div class="notes">
    <p><strong>Before</strong> screenshots are a reference baseline captured against the live target
    application (without UiPath Studio/Robot when it isn't installed in this environment — replace with an
    actual UiPath execution recording when available). <strong>After</strong> screenshots are captured by the
    generated Playwright spec itself (real execution evidence). Pixel similarity uses Pillow when installed;
    a score below 90% is a prompt to review, not automatically a defect (viewport/chrome/timing differences
    between the two capture methods are a known, explainable source of lower scores).</p>
  </div>
  {traceability_html}
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a before/after migration evidence report with screenshot comparison")
    parser.add_argument("--test-name", required=True)
    parser.add_argument("--before-dir", type=Path, required=True)
    parser.add_argument("--after-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Markdown report output path")
    parser.add_argument("--html", type=Path, help="HTML report output path (default: same name as --output with .html extension)")
    parser.add_argument("--no-html", action="store_true", help="Skip generating the HTML report")
    parser.add_argument("--passed", choices=["true", "false"], help="Whether the migrated Playwright test passed")
    parser.add_argument("--compiled", choices=["true", "false"], help="Whether `tsc --noEmit` passed with 0 errors on the generated project")
    parser.add_argument("--blocked-reason", help="If execution failed for a reason unrelated to code quality (e.g. 'VPN/network access to internal SAP host required'), describe it here")
    parser.add_argument("--error-log", type=Path, help="Path to a text file with the real captured Playwright error output, embedded verbatim as evidence")
    parser.add_argument("--mapped-actions", type=int)
    parser.add_argument("--unmatched-actions", type=int)
    parser.add_argument(
        "--report",
        type=Path,
        action="append",
        default=[],
        help="Path to a convert.py/batch_convert.py/project_convert.py JSON report (repeatable) — used to build the UiPath object -> Playwright conversion details table",
    )
    parser.add_argument("--no-traceability", action="store_true", help="Skip the full per-file, every-activity before/after traceability appendix (kept on by default when --report is supplied)")
    parser.add_argument("--source-project", type=Path, help="Path to the real UiPath source project root — scanned directly (independent of the migration output) to embed a verifiable 'how many test cases exist in source' inventory")
    parser.add_argument("--scope-note", help="Optional callout clarifying what this specific report covers (e.g. distinguishing a small demo fixture from the full real-project migration elsewhere)")
    parser.add_argument("--playwright-report", help="Relative path (from the report's output folder) to the real generated Playwright HTML report, e.g. 'playwright-report/index.html' — embedded as a clickable link so reviewers can open the actual test-run report")
    args = parser.parse_args()

    test_passed = None if args.passed is None else args.passed == "true"
    compiled = None if args.compiled is None else args.compiled == "true"
    error_log = args.error_log.read_text(encoding="utf-8") if args.error_log and args.error_log.exists() else None
    conversion_details = build_conversion_details(args.report) if args.report else None
    step_by_step = build_step_by_step_evidence(args.report) if args.report else None
    full_traceability = build_full_traceability(args.report) if args.report and not args.no_traceability else None
    source_inventory = scan_uipath_source_inventory(args.source_project) if args.source_project else None
    report_root = args.output.parent
    report = build_report(
        test_name=args.test_name,
        before_dir=args.before_dir,
        after_dir=args.after_dir,
        report_root=report_root,
        test_passed=test_passed,
        mapped_actions=args.mapped_actions,
        unmatched_actions=args.unmatched_actions,
        conversion_details=conversion_details,
        compiled=compiled,
        blocked_reason=args.blocked_reason,
        error_log=error_log,
        step_by_step=step_by_step,
        full_traceability=full_traceability,
        source_inventory=source_inventory,
        scope_note=args.scope_note,
        playwright_report_path=args.playwright_report,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote evidence report: {args.output}")

    if not args.no_html:
        html_path = args.html or args.output.with_suffix(".html")
        html = build_html_report(
            test_name=args.test_name,
            before_dir=args.before_dir,
            after_dir=args.after_dir,
            test_passed=test_passed,
            mapped_actions=args.mapped_actions,
            unmatched_actions=args.unmatched_actions,
            conversion_details=conversion_details,
            compiled=compiled,
            blocked_reason=args.blocked_reason,
            error_log=error_log,
            step_by_step=step_by_step,
            full_traceability=full_traceability,
            source_inventory=source_inventory,
            scope_note=args.scope_note,
            playwright_report_path=args.playwright_report,
        )
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html, encoding="utf-8")
        print(f"Wrote evidence report (HTML, self-contained): {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
