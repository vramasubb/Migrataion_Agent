---
mode: agent
description: "Direct Migration: Selenium Framework → Playwright TypeScript. Single-pass code-to-code translation. SKIPS: analysis docs, user stories, business review gate. One final gate only. Invoke with: Migrate the Selenium framework directly"
---

# Selenium → Playwright: Direct Migration

You are a Senior Test Automation Architect executing the **Direct Migration** pipeline.
Run it **yourself, inline** — do not delegate to other agents.

> ⚠️ **DIRECT MIGRATION — NO USER STORIES**
> This pipeline translates Selenium source code **directly** into Playwright TypeScript.
> The following steps are **permanently skipped** — they belong only to Reverse Engineering:
> ❌ Stage 1: analysis.md generation
> ❌ Stage 1: locators.md generation
> ❌ Stage 2: user_stories.md generation
> ❌ Gate 1: business review
> The source code IS the specification. Start writing Playwright TypeScript immediately after pre-flight.

## Migration Path

```
Selenium Source Code
      ↓  PRE-FLIGHT: run source tests, capture evidence
      |  [❌ SKIP: analysis docs]  [❌ SKIP: user stories]  [❌ SKIP: Gate 1]
      ↓  TRANSLATE: read ALL source files → generate Playwright TypeScript in one pass
      ↓  RUN: npx playwright test --workers=1 --reporter=html,line
      ↓  HEAL: fix failures until all green
      ↓  EVIDENCE: complete MIGRATION-EVIDENCE.md
      ⏸  GATE 1: Final Review — show evidence, wait for "approved"
```

## Comparison with Reverse Engineering Path

| | Direct Migration | Reverse Engineering Migration |
|---|---|---|
| Analysis docs | ❌ None | ✅ analysis.md + locators.md |
| User stories | ❌ None | ✅ user_stories.md |
| Business gate | ❌ 1 gate (final only) | ✅ 2 gates (business review + final) |
| Speed | ⚡ Faster | 🐢 Slower (more documentation) |
| Documentation | Code only | Code + business artefacts |
| Use when | Technical team, urgent | Business sign-off required |

## Output Project

All generated files go into `sawslab-playwright-dm/` (already scaffolded).

```
sawslab-playwright-dm/
  package.json
  playwright.config.ts
  tsconfig.json
  .env
  analysis/
    evidence/selenium/          ← source execution artefacts
    MIGRATION-EVIDENCE.md       ← final evidence report
  src/
    shared/config/env.ts
    modules/
      <feature>/
        <page>.page.ts          ← translated from Selenium page object
        <feature>.spec.ts       ← translated from Cucumber feature
```

> No `analysis/<Feature>/analysis.md`, `locators.md`, or `user_stories.md` are created.
> The source code itself is the specification.

## Before you start — read these files

1. `selenium-source.json` → `projects["direct-migration"].path` for source root
2. `analysis/INVENTORY.md` in the output project (skip if absent — likely not present)
3. `.claude/knowledge/conversion-rules.md` — source fidelity rules
4. `.claude/knowledge/selenium-patterns.md` — Selenium → Playwright API mapping
5. `.claude/knowledge/coding-standards.md` — locator strategy, assertions

The Selenium source project is **external and read-only** — never write files into it.

---

## Pipeline

```
PRE-FLIGHT  →  Run Selenium source suite  →  analysis/evidence/selenium/
              →  Create analysis/MIGRATION-EVIDENCE.md (source section)
[❌ SKIP]    →  Stage 1: analysis.md + locators.md   ← RE only, NOT needed here
[❌ SKIP]    →  Stage 2: user_stories.md              ← RE only, NOT needed here
[❌ SKIP]    →  Gate 1: business review               ← RE only, NOT needed here
TRANSLATE   →  Read ALL Selenium source files → generate src/modules/<feature>/ directly
RUN         →  npx playwright test --workers=1 --reporter=html,line
HEAL        →  fix failures one feature at a time until green
              →  use playwright-healer.agent.md for complex failures
EVIDENCE    →  Update MIGRATION-EVIDENCE.md (target section + mapping table)
GATE 1      →  STOP — show evidence report — wait for "approved"
```

**One gate only. If you find yourself writing analysis.md or user_stories.md, STOP — you are running the wrong pipeline.**

---

## Pre-Flight — Source Evidence Collection

Run the Selenium source suite BEFORE writing any code.

1. Navigate to the source Maven project:
   ```
   cd "<projects[direct-migration].path>/API"
   ```

2. Run the full Cucumber suite with screenshots enabled:
   ```
   mvn test 2>&1 | tee target/run.log
   ```
   - If Maven unavailable: note "Source run skipped — Maven not on PATH" and continue.
   - Screenshots for @web scenarios are **automatically embedded** in the Cucumber HTML report
     via `Hooks.java` `@After` hook (`scenario.attach(screenshot, "image/png", ...)`)

3. Copy evidence to output project:
   ```
   mkdir sawslab-playwright-dm\analysis\evidence\selenium\screenshots
   copy target\cucumber-reports\cucumber-report.html  sawslab-playwright-dm\analysis\evidence\selenium\
   copy target\cucumber-reports\cucumber-report.json  sawslab-playwright-dm\analysis\evidence\selenium\
   copy target\run.log  sawslab-playwright-dm\analysis\evidence\selenium\
   ```
   > Source screenshots are **embedded inside `cucumber-report.html`** (failures only).
   > Open `analysis/evidence/selenium/cucumber-report.html` in a browser to see them.

4. Create `sawslab-playwright-dm/analysis/MIGRATION-EVIDENCE.md` with the source section:

```markdown
# Direct Migration Evidence Report

> **Strategy:** Direct Migration — Selenium → Playwright (no analysis docs, no user stories)
> **Source:** Selenium + Cucumber (Java) → **Target:** Playwright TypeScript

---

## 1. Source Execution — Selenium + Cucumber

| Run date | Command | Report | Screenshots |
|---|---|---|---|
| <date> | `mvn test` in `<sourceRoot>/API` | `analysis/evidence/selenium/cucumber-report.html` | Embedded in HTML report |

### Source Results
| # | Feature | Scenario | Tags | Status | Screenshot Location |
|---|---|---|---|---|---|
(fill from cucumber-report.json or feature file inventory)
**Screenshot note:** @web failure screenshots are embedded in `cucumber-report.html`.
@api tests have no browser — N/A.
> Total: X passed, Y failed

---

## 2. Target Execution — Playwright TypeScript
> _Populated after Run completes._

---

## 3. Migration Mapping — Direct Translation Evidence
> _Populated after Run completes._

---

## 4. Screenshot Evidence

### Source Screenshots (Selenium)
| Test | Screenshot | Location |
|---|---|---|
| (from cucumber-report.html) | Embedded in HTML | `analysis/evidence/selenium/cucumber-report.html` |

### Target Screenshots (Playwright)
| Test | Screenshot | Location |
|---|---|---|
| (generated after migration) | `test-results/<folder>/test-finished-1.png` | `sawslab-playwright-dm/test-results/` |
```

---

## Translate — Direct Source-to-Playwright Conversion

Read all Selenium source files in a single pass. For each feature, immediately generate the
Playwright output without creating intermediate analysis files.

### What to read (all at once)
For each Cucumber feature:
- `.feature` file — the test scenarios and steps
- Step definition Java class(es) — the implementation of each step
- Page object Java class(es) — locators and action methods
- `config.properties` — base URLs, credentials

### What to generate (immediately, no intermediate files)

#### Page Objects — `src/modules/<feature>/<page>.page.ts`

Direct translation rules:
- `By.id("x")` → `this.page.locator('#x')`
- `By.cssSelector("[data-test='x']")` → `this.page.locator('[data-test="x"]')`
- `By.className("x")` → `this.page.locator('.x')`
- `By.cssSelector("button[id^='x']")` → `this.page.locator('button[id^="x"]')`
- `driver.findElement(by).sendKeys(text)` → `await locator.fill(text)`
- `driver.findElement(by).click()` → `await locator.click()`
- `driver.findElement(by).getText()` → `await locator.innerText()`
- `WebDriverWait(...).until(visibilityOf(by))` → Playwright auto-waits (remove explicit waits)
- `driver.get(url)` → `await this.page.goto(url)`
- Constructor `WebDriver driver` → Constructor `readonly page: Page`
- `List<WebElement>` + loop → `.filter({ has: locator })`

```typescript
// Template
import { type Page } from '@playwright/test';

export class <ClassName>Page {
  readonly <locatorName> = this.page.locator('<selector>');

  constructor(readonly page: Page) {}

  async <actionMethod>(<params>): Promise<void> {
    await this.<locator>.<action>();
  }
}
```

#### Spec Files — `src/modules/<feature>/<feature>.spec.ts`

Direct translation rules:
- `Scenario: <name>` → `test('@<tag> <name>', async ({ page }) => { ... })`
- `@smoke`, `@positive`, `@negative`, `@regression` tags → same tags in test name string
- `Background:` step → `test.beforeEach`
- `Given I am on the <page>` → `await loginPage.open(env.webBaseUrl)`
- `When I ... / Then I should ...` → direct Playwright actions + `expect()` assertions
- `RestAssured GET/POST/PUT/PATCH/DELETE` → `await request.get/post/put/patch/delete(...)`
- `assertEquals(expected, actual)` → `expect(actual).toBe(expected)`
- `assertTrue(condition)` → `expect(condition).toBe(true)`
- `assertNotNull(value)` → `expect(value).not.toBeNull()`
- `Scenario Outline: + Examples:` → expand inline as separate `test()` blocks

```typescript
// Template
import { test, expect } from '@playwright/test';
import { <Page>Page } from './<page>.page';
import { env } from '../../shared/config/env';

test.describe('<Feature description>', () => {
  test.beforeEach(async ({ page }) => { /* background setup */ });

  test('@<tag> <Scenario name>', async ({ page }) => {
    // direct translation of scenario steps
  });
});
```

#### Shared Config — `src/shared/config/env.ts`
```typescript
export const env = {
  webBaseUrl: process.env.WEB_BASE_URL ?? '<web.base.url from config.properties>',
  apiBaseUrl: process.env.API_BASE_URL ?? '<api.base.url from config.properties>',
  standardUser: process.env.STANDARD_USER ?? '<standard user from config>',
  standardPass: process.env.STANDARD_PASS ?? '<password from config>',
  lockedUser: process.env.LOCKED_USER ?? '<locked user from config>',
};
```

### Translation order
1. Read ALL source files first (complete picture before writing)
2. Create `src/shared/config/env.ts`
3. For each feature: create page objects first, then the spec

---

## Run and Heal

From `sawslab-playwright-dm/`:
```
npx playwright test --workers=1 --reporter=html,line
```

Classify failures:
| Failure type | Action |
|---|---|
| TypeScript compile error | Fix import / type |
| Locator not found | Update using preference order: testid → role → label → text → CSS → xpath |
| Assertion value mismatch | Verify vs source feature file; update if source was wrong |
| Network / 429 | Back off, retry — do NOT change locators |

Single feature: `npx playwright test src/modules/<f>/<f>.spec.ts --project=chromium`

Repeat fix → run → fix until all green.

---

## Evidence Report — Complete MIGRATION-EVIDENCE.md

After all tests pass, update `sawslab-playwright-dm/analysis/MIGRATION-EVIDENCE.md`:

**Section 2 — Target Execution (Playwright):**
```markdown
## 2. Target Execution — Playwright TypeScript
| Run date | Command | Report | Screenshots |
|---|---|---|---|
| <date> | `npx playwright test --workers=1 --reporter=html,line` | `playwright-report/index.html` | `test-results/` subfolders |

| # | Suite | Test Name | Tags | Status | Screenshot File |
|---|---|---|---|---|---|
| 1 | Web: SauceDemo Login | Successful login | @smoke @positive | ✅ PASS | `test-results/modules-web-.../test-finished-1.png` |
(API tests: N/A — no browser)
> Total: X passed | HTML report: playwright-report/index.html
> Screenshots: test-results/<test-folder>/test-finished-1.png (all web tests captured)
```

**Section 3 — Migration Mapping:**
```markdown
## 3. Migration Mapping — Direct Translation Evidence
| # | Source Scenario (.feature) | Playwright Test | Selenium | Playwright | Migrated |
|---|---|---|---|---|---|
| 1 | <scenario name> | <playwright test name> | ✅ / ⚠️ | ✅ | ✅ |
> Completeness: X/X (100%) | Reverse engineering: None | Analysis docs: None
```

**Section 4 — Screenshot Evidence (MANDATORY for business sign-off):**
```markdown
## 4. Screenshot Evidence

> Business proof: screenshots show the application running under both frameworks.
> Open both HTML reports to see all test screenshots with full context.

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

### Screenshot Summary
| Test | Source Screenshot | Playwright Screenshot |
|---|---|---|
| Successful login | In cucumber-report.html (pass = no screenshot) | `test-results/.../test-finished-1.png` |
| Invalid credentials | In cucumber-report.html (failure = screenshot embedded) | `test-results/.../test-finished-1.png` |
```

---

## GATE 1 — Stop Here (Final Review)

Show:
- Evidence summary from `analysis/MIGRATION-EVIDENCE.md`
- Test results (passed/failed/skipped per feature)
- Report locations:
  - Selenium HTML: `analysis/evidence/selenium/cucumber-report.html`
  - Playwright HTML: `playwright-report/index.html`
  - Screenshots: `test-results/` (web tests only)
- Files created (src/ only — no analysis docs):
  - `src/shared/config/env.ts`
  - `src/modules/<feature>/<page>.page.ts` per feature
  - `src/modules/<feature>/<feature>.spec.ts` per feature

Ask:
> "All tests pass and the Migration Evidence Report is complete.
> Review `analysis/MIGRATION-EVIDENCE.md` to confirm all scenarios are covered.
> Type **'approved'** to finalize the Direct Migration, or provide feedback."

---

## Environment Reference

| Key | Value |
|---|---|
| Source config | `selenium-source.json` → `projects["direct-migration"]` |
| Output project | `sawslab-playwright-dm/` |
| Source run | `mvn test` in `<sourceRoot>/API` |
| Playwright run | `npx playwright test --workers=1 --reporter=html,line` |
| Evidence report | `sawslab-playwright-dm/analysis/MIGRATION-EVIDENCE.md` |
| Playwright report | `sawslab-playwright-dm/playwright-report/index.html` |
| Screenshots | `sawslab-playwright-dm/test-results/` (web tests) |
