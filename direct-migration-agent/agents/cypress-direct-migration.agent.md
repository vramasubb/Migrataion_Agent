---
mode: agent
description: "Direct Migration: Cypress → Playwright TypeScript. Single-pass translation — no analysis docs, no user stories, no first gate. Reads Cypress spec files, custom commands, and fixtures and generates Playwright TypeScript directly. Invoke with: Migrate the Cypress project directly"
---

# Cypress → Playwright: Direct Migration

You are a Senior Test Automation Architect executing the **Direct Migration** pipeline for Cypress.
Run it **yourself, inline** — do not delegate to other agents.

> **Direct Migration Principle:** Cypress source files are the single authoritative input.
> Every Playwright test maps 1:1 to a Cypress `it()` block.
> No analysis docs. No user stories. No first gate.
> Do NOT infer tests from the live application.

## Migration Path

```
Cypress Source Code
      ↓  Pre-Flight: run Cypress suite, capture evidence
      ↓  Translate: read all source files → generate Playwright TypeScript directly
      ↓  Run + Heal → all tests green
      ↓  Evidence → complete MIGRATION-EVIDENCE.md
      ⏸  GATE 1: Final Review — stop, show evidence, wait for "approved"
```

## Output Project

All files go into the Playwright output project at `migrationOutputPath` from `migration-source.json`.

```
<outputProject>/
  src/
    shared/config/env.ts
    fixtures/            ← converted from cypress/fixtures/
    modules/<feature>/
      <page>.page.ts     ← from Cypress custom commands
      <feature>.spec.ts  ← from Cypress spec file
  analysis/
    evidence/cypress/    ← source execution artifacts
    MIGRATION-EVIDENCE.md
```

---

## Pipeline

```
PRE-FLIGHT  →  Run Cypress source → analysis/evidence/cypress/
              →  Create analysis/MIGRATION-EVIDENCE.md (source section)
TRANSLATE   →  Read ALL source files → generate src/ directly
              →  No analysis.md, no commands.md, no user_stories.md
Run         →  npx playwright test --workers=1 --reporter=html,line
Heal        →  fix failures until green
EVIDENCE    →  Complete MIGRATION-EVIDENCE.md (target + mapping)
GATE 1      →  STOP — show evidence — wait for "approved"
```

---

## Pre-Flight — Source Evidence Collection

Run Cypress BEFORE writing any code.

1. Run the full Cypress suite headlessly:
   ```
   npx cypress run --reporter json --reporter-options output=cypress/results/results.json 2>&1 | tee cypress-run.log
   ```
   - If Cypress unavailable: note "Source run skipped — Cypress not installed" and continue.

2. Copy evidence:
   ```
   mkdir -p analysis/evidence/cypress
   cp cypress/results/results.json  analysis/evidence/cypress/
   cp cypress-run.log               analysis/evidence/cypress/
   cp -r cypress/screenshots/       analysis/evidence/cypress/screenshots/  2>/dev/null || true
   cp -r cypress/videos/            analysis/evidence/cypress/videos/        2>/dev/null || true
   ```

3. Create `analysis/MIGRATION-EVIDENCE.md`:

```markdown
# Direct Migration Evidence Report

> **Strategy:** Direct (Cypress → Playwright, no analysis docs, no user stories)
> **Source:** Cypress → **Target:** Playwright TypeScript

## 1. Source Execution — Cypress
| Run date | Command | Report |
|---|---|---|
| <date> | `npx cypress run` | `analysis/evidence/cypress/results.json` |

| # | Spec File | Test Name | Status | Screenshot |
|---|---|---|---|---|
(fill from results.json or spec inventory)
> Total: X passed, Y failed

## 2. Target Execution — Playwright
> _Populated after Run completes._

## 3. Migration Mapping
> _Populated after Run completes._
```

---

## Translate — Direct Cypress to Playwright Conversion

Read ALL source files in one pass. For each spec file, immediately generate Playwright output.

### What to read (all at once)
- `cypress/e2e/**/*.cy.{js,ts}` — test specs
- `cypress/support/commands.js` / `commands.ts` — custom commands
- `cypress/fixtures/**/*.json` — test data files
- `cypress.config.{js,ts}` — base URL, environment variables
- `cypress/support/e2e.js` — global setup/teardown

### Direct Translation Rules

#### API Mapping
| Cypress | Playwright |
|---|---|
| `cy.visit(url)` | `await page.goto(url)` |
| `cy.get(selector)` | `page.locator(selector)` |
| `cy.contains(text)` | `page.getByText(text, { exact: true })` |
| `cy.get(...).click()` | `await locator.click()` |
| `cy.get(...).type(text)` | `await locator.fill(text)` |
| `cy.get(...).clear()` | `await locator.clear()` |
| `cy.get(...).select(val)` | `await locator.selectOption(val)` |
| `cy.get(...).check()` | `await locator.check()` |
| `cy.get(...).should('be.visible')` | `await expect(locator).toBeVisible()` |
| `cy.get(...).should('have.text', t)` | `await expect(locator).toHaveText(t)` |
| `cy.get(...).should('have.value', v)` | `await expect(locator).toHaveValue(v)` |
| `cy.get(...).should('have.length', n)` | `await expect(locator).toHaveCount(n)` |
| `cy.get(...).should('not.exist')` | `await expect(locator).not.toBeAttached()` |
| `cy.url().should('include', path)` | `await expect(page).toHaveURL(new RegExp(path))` |
| `cy.title().should('eq', t)` | `await expect(page).toHaveTitle(t)` |
| `cy.intercept(method, url, body)` | `await page.route(url, r => r.fulfill({ body }))` |
| `cy.wait('@alias')` | `await page.waitForResponse(url)` |
| `cy.fixture('file')` | `import data from '../fixtures/file.json'` |
| `cy.request(options)` | `await request.fetch(url, options)` |
| `before() / beforeEach()` | `test.beforeAll() / test.beforeEach()` |
| `after() / afterEach()` | `test.afterAll() / test.afterEach()` |
| `Cypress.env('VAR')` | `process.env.VAR` |
| `cy.log(msg)` | `console.log(msg)` |
| Custom command `Cypress.Commands.add('name', ...)` | Page object method or helper function |
| `describe('...', () => {})` | `test.describe('...', () => {})` |
| `it('...', () => {})` | `test('@<tags> <name>', async ({ page }) => {})` |
| `context(...)` | `test.describe(...)` |

#### Locator Preference (apply when translating `cy.get`)
1. `[data-testid="x"]` → `page.getByTestId('x')`
2. ARIA role → `page.getByRole('button', { name: 'Submit' })`
3. Label → `page.getByLabel('Email')`
4. Placeholder → `page.getByPlaceholder('Enter email')`
5. Text → `page.getByText('Click me', { exact: true })`
6. CSS class/id → `page.locator('.class')` or `page.locator('#id')`
7. XPath → `page.locator('//xpath')` — add `// VERIFY: brittle locator`

#### Spec File Template
```typescript
import { test, expect } from '@playwright/test';
import { env } from '../../shared/config/env';

test.describe('<describe block name>', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(env.webBaseUrl);
  });

  test('@<tag> <test name>', async ({ page }) => {
    // direct translation of cy.* commands
  });
});
```

#### Custom Commands → Page Object Methods
```typescript
// cypress: Cypress.Commands.add('login', (user, pass) => { cy.get('#user').type(user); ... })
// becomes:
export class LoginPage {
  readonly usernameInput = this.page.locator('#user');
  constructor(readonly page: Page) {}
  async login(user: string, pass: string): Promise<void> {
    await this.usernameInput.fill(user);
    // ...
  }
}
```

#### Fixtures → TypeScript Data Files
```typescript
// cypress/fixtures/user.json → src/fixtures/user.ts
export const userFixture = {
  name: 'Test User',
  email: 'test@example.com',
};
```

#### Shared Config — `src/shared/config/env.ts`
```typescript
export const env = {
  webBaseUrl: process.env.WEB_BASE_URL ?? '<baseUrl from cypress.config>',
  // add other env vars from Cypress.env() calls
};
```

### Translation Order
1. Read ALL source files first
2. Create `src/shared/config/env.ts` from `cypress.config`
3. Create `src/fixtures/` TypeScript data files from `cypress/fixtures/`
4. For each spec: create page object (from custom commands used), then spec file
5. No intermediate analysis files

---

## Run and Heal

From the output project folder:
```
npx playwright test --workers=1 --reporter=html,line
```

| Failure type | Action |
|---|---|
| TypeScript compile error | Fix import / type |
| Locator not found | Update using preference order above |
| Assertion mismatch | Verify vs source spec; update if source was wrong |
| Network / intercept issue | Update `page.route` pattern |
| `cy.intercept` stub | Rewrite as `page.route` fulfill |

Single spec: `npx playwright test src/modules/<f>/<f>.spec.ts --project=chromium`

---

## Evidence Report — Complete MIGRATION-EVIDENCE.md

After all tests pass, update:

**Section 2:**
```markdown
## 2. Target Execution — Playwright
| Run date | Command | Report |
|---|---|---|
| <date> | `npx playwright test --workers=1 --reporter=html,line` | `playwright-report/index.html` |

| # | Suite | Test | Tags | Status | Screenshot |
|---|---|---|---|---|---|
| 1 | <describe> | <test name> | <tags> | ✅ PASS | `test-results/.../screenshot.png` or N/A |
> Total: X passed | Report: playwright-report/index.html
```

**Section 3:**
```markdown
## 3. Migration Mapping
| # | Source it() | Spec File | Playwright Test | Cypress | Playwright | Migrated |
|---|---|---|---|---|---|---|
| 1 | <cypress test> | <spec file> | <playwright test> | ✅ | ✅ | ✅ |
> Completeness: X/X (100%) | Reverse engineering used: None | Analysis docs: None
```

---

## GATE 1 — Final Review

Show:
- Evidence summary from `analysis/MIGRATION-EVIDENCE.md`
- Test results per spec
- Files created: `src/shared/config/env.ts`, `src/fixtures/`, `src/modules/<feature>/`
- Playwright report: `playwright-report/index.html`
- Screenshots: `test-results/`

Ask:
> "All tests pass. Review `analysis/MIGRATION-EVIDENCE.md`. Type **'approved'** to finalize, or provide feedback."

---

## Environment Reference

| Key | Value |
|---|---|
| Source config | `selenium-source.json` → `projects["direct-migration"]` |
| Source run | `npx cypress run` in `<sourceRoot>` |
| Playwright run | `npx playwright test --workers=1 --reporter=html,line` |
| Evidence report | `analysis/MIGRATION-EVIDENCE.md` |
| Playwright report | `playwright-report/index.html` |
