from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from convert import ProjectWalker, _find_child_by_suffix, _local_name
from mapper_loader import MapperLoader


@dataclass
class ComponentBuild:
    source: Path
    class_name: str
    method_name: str
    file_name: str
    params: list[tuple[str, str]]
    ts: str
    mapped_actions: int
    action_ids: list[str] = field(default_factory=list)
    action_records: list[dict] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    fixture_file: tuple[str, set[str]] | None = None


def _pascal(stem: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", stem)
    # Real UiPath component filenames are already PascalCase (CreateOBD.xaml), but "flat" projects often
    # use lowercase framework filenames (start.xaml, stop.xaml) — capitalize so the generated class name is
    # never identical to its own lowerCamelCase instance variable (e.g. class `startPage` vs `const startPage`).
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


def _camel(stem: str) -> str:
    cleaned = _pascal(stem)
    return cleaned[:1].lower() + cleaned[1:] if cleaned else "run"


def _kebab(stem: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", stem)
    # Split camelCase word boundaries but keep acronym runs together (OBD -> obd, not o-b-d).
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "-", cleaned)
    return spaced.strip("-").lower()


_LOCATOR_CALL_RE = re.compile(r"page\.locator\('((?:[^'\\]|\\.)*)'\)")


def _locator_field_name(selector: str, used_names: set[str]) -> str:
    """Derives a readable camelCase field name from a selector, e.g. '#USERNAME_FIELD-inner' -> 'usernameFieldInnerLocator'."""
    text = selector
    if text.startswith("text="):
        text = text[len("text="):]
    elif text.startswith("#"):
        text = text[1:]
    else:
        attr_match = re.match(r'^\[[\w-]+="([^"]+)"\]$', text)
        if attr_match:
            text = attr_match.group(1)
    # Split on non-alnum separators AND on camelCase boundaries (userActionsMenu -> user Actions Menu).
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    words = [w for w in re.split(r"[^A-Za-z0-9]+", text) if w][:6]
    if not words:
        words = ["locator"]
    name = words[0].lower() + "".join(w.capitalize() for w in words[1:])
    name = re.sub(r"[^A-Za-z0-9]", "", name) or "locator"
    if not name[0].isalpha():
        name = f"loc{name}"
    name += "Locator"
    base, candidate, counter = name, name, 2
    while candidate in used_names:
        candidate = f"{base}{counter}"
        counter += 1
    used_names.add(candidate)
    return candidate


def hoist_locators_to_properties(body: str) -> tuple[str, list[tuple[str, str]], dict[str, str]]:
    """Page Object Model refactor: replaces every inline `page.locator('...')` call in `body` with a
    `this.<name>` reference to a named class field. Returns the modified body, an ordered list of
    (fieldName, selector) pairs the caller declares/assigns once per class (not per call site), and the
    selector->fieldName mapping (so callers can apply the identical substitution to other snippets, e.g. the
    evidence report's per-occurrence `rendered` code, keeping them in sync with the real generated file)."""
    seen: dict[str, str] = {}
    order: list[str] = []
    used_names: set[str] = set()

    def repl(match: re.Match[str]) -> str:
        selector = match.group(1)
        if selector not in seen:
            seen[selector] = _locator_field_name(selector, used_names)
            order.append(selector)
        return f"this.{seen[selector]}"

    new_body = _LOCATOR_CALL_RE.sub(repl, body)
    return new_body, [(seen[sel], sel) for sel in order], seen


def apply_locator_mapping(text: str, mapping: dict[str, str]) -> str:
    """Applies an already-computed selector->fieldName mapping (from `hoist_locators_to_properties`) to
    another snippet of generated code, e.g. an evidence-report record, so it matches the real output file."""
    return _LOCATOR_CALL_RE.sub(lambda m: f"this.{mapping[m.group(1)]}" if m.group(1) in mapping else m.group(0), text)


def _extract_in_arguments(root: ET.Element) -> list[tuple[str, str]]:
    """Read the workflow's own `<x:Members><x:Property Type="InArgument(...)">` declarations."""
    members = None
    for child in root:
        if _local_name(child.tag) == "Members":
            members = child
            break
    if members is None:
        return []
    params: list[tuple[str, str]] = []
    for prop in members:
        if _local_name(prop.tag) != "Property":
            continue
        type_attr = prop.attrib.get("Type", "")
        if not type_attr.startswith("InArgument"):
            continue
        name = prop.attrib.get("Name")
        if name:
            params.append((name, "string"))
    return params


def build_component(xaml_path: Path, loader: MapperLoader, engine: str = "web") -> ComponentBuild:
    xaml_text = xaml_path.read_text(encoding="utf-8")
    root = ET.fromstring(xaml_text)
    params = _extract_in_arguments(root)
    fixture_slug = _kebab(xaml_path.stem)
    walker = ProjectWalker(loader, engine, fixture_slug=fixture_slug, source_text=xaml_text)
    body_lines = walker.walk_root(root)

    stem = xaml_path.stem
    method_name = _camel(stem)
    class_name = f"{_pascal(stem)}Page"
    if params:
        type_literal = "; ".join(f"{name}: string" for name, _ in params)
        destructure = ", ".join(name for name, _ in params)
        signature = f"{{ {destructure} }}: {{ {type_literal} }}"
    else:
        signature = ""
    indented_body = "\n".join(f"    {line}" for line in body_lines) or "    // No mapped UiPath actions found."
    indented_body, locator_fields, locator_mapping = hoist_locators_to_properties(indented_body)
    if locator_mapping:
        for record in walker.mapped_records:
            record["rendered"] = apply_locator_mapping(record["rendered"], locator_mapping)
    # `GlobalVariablesNamespace.GlobalVariables.X` translates to `env.x`; import env only when it's actually used.
    env_import = "import { env } from '../config/env';\n" if re.search(r"\benv\.", indented_body) else ""
    fixture_import = "".join(f"{line}\n" for line in sorted(set(walker.fixture_imports.values())))
    page_type_import = "Page, Locator" if locator_fields else "Page"
    field_decls = "".join(f"  private readonly {name}: Locator;\n" for name, _ in locator_fields)
    if locator_fields:
        field_assigns = "".join(f"    this.{name} = page.locator('{selector}');\n" for name, selector in locator_fields)
        constructor = f"  constructor(readonly page: Page) {{\n{field_assigns}  }}\n\n"
    else:
        constructor = "  constructor(readonly page: Page) {}\n\n"
    ts = (
        f"import type {{ {page_type_import} }} from '@playwright/test';\n"
        "import { expect } from '@playwright/test';\n"
        f"{env_import}{fixture_import}\n"
        f"export class {class_name} {{\n"
        f"{field_decls}"
        f"{constructor}"
        f"  async {method_name}({signature}): Promise<void> {{\n"
        "    const page = this.page;\n"
        f"{indented_body}\n"
        "  }\n"
        "}\n"
    )
    all_columns: set[str] = set()
    for columns in walker.fixture_columns.values():
        all_columns.update(columns)
    return ComponentBuild(
        source=xaml_path,
        class_name=class_name,
        method_name=method_name,
        file_name=f"{_kebab(stem)}.page.ts",
        params=params,
        ts=ts,
        fixture_file=(fixture_slug, all_columns) if all_columns else None,
        mapped_actions=len(walker.mapped_ids),
        action_ids=walker.mapped_ids,
        action_records=walker.mapped_records,
        unmatched=walker.unmatched,
    )


def build_registry(components_dir: Path, loader: MapperLoader, engine: str = "web") -> tuple[dict[str, dict], list[ComponentBuild]]:
    paths = sorted(components_dir.rglob("*.xaml"))
    return build_registry_from_paths(paths, components_dir.parent, loader, engine)


def build_registry_from_paths(
    paths: list[Path], relative_root: Path, loader: MapperLoader, engine: str = "web"
) -> tuple[dict[str, dict], list[ComponentBuild]]:
    """Same as `build_registry` but takes an explicit file list — used for "flat" UiPath projects (a single
    `Main.xaml` with loose top-level `.xaml` helper workflows, no `Testcases/`/`Reusable components/` split)."""
    from convert import normalize_workflow_path

    registry: dict[str, dict] = {}
    builds: list[ComponentBuild] = []
    for xaml_path in paths:
        build = build_component(xaml_path, loader, engine)
        relative = xaml_path.relative_to(relative_root)
        registry[normalize_workflow_path(str(relative))] = {
            "class_name": build.class_name,
            "method_name": build.method_name,
            "instance_var": f"{build.method_name}Page",
            "file_name": build.file_name,
            "params": build.params,
        }
        builds.append(build)
    return registry, builds


def build_testcase_spec(
    xaml_path: Path, loader: MapperLoader, registry: dict[str, dict], engine: str = "web"
) -> tuple[str, ProjectWalker]:
    root = ET.fromstring(xaml_path.read_text(encoding="utf-8"))
    walker = ProjectWalker(loader, engine, component_registry=registry)
    body_lines = walker.walk_root(root)

    used = sorted(walker.used_components.values(), key=lambda component: component["instance_var"])
    imports = "\n".join(f"import {{ {component['class_name']} }} from '../src/pages/{component['file_name'][:-3]}';" for component in used)
    instantiations = "\n".join(f"    const {component['instance_var']} = new {component['class_name']}(page);" for component in used)

    title = (walker.test_name or xaml_path.stem).replace("'", "\\'")
    body = "\n".join(body_lines) or "    // No mapped UiPath actions found."
    # UiPath's "attach to an already-open browser/app" model (NApplicationCard) has no explicit navigate
    # step; Playwright always starts from a blank page, so bridge with an initial goto if none was mapped.
    env_import = ""
    if "page.goto(" not in body:
        env_import = "import { env } from '../src/config/env';\n"
        instantiations = f"    await page.goto(env.webBaseUrl);\n{instantiations}" if instantiations else "    await page.goto(env.webBaseUrl);"
    ts = (
        "import { test, expect } from '@playwright/test';\n"
        f"{env_import}"
        f"{imports}\n\n"
        f"test.describe('{title}', () => {{\n"
        f"  test('{title}', async ({{ page }}) => {{\n"
        f"{instantiations}\n"
        f"{body}\n"
        "  });\n"
        "});\n"
    )
    return ts, walker


PACKAGE_JSON = """{
  "name": "uipath-poc-playwright-project",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "test": "playwright test",
    "report": "npx playwright show-report playwright-report",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "@playwright/test": "^1.55.0",
    "dotenv": "^16.4.0",
    "@types/node": "^24.0.0",
    "typescript": "^5.9.0"
  }
}
"""

PLAYWRIGHT_CONFIG = """import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';

dotenv.config();

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [['html', { outputFolder: 'playwright-report', open: 'never' }], ['line']],
  use: { trace: 'on-first-retry', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
"""

TSCONFIG = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  }
}
"""


def _env_ts(base_url: str) -> str:
    return (
        "export const env = {\n"
        f'  webBaseUrl: process.env.WEB_BASE_URL ?? "{base_url}",\n'
        "  username: process.env.UIPATH_USERNAME ?? '',\n"
        "  password: process.env.UIPATH_PASSWORD ?? '',\n"
        "  // Mirrors the UiPath project's GlobalVariablesNamespace.GlobalVariables.* framework values.\n"
        "  folderPath: process.env.REPORTS_FOLDER_PATH ?? './reports',\n"
        "  testcaseName: process.env.TESTCASE_NAME ?? 'OrderToCash',\n"
        "};\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a full standard Playwright project from a UiPath Studio project")
    parser.add_argument("uipath_project", type=Path, help="Path to the UiPath project root (contains Testcases/, Reusable components/)")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output Playwright project directory")
    parser.add_argument("--client")
    parser.add_argument("--engine", default="web")
    parser.add_argument(
        "--base-url",
        default="https://usawsconl0576.us.deloitte.com:8100/sap/bc/ui2/flp",
        help="Default web base URL for src/config/env.ts (override with WEB_BASE_URL at runtime)",
    )
    parser.add_argument("--report", type=Path, help="Write a JSON report with per-file action_ids for build_evidence_report.py")
    args = parser.parse_args()

    loader = MapperLoader(client=args.client)
    errors = loader.validate()
    if errors:
        raise SystemExit("Mapper validation failed:\n- " + "\n- ".join(errors))

    components_dir = args.uipath_project / "Reusable components"
    testcases_dir = args.uipath_project / "Testcases"
    if testcases_dir.exists() or components_dir.exists():
        registry, component_builds = build_registry(components_dir, loader, args.engine)
        testcase_paths = sorted(testcases_dir.rglob("*.xaml"))
    else:
        # "Flat" UiPath project shape (no Testcases/Reusable components split) — e.g. a single Main.xaml
        # entry point with loose helper workflows (start.xaml, stop.xaml, ...) at the project root, common
        # for UiPath Test Manager/recorder-generated projects. The project.json `main` field names the entry
        # workflow; every OTHER top-level .xaml becomes an invokable component/page object, same as a
        # Reusable component would (InvokeWorkflowFile references them by their plain relative filename).
        main_entry = "Main.xaml"
        project_json_path = args.uipath_project / "project.json"
        if project_json_path.exists():
            try:
                main_entry = json.loads(project_json_path.read_text(encoding="utf-8")).get("main", main_entry)
            except (OSError, json.JSONDecodeError):
                pass
        main_path = args.uipath_project / main_entry
        component_paths = sorted(
            p for p in args.uipath_project.glob("*.xaml") if p.resolve() != main_path.resolve()
        )
        registry, component_builds = build_registry_from_paths(component_paths, args.uipath_project, loader, args.engine)
        testcase_paths = [main_path] if main_path.exists() else []

    pages_dir = args.output / "src" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    for build in component_builds:
        (pages_dir / build.file_name).write_text(build.ts, encoding="utf-8")

    test_data_dir = args.output / "test-data"
    fixtures_created = []
    for build in component_builds:
        if build.fixture_file is None:
            continue
        slug, columns = build.fixture_file
        fixture_path = test_data_dir / f"{slug}-data.json"
        if fixture_path.exists():
            continue  # never overwrite a fixture a human has already filled in with real values
        test_data_dir.mkdir(parents=True, exist_ok=True)
        placeholder_row = {column: f"SAMPLE_{column.upper()}" for column in sorted(columns)}
        fixture_path.write_text(json.dumps([placeholder_row], indent=2) + "\n", encoding="utf-8")
        fixtures_created.append(str(fixture_path))

    tests_dir = args.output / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    testcase_results = []
    for xaml_path in testcase_paths:
        ts, walker = build_testcase_spec(xaml_path, loader, registry, args.engine)
        spec_name = f"{_kebab(xaml_path.stem)}.spec.ts"
        (tests_dir / spec_name).write_text(ts, encoding="utf-8")
        testcase_results.append((xaml_path, spec_name, walker))

    config_dir = args.output / "src" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "env.ts").write_text(_env_ts(args.base_url), encoding="utf-8")

    (args.output / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    (args.output / "playwright.config.ts").write_text(PLAYWRIGHT_CONFIG, encoding="utf-8")
    (args.output / "tsconfig.json").write_text(TSCONFIG, encoding="utf-8")

    total_mapped = sum(build.mapped_actions for build in component_builds) + sum(len(w.mapped_ids) for _, _, w in testcase_results)
    total_unmatched = sum(len(build.unmatched) for build in component_builds) + sum(len(w.unmatched) for _, _, w in testcase_results)

    if args.report:
        files_report = [
            {
                "source": str(build.source),
                "output": f"src/pages/{build.file_name}",
                "kind": "page-object",
                "mapped_actions": build.mapped_actions,
                "unmatched_lines": len(build.unmatched),
                "action_ids": build.action_ids,
                "action_records": build.action_records,
            }
            for build in component_builds
        ] + [
            {
                "source": str(xaml_path),
                "output": f"tests/{spec_name}",
                "kind": "test-spec",
                "mapped_actions": len(walker.mapped_ids),
                "unmatched_lines": len(walker.unmatched),
                "action_ids": walker.mapped_ids,
                "action_records": walker.mapped_records,
            }
            for xaml_path, spec_name, walker in testcase_results
        ]
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"files": files_report}, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote conversion report: {args.report}")

    print(f"Assembled Playwright project at {args.output}")
    print(f"  Page objects: {len(component_builds)} ({', '.join(b.class_name for b in component_builds)})")
    print(f"  Test specs:   {len(testcase_results)} ({', '.join(name for _, name, _ in testcase_results)})")
    print(f"  Total mapped actions: {total_mapped}, unmatched: {total_unmatched}")
    if fixtures_created:
        print(f"  Fixtures created (SAMPLE_* placeholders — replace with real values): {', '.join(fixtures_created)}")
    if total_unmatched:
        print("  Unmatched:")
        for build in component_builds:
            for item in build.unmatched:
                print(f"    {build.source.name}: {item}")
        for xaml_path, _, walker in testcase_results:
            for item in walker.unmatched:
                print(f"    {xaml_path.name}: {item}")
    return 1 if total_unmatched else 0


if __name__ == "__main__":
    raise SystemExit(main())
