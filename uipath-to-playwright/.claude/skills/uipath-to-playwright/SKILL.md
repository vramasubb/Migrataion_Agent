---
name: uipath-to-playwright
description: Mapper-first migration of UiPath Studio (XAML) web automation projects to Playwright TypeScript, with client overrides, validation, tests, and minimal context usage.
---

# UiPath Studio (XAML) to Playwright TypeScript

Use this skill only for UiPath-to-Playwright migration of **web** UI Automation activities. The UiPath source is read-only and the target must be a separate output directory.

## Non-negotiable rules

1. Run `python scripts/mapper_loader.py --validate` before conversion and after every mapper edit.
2. Read mappings from `mappers/property_mapper.json` and `mappers/action_mapper.json` only through `MapperLoader`. Never add activity-tag switch statements, selector-parsing regexes, or migration tables to converter code — new activities are new JSON entries, not new Python branches.
3. Put client differences in `mappers/clients/<client>.json`; do not fork base mappings.
4. Preserve every test case, assertion, data row, tag/priority, `InvokeWorkflowFile` call, and configuration value (assets, queues, environment URLs). Never invent behavior missing from source.
5. Prefer Playwright user-facing locators: test id/automation id, stable `id`, accessible name (UiPath `aaname`/`name`), CSS class, then tag. Use the ordered property mapper for fallback.
6. Use Playwright auto-waiting and web-first assertions. Do not migrate `ui:Delay`, hardcoded `Duration`/`Timeout` waits, or UiPath browser-lifecycle activities (`ui:OpenBrowser`/`ui:CloseTab`/`ui:KillProcess`) literally beyond the initial navigation — Playwright's fixture manages browser/context lifecycle.
7. Generated TypeScript must contain no UiPath imports/namespaces and no secrets (Orchestrator assets, credentials) copied into source — read them from environment variables instead.

## Scope — what the deterministic converter covers

The converter is a **real XAML (XML) tree walker** (`xml.etree.ElementTree`), not line/regex-based — UiPath source is well-formed XML, so activities are matched by tag name and read via `.attrib`/child elements regardless of attribute order or line wrapping. This is validated against the real `UiPath_POC_TestAutomationProject` sample (SAP Fiori web automation): **all 9 `.xaml` files convert with zero unmatched activities.**

It reliably covers, tag-driven from `action_mapper.json` (no code changes needed to add more):

- Classic single-attribute activities: `ui:OpenBrowser`/`ui:NavigateTo` → `page.goto`, `ui:Click`, `ui:TypeInto`, `ui:CheckBox`, `ui:SelectItem`, `ui:ElementExists`, `ui:GetText`, `ui:VerifyExpression`, `ui:LogMessage`, `ui:InvokeWorkflowFile`
- Modern `UiPath.UIAutomationNext` (App/Web recorder) activities with the selector nested in a child `<Tag.Target><TargetAnchorable FullSelectorArgument="...">`: `uix:NClick`, `uix:NTypeInto`, `uix:NGetText`, `uix:NMouseScroll`
- Structural/control-flow constructs handled by a small fixed set of tree-walker rules (not JSON, since they express nesting/branching, not automation): `Sequence` containers, `uix:NApplicationCard` (descends only into `.Body`), `ui:MultipleAssign`/`Assign` (VB `.To`/`.Value` → `const`/assignment), `ui:ForEachRow` (→ `for...of`), `uix:NCheckState` (`.IfExists`/`.IfNotExists` → `if/else` on `isVisible()`)
- `ui:CommentOut` is fully **excluded** (Studio's "disabled" state) — its contents never reach the generated spec
- Orchestrator plumbing: `ui:GetRobotAsset`/`ui:GetRobotCredential` → `process.env.*`, `ui:KillProcess` → lifecycle comment, `ra:StartTest` (sets the test title from `TestName`), `ra:StepStatus`/`ra:CreateReport`/`ra:StartSuite` → informational `console.log`
- `ui:Matches` (regex extraction) → `String.match(/pattern/)`
- `ui:ReadRange` → a `// TODO` pointing at the workbook/sheet (Excel data loading is intentionally not auto-generated — see below)

**Never silently dropped:** any activity that reaches the tree walker's default fallthrough with no recognized tag AND no children is emitted as `// TODO: unmapped activity <Tag> DisplayName` and counted in `unmatched_lines` in the JSON report — it is never invented or skipped quietly.

**Intentionally not code-generated** (needs a human/agent decision, flagged clearly rather than guessed): Excel/DataTable **content** (only the read call is flagged, not the data itself), and complex VB expressions containing `String.Format(`, `vbCrLf`, `Nothing`, `AndAlso`/`OrElse` (emitted as-is with a `// VERIFY: VB expression` comment).

## Low-token workflow

### 1. Preflight

- Resolve source (`.xaml` project) and target (Playwright project) paths once.
- Inventory `Testcases/`, `Reusable components/`, and `TestData/` with file-name searches; do not paste entire XAML files into context.
- Read `project.json` for entry points, dependencies, and `ignoredFiles`.
- Run the UiPath suite if UiPath Studio/Robot is available on this machine; record command and result. Never modify source.

### 2. Validate and map

```powershell
python scripts/mapper_loader.py --validate
python scripts/batch_convert.py <source-testcases-folder> --output-dir output --client <client>
python scripts/batch_convert.py "<source>/Reusable components" --output-dir output/components --client <client>
```

- Omit `--client` when no overlay applies.
- Use the compact `output/migration-report.json` (`unmatched_lines`, `action_ids`, `failures`) to identify gaps — one file's XML parse error never aborts the batch.
- Do not re-read mapped source. Read only the `// TODO` lines (with their enclosing activity) reported as unmatched.
- Add a reusable mapping to JSON when the behavior is general (any UiPath project). Add it to a client overlay only when application-specific.

### 3. Assemble the Playwright project

Prefer `python scripts/project_convert.py "<uipathProjectRoot>" --output <targetProjectPath>` over hand-assembly
— it already produces the standard shape in one deterministic pass:

- `playwright.config.ts`, `package.json`, `tsconfig.json`: standard config matching source intent.
- `src/config/env.ts`: base URL + Orchestrator asset/credential env vars.
- `src/pages/*.page.ts`: one class per `Reusable components/**/*.xaml` file, method name/args derived from the
  workflow's own `<x:Members>` declaration — a `ui:InvokeWorkflowFile` call in a test case becomes a real call
  to that method with the exact call-site arguments, not a TODO.
- `tests/*.spec.ts`: one spec per `Testcases/*.xaml` file, preserving the test name (from `ra:StartTest`'s
  `TestName`), instantiating only the page objects it actually calls.
- Any `ui:ReadRange` data is flagged, not fabricated — load it as a JSON/CSV fixture next to the spec.

### 4. Verify incrementally

Run in this order:

```powershell
npx tsc --noEmit
npx playwright test <one-generated-spec> --project=chromium --workers=1
npx playwright test --workers=1
```

Classify failures as compile, configuration, locator, timing, assertion, data, environment, or application. Fix the root mapping or generated code, rerun the narrow test, then rerun the suite. Never weaken an assertion merely to make a test pass.

### 5. Evidence and completion

Create a migration report containing source/target counts, mapping IDs used, unmatched constructs, inlined reusable components, test results, intentional deviations, and report paths. Completion requires:

- mapper validation passes;
- source test cases and target tests have traceable one-to-one coverage;
- zero unexplained `unmatched_lines` (including resolved `InvokeWorkflowFile` TODOs) and zero `failures` in the batch report;
- TypeScript compile passes;
- target tests pass, or environment/application blockers are evidenced;
- `coverage-tracker.csv` reflects validated mappings.

Read [references/mapping_guide.md](references/mapping_guide.md) before changing mapper data.

## Before/After Execution Evidence (Screenshot Comparison)

To claim "100% migration" for a test case, produce **both** a pre-migration and a post-migration screenshot
trail and a diffed comparison report — do not just show the target passing.

1. **Pre-migration (source) execution** — run the UiPath test case for real and capture a screenshot at each
   step:
   - If UiPath Studio/Robot is installed: `UiRobot.exe execute --file "<TestCase>.xaml"` and export the
     Robot/Orchestrator execution screenshots into `evidence/before/<test-slug>/NN-<step>.png` (numbered in
     the same order the steps occur in the `.xaml`).
   - If UiPath is **not** installed in this environment (common in CI/agent sandboxes): capture a reference
     baseline instead by driving the same target application through the identical step sequence (same
     selectors, same order) with a browser tool, and label it explicitly as a reference baseline, not a
     UiPath-produced screenshot. Never claim a screenshot came from UiPath when it did not.
2. **Migrate** — run `convert.py`/`batch_convert.py` with `--screenshots evidence/after` so the generated
   spec captures `page.screenshot()` after every `.click()`/`.fill()`/`.check()`/`.uncheck()`/`.selectOption()`
   call, numbered in execution order to line up with the pre-migration set.
3. **Post-migration (target) execution** — run the real Playwright suite (`npx playwright test`); this
   populates `evidence/after/<test-slug>/NN-<action>.png` for real, plus the standard `playwright-report/`
   and traces.
4. **Compare** — run `python scripts/build_evidence_report.py --test-name "<name>" --before-dir
   evidence/before/<test-slug> --after-dir evidence/after/<test-slug> --output
   analysis/MIGRATION-EVIDENCE.md --passed true|false --mapped-actions N --unmatched-actions N`. This writes
   **both** `analysis/MIGRATION-EVIDENCE.md` and a self-contained `analysis/MIGRATION-EVIDENCE.html` (images
   embedded as base64 — one portable file, no separate screenshot folder needed to view it; `--no-html` to
   skip). It pairs screenshots by step, computes a Pillow pixel-similarity score per pair when Pillow is
   installed (falls back to a note when it isn't — never fabricates a similarity number).
5. Attach `analysis/MIGRATION-EVIDENCE.html` (open it directly in a browser) as the migration's evidence
   artifact — its banner only shows green "Migration complete" when mapper coverage is 100% **and** the
   Playwright run passed; otherwise it shows an amber "needs review" state, so the report itself cannot
   overstate completeness. A similarity score below ~90% is a prompt to review, not an automatic failure —
   differing viewport size or browser chrome between the two capture methods is a known, explainable source
   of lower scores; call this out rather than silently accepting or silently failing.
