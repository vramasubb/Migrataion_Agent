---
mode: agent
description: "Full end-to-end UFT/QTP (VBScript) to Playwright TypeScript migration with evidence collection. Direct code-to-code translation — no reverse engineering. Pre-flight: run UFT suite and save evidence. Analyzes UFT action files and scripts, generates user stories, implements Playwright TypeScript tests. Generate MIGRATION-EVIDENCE.md. Invoke with: Migrate the UFT project end to end"
---

# UFT/QTP → Playwright Conversion Orchestrator

You are a Senior Test Automation Architect. Execute the full UFT/QTP to Playwright TypeScript migration **yourself, inline**.

> **Direct Migration Principle:** This migration is a **direct, code-to-code translation** of the existing
> UFT/QTP test suite. Every Playwright test must trace to an existing UFT action or test step.
> Do **NOT** infer tests by crawling the live application — the source action files and scripts are the
> single authoritative input. Reverse engineering from the application UI is strictly prohibited.

Read `migration-source.json` before starting to get source and output paths.

---

## Pipeline

```
PRE-FLIGHT  →  Run UFT source suite  →  analysis/evidence/uft/
              →  Create analysis/MIGRATION-EVIDENCE.md (source section)
Stage 1     →  analysis/<Action>/analysis.md + objects.md
Stage 2     →  analysis/<Action>/user_stories.md
GATE 1      →  STOP — show story summary — wait for "approved"
Stage 3     →  src/modules/<feature>/ (page objects + specs)
Run         →  npx playwright test --workers=1 --reporter=html,line
Heal        →  fix failures until green
EVIDENCE    →  Update MIGRATION-EVIDENCE.md (target section + mapping table)
GATE 2      →  STOP — show evidence report + results — wait for "approved"
```

---

## Pre-Migration — Source Evidence Collection

**Run the UFT source suite BEFORE writing any analysis file.**

> Direct Migration Principle: source action files are the input. The live application is **not** crawled.

### Steps

1. If UFT is available on the machine, run the test:
   - Open UFT One, load the test/suite, click Run, and export results as HTML.
   - Or use the UFT Command Line Runner:
     ```
     "C:\Program Files (x86)\Micro Focus\UFT One\bin\UFTBatchRunnerCMD.exe"
       /Storage "<path_to_test>" /Report "analysis\evidence\uft\report.html"
     ```
   - If UFT is unavailable: note "Source run skipped — UFT not installed on this machine. Evidence from source code analysis only." and proceed.

2. Copy/export evidence:
   ```
   mkdir analysis\evidence\uft
   copy <uft_results_folder>\*.html  analysis\evidence\uft\
   copy <uft_results_folder>\Screenshots\*  analysis\evidence\uft\screenshots\
   ```

3. Create `analysis/MIGRATION-EVIDENCE.md`:

```markdown
# Migration Evidence Report

> **Migration type:** Direct code-to-code translation
> **Source:** UFT/QTP (VBScript) → **Target:** Playwright TypeScript
> **Principle:** Every Playwright test maps 1:1 to an existing UFT action or step.
>               No tests inferred from the live application. No reverse engineering.

## 1. Source Execution — UFT/QTP

| Run date | Command | Report |
|---|---|---|
| <date> | UFT Command Line Runner | `analysis/evidence/uft/report.html` |

### Source Results
| # | Test/Action | Step Description | Status | Screenshot |
|---|---|---|---|---|
| 1 | <action name> | <step description> | ✅ PASS / ❌ FAIL | `analysis/evidence/uft/screenshots/` |

> **Total:** X passed, Y failed
> **Note:** UFT run may not be available in non-Windows/non-UFT environments.

## 2. Target Execution — Playwright TypeScript
> _Populated after Stage 3 completes._

## 3. Migration Mapping — Direct Translation Evidence
> _Populated after Stage 3 completes._
```

---

## Stage 1 — Analyze UFT Actions / Scripts

For every UFT action file (`.usr`, `.mts`, `.vbs`, action scripts), produce:

### `analysis/<Action>/analysis.md`
```
## Action Metadata
- Action name / shared object repository references / test flow

## Test Steps
For each action step:
  - Description (plain English)
  - UFT operation (Click, Set, GetROProperty, etc.)
  - Object name from Object Repository
  - Expected outcome / checkpoint

## Checkpoints
  - Checkpoint type | Expected value | Playwright assertion equivalent

## Conversion Notes
  - Confidence: High / Medium / Low
  - Risks: OR-based objects, DataTable parameters, environment variables
```

### `analysis/<Action>/objects.md`
Table: `Object Name | UFT Description Properties | Proposed Playwright Locator | Confidence`

UFT → Playwright object/locator mapping:
- `Browser("...").Page("...").WebButton("name:=Submit")` → `page.getByRole('button', { name: 'Submit' })`
- `WebEdit("name:=username")` → `page.getByLabel('username')` or `page.locator('[name="username"]')`
- `WebList("name:=country")` → `page.getByLabel('country')` → `.selectOption(value)`
- `WebCheckBox` → `page.getByRole('checkbox', { name: ... })`
- `WebTable` → `page.locator('table')`
- `GetROProperty("value")` → `await locator.inputValue()`
- `GetROProperty("innertext")` → `await locator.innerText()`

---

## Stage 2 — Generate User Stories

Group actions by business capability. Use standard story format.

---

## GATE 1 — Stop here

Show summary table, wait for "approved".

---

## Stage 3 — Implement Playwright TypeScript

UFT VBScript → TypeScript conversions:
- `Browser().Page().Navigate(url)` → `await page.goto(url)`
- `obj.Click` → `await locator.click()`
- `obj.Set "value"` → `await locator.fill('value')`
- `obj.Select "option"` → `await locator.selectOption('option')`
- `Checkpoint(name)` → `await expect(locator).toHaveText(expected)`
- `DataTable.Value(col, row)` → test data TypeScript constant or fixture
- `Wait(seconds)` → remove — use Playwright auto-waiting or `toBeVisible()`
- `Environment("var")` → `process.env.VAR`
- `Reporter.ReportEvent` → built-in Playwright test reporting
- `If / ElseIf / Else` → TypeScript `if / else`
- `For / ForEach` → TypeScript `for` loops
- `Function` / `Sub` → TypeScript function

Output structure:
```
src/modules/<feature>/
  <page>.page.ts
  <feature>.flow.ts
  <feature>.data.ts
  <feature>.spec.ts
```

Scaffold `package.json`, `playwright.config.ts`, `tsconfig.json` in `migrationOutputPath`.

Run and heal until all tests are green.

---

## Evidence Report — Complete MIGRATION-EVIDENCE.md

Once all Playwright tests are green, update `analysis/MIGRATION-EVIDENCE.md`:

**Section 2:** Fill Playwright target results from run output and `playwright-report/index.html`.

**Section 3 — Migration Mapping:**
```markdown
## 3. Migration Mapping — Direct Translation Evidence
| # | Source UFT Action/Step | Playwright Test | UFT | Playwright | Directly Migrated |
|---|---|---|---|---|---|
| 1 | <UFT action/step name> | <playwright test name> | ✅ | ✅ | ✅ |
> **Migration completeness:** X/X actions migrated (100%) | **Reverse engineering used:** None
```

---

## GATE 2 — Stop here

Show:
- Evidence summary from `analysis/MIGRATION-EVIDENCE.md`
- Report locations: UFT → `analysis/evidence/uft/report.html`, Playwright → `playwright-report/index.html`
- Screenshots: UFT `analysis/evidence/uft/screenshots/`, Playwright `test-results/`

Ask:
> "All tests are passing and the Migration Evidence Report is complete.
> Type **'approved'** to finalize, or provide feedback."
