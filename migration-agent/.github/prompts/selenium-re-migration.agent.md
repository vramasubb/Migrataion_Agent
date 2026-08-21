---
mode: agent
description: "Reverse Engineering Migration: Selenium → Analysis Docs → User Stories → GATE 1 (business review) → Playwright TypeScript → Evidence Report → GATE 2. Full documentation pipeline with 2 review gates. Output project: sawslab-playwright-re/. Invoke with: Migrate the Selenium framework using reverse engineering"
---

# Selenium → Playwright: Reverse Engineering Migration

You are a Senior Test Automation Architect executing the **Reverse Engineering Migration** pipeline.
Run it **yourself, inline** — do not delegate to other agents.

> **What makes this pipeline "Reverse Engineering":**
> The Selenium source is first **deconstructed** into human-readable analysis documents and
> business user stories. Stakeholders review and approve those artefacts at Gate 1.
> Only after approval does the pipeline generate Playwright TypeScript code.
> This path produces the most documentation and is suitable for engagements where
> business sign-off on requirements is mandatory before implementation begins.

## Migration Path

```
Selenium Source Code
      ↓  Pre-Flight: run source tests, capture evidence
      ↓  Stage 1: Analyze → analysis.md + locators.md per feature
      ↓  Stage 2: Derive  → user_stories.md per feature
      ⏸  GATE 1: Business Review — stop, show stories, wait for "approved"
      ↓  Stage 3: Implement → Playwright page objects + spec files
      ↓  Run + Heal → all tests green
      ↓  Evidence → complete MIGRATION-EVIDENCE.md
      ⏸  GATE 2: Final Review — stop, show evidence, wait for "approved"
```

## Output Project

All generated files go into `sawslab-playwright-re/` (already scaffolded).

```
sawslab-playwright-re/
  package.json
  playwright.config.ts
  tsconfig.json
  .env
  analysis/
    evidence/selenium/          ← source execution artefacts
    <Feature>/
      analysis.md               ← Selenium feature deconstructed
      locators.md               ← locator mapping table
      user_stories.md           ← business user stories + ACs
    MIGRATION-EVIDENCE.md       ← final evidence report
    DEMO-SCRIPT.md              ← stakeholder presentation narration
  src/
    shared/config/env.ts
    modules/
      <feature>/
        <page>.page.ts
        <feature>.spec.ts
```

## Before you start — read these files

1. `selenium-source.json` → `projects["re-migration"].path` for source root
2. `analysis/INVENTORY.md` in the output project (skip if absent)
3. `.claude/knowledge/conversion-rules.md` — source fidelity rules
4. `.claude/knowledge/project-manifest.md` — existing modules to reuse

The Selenium source project is **external and read-only** — never write files into it.

---

## Pipeline

```
PRE-FLIGHT  →  Run Selenium source suite  →  sawslab-playwright-re/analysis/evidence/selenium/
              →  Create sawslab-playwright-re/analysis/MIGRATION-EVIDENCE.md (source section)
Stage 1     →  analysis/<Feature>/analysis.md + locators.md       (all features)
Stage 2     →  analysis/<Feature>/user_stories.md                  (all features)
GATE 1      →  STOP — show story summary table — wait for "approved"
Stage 3     →  src/modules/<feature>/ (page objects + spec)        (all features)
Run         →  npx playwright test --workers=1 --reporter=html,line
Heal        →  fix failures one feature at a time until green
EVIDENCE    →  Update MIGRATION-EVIDENCE.md (target section + mapping table)
GATE 2      →  STOP — show evidence report + results — wait for "approved"
```

**Never auto-advance past a gate. Always stop and wait for explicit approval.**

---

## Pre-Flight — Source Evidence Collection

Run the Selenium source suite BEFORE writing any analysis file.

1. Navigate to the source Maven project:
   ```
   cd "<projects[re-migration].path>/API"
   ```

2. Run the full Cucumber suite:
   ```
   mvn test 2>&1 | tee target/run.log
   ```
   - If Maven unavailable: note "Source run skipped — Maven not on PATH" and continue.

3. Copy evidence to output project:
   ```
   mkdir sawslab-playwright-re\analysis\evidence\selenium
   copy target\cucumber-reports\cucumber-report.html  sawslab-playwright-re\analysis\evidence\selenium\
   copy target\cucumber-reports\cucumber-report.json  sawslab-playwright-re\analysis\evidence\selenium\
   copy target\run.log  sawslab-playwright-re\analysis\evidence\selenium\
   ```

4. Create `sawslab-playwright-re/analysis/MIGRATION-EVIDENCE.md` with the source section:

```markdown
# RE Migration Evidence Report

> **Strategy:** Reverse Engineering — Selenium → Analysis → User Stories → Playwright
> **Source:** Selenium + Cucumber (Java) → **Target:** Playwright TypeScript
> **Output project:** sawslab-playwright-re/

## 1. Source Execution — Selenium + Cucumber
| Run date | Command | Report |
|---|---|---|
| <date> | `mvn test` in `<sourceRoot>/API` | `analysis/evidence/selenium/cucumber-report.html` |

### Source Results
| # | Feature | Scenario | Tags | Status | Screenshot |
|---|---|---|---|---|---|
(fill from cucumber-report.json or feature file inventory)
> Total: X passed, Y failed

## 2. Target Execution — Playwright TypeScript
> _Populated after Stage 3 completes._

## 3. Migration Mapping — RE Evidence
> _Populated after Stage 3 completes._
```

5. Create `sawslab-playwright-re/analysis/DEMO-SCRIPT.md` with the Opening section.

---

## Stage 1 — Analyze Each Selenium Feature

Read `.claude/knowledge/selenium-patterns.md` for API mapping reference.

For every feature in `selenium-source.json` features list (or every `.feature` file found), produce:

### `analysis/<Feature>/analysis.md`
```
## File Metadata
- Language / Framework / Class name / Base URL / Imports

## Test Methods (Scenarios)
For each Scenario:
  - Name + intent (plain English)
  - Ordered steps: NAVIGATE | CLICK | TYPE | SELECT | ASSERT | WAIT
  - Assertions made (exact values from source)
  - Business logic / data dependencies

## Shared Elements
- Setup / teardown hooks
- Page objects used

## Conversion Notes
- Confidence: High / Medium / Low per test
- Risks and data dependencies
```

### `analysis/<Feature>/locators.md`
Table: `Element Name | Selenium Locator | Confidence | Proposed Playwright Locator`

Confidence: High = stable ID/testid | Medium = class/text | Low = XPath/dynamic
Locator preference: `getByTestId` → `getByRole` → `getByLabel` → `getByText` → CSS → XPath

Append `[Stage 1]` section to `analysis/DEMO-SCRIPT.md` after all Stage 1 files are written.

---

## Stage 2 — Generate User Stories

Read `.claude/knowledge/user-story-standards.md` before writing.

For every `analysis/<Feature>/analysis.md`, create `analysis/<Feature>/user_stories.md`:

```markdown
## Traceability Table
| Selenium Scenario | Tags | Covered by |
|---|---|---|

## Story <Feature>-<N>: <Actor> — <Capability>

**As a** <actor>
**I want to** <action>
**So that** <business value>

### Acceptance Criteria

#### AC-<N>: <Observable outcome>
<One sentence — observable business outcome, no implementation detail>

**Business Logic:**
- <Rule>
```

Rules:
- Zero implementation details — no locators, CSS, XPath, class names
- Every Selenium scenario maps to exactly one AC
- ACs describe observable outcomes, not UI mechanics
- Aim for 1–3 stories per feature

Append `[Stage 2]` section to `analysis/DEMO-SCRIPT.md`.

---

## GATE 1 — Stop Here

Append `[Gate 1]` section to `analysis/DEMO-SCRIPT.md`. Then **STOP**.

Show:
| Feature | Story ID | Title | AC count |
|---|---|---|---|

Ask:
> "All user stories are ready for business review.
> Type **'approved'** to proceed to Stage 3 (Playwright implementation), or provide feedback."

Do **not** proceed until the user types "approved".

---

## Stage 3 — Implement Playwright TypeScript (Gate 1 approved only)

Read before generating any code:
- `.claude/knowledge/framework-architecture.md`
- `.claude/knowledge/coding-standards.md`
- `.claude/knowledge/stage3-implementation.md`

Output into `sawslab-playwright-re/src/modules/<feature>/`:

```
src/modules/<feature>/
  <page>.page.ts        ← Page Object: readonly locators + action methods
  <feature>.spec.ts     ← Spec: test cases matching user story IDs
```

### Page Object rules
- All locators are `readonly` properties
- One method per action — no assertions in page objects
- Reuse existing modules from `.claude/knowledge/project-manifest.md`

### Spec rules
- Test names include story ID: `@<tag> @<Feature>-<N> <description>`
- `expect()` assertions mirror the AC exactly
- No `page.waitForTimeout()` — use `toBeVisible()`, `toBeEnabled()`, `waitFor()`
- API tests: `test('...', async ({ request }) => {`

### Locator preference order
1. `getByTestId` — `data-testid` attribute
2. `getByRole` — ARIA role + accessible name
3. `getByLabel` — labelled form fields
4. `getByPlaceholder`
5. `getByText('...', { exact: true })`
6. CSS selector
7. XPath — last resort, add `// VERIFY: brittle locator`

---

## Run and Heal

From `sawslab-playwright-re/`:
```
npx playwright test --workers=1 --reporter=html,line
```

Classify failures:
| Failure type | Action |
|---|---|
| TypeScript compile error | Fix import / type |
| Locator not found | Update using strategy above |
| Assertion value mismatch | Verify vs source; update if source was wrong |
| Network / 429 | Back off, retry — do NOT change locators |

Single feature: `npx playwright test src/modules/<f>/<f>.spec.ts --project=chromium`

Repeat fix → run → fix until all green.

---

## Evidence Report — Complete MIGRATION-EVIDENCE.md

After all tests pass, update `sawslab-playwright-re/analysis/MIGRATION-EVIDENCE.md`:

**Section 2 — Target Execution (Playwright):**
```markdown
## 2. Target Execution — Playwright TypeScript
| Run date | Command | Report | Screenshots |
|---|---|---|---|
| <date> | `npx playwright test --workers=1 --reporter=html,line` | `playwright-report/index.html` | `test-results/` subfolders |

| # | Suite | Test Name | Story/AC | Tags | Status | Screenshot File |
|---|---|---|---|---|---|---|
| 1 | Web: SauceDemo Login | Successful login | WEB-01/AC-1 | @smoke @positive | ✅ PASS | `test-results/modules-web-.../test-finished-1.png` |
(API tests: N/A — no browser)
> Total: X passed | HTML report: playwright-report/index.html
> Screenshots: test-results/<test-folder>/test-finished-1.png (all web tests captured)
```

**Section 3 — Migration Mapping:**
```markdown
## 3. Migration Mapping — RE Evidence
> Strategy: Reverse Engineering (Selenium → Analysis → User Stories → Playwright)
| # | Source Scenario | Story/AC | Playwright Test | Selenium | Playwright | Migrated |
|---|---|---|---|---|---|---|
| 1 | <scenario name> | <Story>-<N>/AC-<N> | <playwright test> | ✅ | ✅ | ✅ |
> Migration completeness: X/X (100%)
```

**Section 4 — Screenshot Evidence (MANDATORY for business sign-off):**
```markdown
## 4. Screenshot Evidence

> Business proof: screenshots show the application running under both frameworks.
> Source screenshots prove the original tests worked.
> Target screenshots prove the migrated tests work in Playwright.

### Source Screenshots — Selenium + Cucumber
| Evidence Type | Location | View With |
|---|---|---|
| Failure screenshots (embedded) | `analysis/evidence/selenium/cucumber-report.html` | Any browser |
| Full execution log | `analysis/evidence/selenium/run.log` | Text editor |

### Target Screenshots — Playwright
| Evidence Type | Location | View With |
|---|---|---|
| Per-test screenshots (ALL web tests) | `test-results/<test-folder>/test-finished-1.png` | Image viewer |
| Full interactive report with screenshots | `playwright-report/index.html` | `npx playwright show-report` |

### Screenshot Comparison (Source vs Target)
| Test | Source Screenshot | Playwright Screenshot |
|---|---|---|
| Successful login | In cucumber-report.html (pass = no screenshot; failure = embedded) | `test-results/.../test-finished-1.png` |
| Invalid credentials | Embedded in cucumber-report.html on failure | `test-results/.../test-finished-1.png` |
| Add to cart | Embedded in cucumber-report.html on failure | `test-results/.../test-finished-1.png` |
```

---

## GATE 2 — Stop Here

Show:
- Evidence summary from `analysis/MIGRATION-EVIDENCE.md`
- Test results (passed/failed/skipped per feature)
- Report locations:
  - Selenium HTML: `analysis/evidence/selenium/cucumber-report.html`
  - Playwright HTML: `playwright-report/index.html`
  - Screenshots: `test-results/` subfolders

Ask:
> "All tests pass and the Migration Evidence Report is complete. Review `analysis/MIGRATION-EVIDENCE.md`.
> Type **'approved'** to finalize, or provide feedback."

---

## Environment Reference

| Key | Value |
|---|---|
| Source config | `selenium-source.json` → `projects["re-migration"]` |
| Output project | `sawslab-playwright-re/` |
| Source run | `mvn test` in `<sourceRoot>/API` |
| Playwright run | `npx playwright test --workers=1 --reporter=html,line` |
| Evidence report | `sawslab-playwright-re/analysis/MIGRATION-EVIDENCE.md` |
| Playwright report | `sawslab-playwright-re/playwright-report/index.html` |
| Screenshots | `sawslab-playwright-re/test-results/` |
