# UiPath to Playwright Mapper

An isolated, mapper-driven UiPath Studio (XAML) to Playwright TypeScript migration project. It does not modify any existing migration agent or generated Playwright project.

## Why this uses fewer tokens

UiPath source is well-formed XML, so this converter parses it with a real XML tree walker (`xml.etree.ElementTree`) and matches known activities and Excel-driven data by **tag name**, not by AI inference. An AI agent needs context only for the small number of activities the walker reports as unmatched, rather than repeatedly reading and translating the whole XAML project.

Validated end to end against the real **`UiPath_POC_TestAutomationProject`** (a SAP Fiori web-automation suite
— not a toy fixture): the `OrderToCash` test case and all 8 `Reusable components/**/*.xaml` files convert with
**96/96 activities mapped, zero unmatched, zero parse failures**, entirely offline. See
[`../uipath-playwright-dm/`](../uipath-playwright-dm) for the assembled, standard Playwright project this
produces (page objects, env config, specs) and its `README.md` for the exact, honestly-reported gaps that
remain (Excel data content and a few VB/.NET framework calls — never silently invented).

## Structure

```text
uipath-to-playwright/
  .claude/skills/uipath-to-playwright/
    SKILL.md
    references/mapping_guide.md
  mappers/
    property_mapper.json
    action_mapper.json
    schema/
    clients/
  scripts/
    mapper_loader.py
    convert.py
    batch_convert.py
    project_convert.py
    build_evidence_report.py
    token_usage.py
  input/
  output/
  evidence-demo/
  tests/
```

## Commands

Requires Python 3.10 or newer and has no third-party runtime dependencies (Pillow is optional, only for
pixel-similarity screenshot comparison — see below).

```powershell
cd uipath-to-playwright
python scripts/mapper_loader.py --validate

# Single-file, statement-level conversion (raw test.describe/test wrapper — good for quick checks).
# Deliberately kept in its own quick-check-demo/ subfolder — NEVER at the top level of output/ — so it can
# never be mistaken for the real UiPath_POC_TestAutomationProject migration below.
python scripts/convert.py input/LoginFlow.xaml --output output/quick-check-demo/LoginFlow.spec.ts --report output/quick-check-demo/LoginFlow.json
python scripts/batch_convert.py input --output-dir output/quick-check-demo

# Full STANDARD project assembly (page objects + env config + specs) — the flagship path.
# ALWAYS point this at the real UiPath project root (contains Testcases/, Reusable components/), never at
# the input/ folder (that only holds small single-file fixtures for the quick-check command above).
python scripts/project_convert.py "C:\path\to\UiPathProject" --output ../uipath-playwright-dm

python -m unittest discover -s tests -v
```

`project_convert.py` is the one that produces the same standard project shape used everywhere else in this
repo (`package.json`, `playwright.config.ts`, `tsconfig.json`, `src/config/env.ts`, `src/pages/*.page.ts`,
`tests/*.spec.ts`) — one page object per `Reusable components/**/*.xaml` file, with `InvokeWorkflowFile` calls
resolved to real method calls using the exact call-site arguments. Each page object follows the standard
Playwright Page Object Model pattern: every UiPath Selector used is hoisted into a named `private readonly
...: Locator` class field (assigned once in the constructor via `hoist_locators_to_properties()`), instead of
being repeated as an inline literal at every call site. `convert.py`/`batch_convert.py` remain available for
quick single-file/statement-level checks and for the live-execution proof below.

`batch_convert.py`/`project_convert.py` never abort on one bad file — a `.xaml` that fails to parse or map is
recorded/reported explicitly and the rest of the run still completes, so it's safe to hand this repo to any
team and point it at their own UiPath project.

## Before/After execution evidence (screenshot comparison)

`evidence-demo/` is a **secondary, live-execution proof of the engine** using the `LoginFlow.xaml` fixture
against the public `saucedemo.com` site — a small 1-file demo, **not** the real `UiPath_POC_TestAutomationProject`
(that real project targets an internal, VPN-gated SAP system this environment can't reach). Its report is
deliberately named `DEMO-EVIDENCE.html`, not `MIGRATION-EVIDENCE.html`, so it can never be mistaken for the
real project's report. For the real project's complete evidence (all test cases, 102/102 activities mapped)
see [`output/uipath-poc-playwright-project/MIGRATION-EVIDENCE.html`](output/uipath-poc-playwright-project/MIGRATION-EVIDENCE.html)
(this Python converter) or [`../uipath-playwright-dm/MIGRATION-EVIDENCE.html`](../uipath-playwright-dm/MIGRATION-EVIDENCE.html)
(agent flow) — both are generated from the same source and are identical in coverage.

```powershell
# 1. Convert with screenshot capture enabled (adds a page.screenshot() after every UI action)
python scripts/convert.py input/LoginFlow.xaml --output evidence-demo/tests/LoginFlow.spec.ts --screenshots evidence/after

# 2. Run the migrated spec for real — this populates evidence/after/<test>/NN-<action>.png
cd evidence-demo && npx playwright test

# 3. Capture (or supply, from an actual UiPath Robot/Studio run) matching evidence/before/<test>/NN-*.png screenshots

# 4. Build the side-by-side comparison report
python ../scripts/build_evidence_report.py --test-name "LoginFlow" `
  --before-dir evidence/before/loginflow --after-dir evidence/after/loginflow `
  --output DEMO-EVIDENCE.md --passed true --mapped-actions 7 --unmatched-actions 0
```

`build_evidence_report.py` pairs before/after screenshots by step order and computes a Pillow-based pixel
similarity score per pair (`pip install Pillow`; falls back to a plain note if Pillow isn't installed — it
never invents a similarity number). See [`evidence-demo/`](evidence-demo) for a real, executed example: the
`LoginFlow.xaml` fixture converted, run against the live `saucedemo.com` target, and diffed against a
reference baseline in [`evidence-demo/DEMO-EVIDENCE.md`](evidence-demo/DEMO-EVIDENCE.md).

## Token usage report

Every converter prints a token summary. When a report path is used, the same data is saved under `tokenUsage` in `migration-report.json`.

- `migrationConversion` is exact: local Python invokes no model, so billable input/output tokens and cost are zero.
- `textEquivalentWorkload` estimates source and generated text at four characters per token. This is useful for comparison but is not billable usage.
- `optionalAgentAssistance` is separate. Actual setup/help tokens cannot be inferred by the Python process; supply counts from the API/provider usage response.

Validate the generated project with:

```powershell
cd output/uipath-poc-playwright-project
npm install
npm run typecheck
npx playwright test
npm run report      # opens playwright-report/index.html — the html reporter uses open:'never', so it never
                     # auto-opens after `npx playwright test`; run this to actually view the report
```

Credentials and the target URL are read from `.env` (already populated with the `TEST_OTC` Orchestrator
account for this project, gitignored via `output/*`) and loaded automatically by `playwright.config.ts` via
`dotenv.config()`. Test data fixtures (`test-data/create-sales-order-data.json`,
`test-data/create-obd-data.json`) are populated with real rows from the source project's
`TestData/Order2Cash.xlsx`, not `SAMPLE_*` placeholders.


Use `--strict` to fail on any unmapped activity. Without it, unmatched activities become visible `// TODO: unmapped activity <Tag>` comments and are counted in the JSON report (`unmatched_lines`); they are never silently dropped.

## Scope

The deterministic converter is a real XAML tree walker: it recognizes activities **by XML tag**, not line position, so attribute order and multi-line nesting don't matter. It covers classic single-attribute activities (`ui:Click`, `ui:TypeInto`, `ui:CheckBox`, `ui:SelectItem`, `ui:ElementExists`, `ui:GetText`, `ui:VerifyExpression`, `ui:OpenBrowser`/`ui:NavigateTo`, `ui:LogMessage`, `ui:InvokeWorkflowFile`), modern `UiPath.UIAutomationNext` "App/Web recorder" activities with nested Target descriptors (`uix:NClick`, `uix:NTypeInto`, `uix:NGetText`, `uix:NMouseScroll`, `uix:NCheckState`), control flow (`ui:MultipleAssign`/`Assign`, `ui:ForEachRow`), Orchestrator plumbing (`ui:GetRobotAsset`/`ui:GetRobotCredential`), regex extraction (`ui:Matches`), and reporting activities (`ra:StartTest`/`ra:StepStatus`/etc.). `ui:CommentOut` (Studio's "disabled" state) is fully excluded from output. See [.claude/skills/uipath-to-playwright/SKILL.md](.claude/skills/uipath-to-playwright/SKILL.md) for the full coverage table and what's intentionally left as a flagged `// TODO` (e.g. Excel cell **contents**, complex VB expressions) for a human or agent to finish.

`coverage-tracker.csv` records current mappings using the glossary names cited by the shared migration prompt; reconcile it with the shared workbook before declaring organizational coverage complete.
