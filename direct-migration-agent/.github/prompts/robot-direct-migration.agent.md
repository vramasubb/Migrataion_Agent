---
mode: agent
description: "Direct Migration: Robot Framework → Playwright TypeScript. Single-pass translation — no analysis docs, no user stories, no first gate. Reads Robot .robot and .resource files and generates Playwright TypeScript directly. Invoke with: Migrate the Robot Framework project directly"
---

# Robot Framework → Playwright: Direct Migration

You are a Senior Test Automation Architect executing the **Direct Migration** pipeline for Robot Framework.
Run it **yourself, inline** — do not delegate to other agents.

> **Direct Migration Principle:** Robot Framework `.robot` and `.resource` files are the single
> authoritative input. Every Playwright test maps 1:1 to a Robot test case.
> No analysis docs. No keyword docs. No user stories. No first gate.
> Do NOT infer tests from the live application.

## Migration Path

```
Robot Framework Source
      ↓  Pre-Flight: run Robot suite, capture evidence
      ↓  Translate: read all .robot/.resource files → generate Playwright TypeScript directly
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
    modules/<suite>/
      <page>.page.ts     ← from .resource keywords and SeleniumLibrary calls
      <suite>.spec.ts    ← from Robot test cases
  analysis/
    evidence/robot/      ← Robot Framework execution artifacts
    MIGRATION-EVIDENCE.md
```

---

## Pipeline

```
PRE-FLIGHT  →  Run Robot source → analysis/evidence/robot/
              →  Create analysis/MIGRATION-EVIDENCE.md (source section)
TRANSLATE   →  Read ALL .robot/.resource files → generate src/ directly
              →  No analysis.md, no keywords.md, no user_stories.md
Run         →  npx playwright test --workers=1 --reporter=html,line
Heal        →  fix failures until green
EVIDENCE    →  Complete MIGRATION-EVIDENCE.md (target + mapping)
GATE 1      →  STOP — show evidence — wait for "approved"
```

---

## Pre-Flight — Source Evidence Collection

Run Robot Framework BEFORE writing any code.

1. Run the full suite:
   ```
   python -m robot --outputdir analysis/evidence/robot <source_suite_dir> 2>&1 | tee robot-run.log
   ```
   Robot auto-generates `output.xml`, `report.html`, `log.html` in the outputdir.
   - If Robot unavailable: note "Source run skipped — Robot Framework not installed" and continue.

2. `analysis/evidence/robot/` is already populated by the run above. Also copy the log:
   ```
   cp robot-run.log analysis/evidence/robot/
   ```

3. Create `analysis/MIGRATION-EVIDENCE.md`:

```markdown
# Direct Migration Evidence Report

> **Strategy:** Direct (Robot Framework → Playwright, no analysis docs, no user stories)
> **Source:** Robot Framework → **Target:** Playwright TypeScript

## 1. Source Execution — Robot Framework
| Run date | Command | Report |
|---|---|---|
| <date> | `python -m robot <suite_dir>` | `analysis/evidence/robot/report.html` |

| # | Suite | Test Case | Tags | Status | Screenshot |
|---|---|---|---|---|---|
(fill from output.xml or test case inventory)
> Total: X passed, Y failed

## 2. Target Execution — Playwright
> _Populated after Run completes._

## 3. Migration Mapping
> _Populated after Run completes._
```

---

## Translate — Direct Robot to Playwright Conversion

Read ALL `.robot` and `.resource` files in one pass. For each suite, immediately generate output.

### What to read (all at once)
- `**/*.robot` — test suites (contain Test Cases)
- `**/*.resource` — resource files (contain Keywords, Variables)
- `*.py` custom libraries imported by the suite
- `robot.yaml` or `pyproject.toml` for configuration

### Direct Translation Rules

#### API Mapping
| Robot Framework | Playwright |
|---|---|
| `Open Browser  ${URL}  chrome` | `await page.goto(url)` |
| `Go To  ${URL}` | `await page.goto(url)` |
| `Click Element  locator` | `await page.locator(sel).click()` |
| `Input Text  locator  text` | `await page.locator(sel).fill(text)` |
| `Clear Element Text  locator` | `await page.locator(sel).clear()` |
| `Select From List By Value  locator  value` | `await page.locator(sel).selectOption(value)` |
| `Select Checkbox  locator` | `await page.locator(sel).check()` |
| `Unselect Checkbox  locator` | `await page.locator(sel).uncheck()` |
| `Element Should Be Visible  locator` | `await expect(page.locator(sel)).toBeVisible()` |
| `Element Should Not Be Visible  locator` | `await expect(page.locator(sel)).not.toBeVisible()` |
| `Element Should Contain  locator  text` | `await expect(page.locator(sel)).toContainText(text)` |
| `Element Text Should Be  locator  text` | `await expect(page.locator(sel)).toHaveText(text)` |
| `Input Value Should Be  locator  value` | `await expect(page.locator(sel)).toHaveValue(value)` |
| `Page Should Contain  text` | `await expect(page.getByText(text)).toBeVisible()` |
| `Page Should Contain Element  locator` | `await expect(page.locator(sel)).toBeAttached()` |
| `Location Should Be  url` | `await expect(page).toHaveURL(url)` |
| `Title Should Be  title` | `await expect(page).toHaveTitle(title)` |
| `Wait Until Element Is Visible  locator` | Playwright auto-waits — remove explicit waits |
| `Wait Until Page Contains  text` | `await page.getByText(text).waitFor()` |
| `Reload Page` | `await page.reload()` |
| `Close Browser` | handled by Playwright fixture teardown |
| `Suite Setup` | `test.beforeAll(...)` |
| `Suite Teardown` | `test.afterAll(...)` |
| `Test Setup` | `test.beforeEach(...)` |
| `Test Teardown` | `test.afterEach(...)` |
| `${VARIABLE}` | TypeScript `const` or `env.variableName` |
| `@{LIST}` | TypeScript `string[]` |
| `FOR  ${item}  IN  @{list}` | `for (const item of list)` |
| Keyword definition | TypeScript helper function or page object method |

#### Locator Strategy for Robot Locators
| Robot Locator | Playwright Equivalent |
|---|---|
| `id=submit` | `page.locator('#submit')` |
| `css=.class` | `page.locator('.class')` |
| `xpath=//button` | `page.locator('//button')` — add `// VERIFY: brittle` |
| `name=fieldname` | `page.getByLabel('fieldname')` or `page.locator('[name="fieldname"]')` |
| `link=Link Text` | `page.getByRole('link', { name: 'Link Text' })` |
| `partial link=Text` | `page.getByRole('link', { name: /Text/ })` |
| `tag=button` | `page.locator('button')` |
| `class=myClass` | `page.locator('.myClass')` |

Prefer: `getByTestId` → `getByRole` → `getByLabel` → `getByPlaceholder` → CSS → XPath.

#### Resource File Keywords → Page Object Methods
```typescript
// Robot: Keywords section with "Login As User"
//   Input Text  id=user    ${username}
//   Input Text  id=pass    ${password}
//   Click Button  id=submit
// becomes:
export class LoginPage {
  readonly usernameInput = this.page.locator('#user');
  readonly passwordInput = this.page.locator('#pass');
  readonly submitButton  = this.page.locator('#submit');
  constructor(readonly page: Page) {}
  async loginAs(username: string, password: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}
```

#### Test Case → Playwright Test
```typescript
// Robot:
// Test Case: Valid Login
//   [Tags]    smoke    positive
//   Login As User    standard_user    secret_sauce
//   Page Should Contain    Products
// becomes:
test('@smoke @positive Valid Login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.open(env.webBaseUrl);
  await loginPage.loginAs('standard_user', 'secret_sauce');
  await expect(page.getByText('Products')).toBeVisible();
});
```

#### Shared Config
```typescript
export const env = {
  webBaseUrl: process.env.WEB_BASE_URL ?? '${BASE_URL from robot variables}',
};
```

### Translation Order
1. Read ALL `.resource` files → identify all keywords and variables
2. Read ALL `.robot` files → inventory all test cases
3. Create `src/shared/config/env.ts` from `${VARIABLES}` section
4. For each resource file → create page object (keywords → methods)
5. For each test suite → create spec file (test cases → `test()` blocks)

---

## Run and Heal

```
npx playwright test --workers=1 --reporter=html,line
```

| Failure type | Action |
|---|---|
| TypeScript compile error | Fix import / type |
| Locator not found | Update using preference order above |
| Assertion mismatch | Verify vs source Robot test; update if source was wrong |
| Explicit wait removed | Confirm Playwright auto-waiting is sufficient; add `waitFor` if needed |

---

## Evidence Report — Complete MIGRATION-EVIDENCE.md

**Section 2:**
```markdown
## 2. Target Execution — Playwright
| Run date | Command | Report |
|---|---|---|
| <date> | `npx playwright test --workers=1 --reporter=html,line` | `playwright-report/index.html` |

| # | Suite | Test | Tags | Status | Screenshot |
|---|---|---|---|---|---|
> Total: X passed | Report: playwright-report/index.html
```

**Section 3:**
```markdown
## 3. Migration Mapping
| # | Source Test Case (Robot) | Suite | Playwright Test | Robot | Playwright | Migrated |
|---|---|---|---|---|---|---|
| 1 | <robot test case> | <suite.robot> | <playwright test name> | ✅ | ✅ | ✅ |
> Completeness: X/X (100%) | Reverse engineering: None | Analysis docs: None
```

---

## GATE 1 — Final Review

Show evidence summary, test results, and report locations. Ask:
> "All tests pass. Review `analysis/MIGRATION-EVIDENCE.md`. Type **'approved'** to finalize, or provide feedback."
