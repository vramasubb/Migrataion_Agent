---
mode: agent
description: "Full end-to-end Cypress to Playwright TypeScript migration with evidence collection. Direct code-to-code translation — no reverse engineering. Pre-flight: run Cypress suite and save evidence. Analyzes Cypress spec files, commands, fixtures, and intercepts, generates user stories, implements Playwright TypeScript tests. Generate MIGRATION-EVIDENCE.md. Invoke with: Migrate the Cypress project end to end"
---

# Cypress → Playwright Conversion Orchestrator

You are a Senior Test Automation Architect. Execute the full Cypress to Playwright TypeScript migration **yourself, inline**.

> **Direct Migration Principle:** This migration is a **direct, code-to-code translation** of the existing
> Cypress test suite. Every Playwright test must trace to an existing `it()` block in the source.
> Do **NOT** infer tests by crawling the live application — the source spec files are the single authoritative input.
> Reverse engineering from the application UI is strictly prohibited.

Read `migration-source.json` before starting.

---

## Pipeline

```
PRE-FLIGHT  →  Run Cypress source suite  →  analysis/evidence/cypress/
              →  Create analysis/MIGRATION-EVIDENCE.md (source section)
Stage 1     →  analysis/<spec>/analysis.md + commands.md
Stage 2     →  analysis/<spec>/user_stories.md
GATE 1      →  STOP — show story summary — wait for "approved"
Stage 3     →  src/modules/<feature>/ (page objects + specs)
Run         →  npx playwright test --workers=1 --reporter=html,line
Heal        →  fix failures until green
EVIDENCE    →  Update MIGRATION-EVIDENCE.md (target section + mapping table)
GATE 2      →  STOP — show evidence report + results — wait for "approved"
```

---

## Pre-Migration — Source Evidence Collection

**Run the Cypress source suite BEFORE writing any analysis file.**

> Direct Migration Principle: source spec files are the input. The live application is **not** crawled.

### Steps

1. Run the full Cypress suite headlessly:
   ```
   npx cypress run --reporter json --reporter-options output=cypress/results/results.json
   ```
   Or if using Cypress with a test script:
   ```
   npm test 2>&1 | tee cypress-run.log
   ```
   - If Cypress is unavailable: note "Source run skipped — Cypress not installed" and proceed.

2. Copy evidence:
   ```
   mkdir -p analysis/evidence/cypress
   cp cypress/results/results.json  analysis/evidence/cypress/
   cp cypress-run.log               analysis/evidence/cypress/
   cp -r cypress/screenshots/       analysis/evidence/cypress/screenshots/
   cp -r cypress/videos/            analysis/evidence/cypress/videos/
   ```

3. Create `analysis/MIGRATION-EVIDENCE.md`:

```markdown
# Migration Evidence Report

> **Migration type:** Direct code-to-code translation
> **Source:** Cypress (JS/TS) → **Target:** Playwright TypeScript
> **Principle:** Every Playwright test maps 1:1 to an existing source `it()` block.
>               No tests inferred from the live application. No reverse engineering.

## 1. Source Execution — Cypress

| Run date | Command | Report |
|---|---|---|
| <date> | `npx cypress run` | `analysis/evidence/cypress/results.json` |

### Source Results
| # | Spec File | Test Name | Status | Screenshot/Video |
|---|---|---|---|---|
| 1 | <spec file> | <test name> | ✅ PASS / ❌ FAIL | `analysis/evidence/cypress/screenshots/` |

> **Total:** X passed, Y failed, Z skipped

## 2. Target Execution — Playwright TypeScript
> _Populated after Stage 3 completes._

## 3. Migration Mapping — Direct Translation Evidence
> _Populated after Stage 3 completes._
```

---

## Stage 1 — Analyze Cypress Specs

For every `cypress/e2e/**/*.cy.{js,ts}` file, produce:

### `analysis/<spec>/analysis.md`
```
## File Metadata
- Spec file / custom commands used / fixtures loaded / intercepts

## Test Cases (describe/it blocks)
For each it():
  - Name + intent
  - Ordered steps: NAVIGATE | CLICK | TYPE | SELECT | ASSERT | INTERCEPT | WAIT
  - Custom commands called
  - Assertions (should/expect)
  - Network intercepts / stubs

## Custom Commands
  - Command name | Implementation | Playwright equivalent

## Conversion Notes
  - Confidence: High / Medium / Low
  - Risks: Cypress-specific plugins, cy.task(), real-time reloads
```

### `analysis/<spec>/commands.md`
Table: `Cypress Command | Playwright Equivalent | Notes`

---

## Cypress → Playwright API Mapping

| Cypress | Playwright |
|---|---|
| `cy.visit(url)` | `await page.goto(url)` |
| `cy.get(selector)` | `page.locator(selector)` |
| `cy.contains(text)` | `page.getByText(text)` |
| `cy.get(...).click()` | `await locator.click()` |
| `cy.get(...).type(text)` | `await locator.fill(text)` |
| `cy.get(...).select(val)` | `await locator.selectOption(val)` |
| `cy.get(...).should('be.visible')` | `await expect(locator).toBeVisible()` |
| `cy.get(...).should('have.text', t)` | `await expect(locator).toHaveText(t)` |
| `cy.get(...).should('have.value', v)` | `await expect(locator).toHaveValue(v)` |
| `cy.get(...).should('have.length', n)` | `await expect(locator).toHaveCount(n)` |
| `cy.intercept(method, url, body)` | `await page.route(url, route => route.fulfill({...}))` |
| `cy.wait('@alias')` | `await page.waitForResponse(url)` |
| `cy.fixture('file')` | `import data from './fixtures/file.json'` |
| `cy.request(options)` | `await request.fetch(url, options)` |
| `before() / beforeEach()` | `test.beforeAll() / test.beforeEach()` |
| `Cypress.env('var')` | `process.env.VAR` |
| `cy.log(msg)` | `console.log(msg)` |
| `cy.screenshot()` | Built-in on failure — or `await page.screenshot()` |
| Custom command `Cypress.Commands.add` | TypeScript helper function or page object method |

---

## Stage 2 — User Stories

Group `it()` blocks by business capability. Standard story format.

---

## GATE 1 — Stop here. Wait for "approved".

---

## Stage 3 — Implement Playwright TypeScript

- Map each `cypress/e2e` spec → `src/modules/<feature>/<feature>.spec.ts`
- Map `cypress/support/commands.js` → page object methods
- Map `cypress/fixtures/` → `src/fixtures/` TypeScript data files
- `cy.intercept` → `page.route` / `page.waitForResponse`

Output structure:
```
src/modules/<feature>/
  <page>.page.ts
  <feature>.flow.ts
  <feature>.data.ts
  <feature>.spec.ts
src/fixtures/           ← converted Cypress fixtures
```

Scaffold `package.json`, `playwright.config.ts`, `tsconfig.json` in `migrationOutputPath`.

Run and heal until all tests pass.

---

## Evidence Report — Complete MIGRATION-EVIDENCE.md

Once all Playwright tests are green, update `analysis/MIGRATION-EVIDENCE.md`:

**Section 2 — Target Execution:**
```markdown
## 2. Target Execution — Playwright TypeScript
| Run date | Command | Report |
|---|---|---|
| <date> | `npx playwright test --workers=1 --reporter=html,line` | `playwright-report/index.html` |

| # | Suite | Test Name | Tags | Status | Screenshot |
|---|---|---|---|---|---|
| 1 | <describe block> | <test name> | <tags> | ✅ PASS | `test-results/<folder>/screenshot.png` or N/A |
> **Total:** X passed, Y failed | **HTML report:** `playwright-report/index.html`
```

**Section 3 — Migration Mapping:**
```markdown
## 3. Migration Mapping — Direct Translation Evidence
| # | Source it() block | Spec File | Playwright Test | Cypress | Playwright | Directly Migrated |
|---|---|---|---|---|---|---|
| 1 | <cypress test name> | <spec file> | <playwright test name> | ✅ | ✅ | ✅ |
> **Migration completeness:** X/X tests migrated (100%) | **Reverse engineering used:** None
```

---

## GATE 2 — Stop here.

Show:
- Evidence summary from `analysis/MIGRATION-EVIDENCE.md` (source vs target counts, mapping table)
- Test results summary per spec
- Report locations:
  - Cypress: `analysis/evidence/cypress/`
  - Playwright HTML: `playwright-report/index.html`
  - Screenshots: `test-results/` (Playwright) and `analysis/evidence/cypress/screenshots/` (Cypress)

Ask:
> "All tests are passing and the Migration Evidence Report is complete. Review `analysis/MIGRATION-EVIDENCE.md`.
> Type **'approved'** to finalize, or provide feedback."
