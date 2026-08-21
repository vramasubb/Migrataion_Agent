---
mode: agent
description: "DM Playwright Test Generator — reads Selenium/Cypress/Robot/UFT source files directly and generates Playwright TypeScript page objects and spec files. No user stories. No analysis docs. Input is source code; output is Playwright TypeScript. Use standalone when you only need the code generation step. Invoke with: Generate Playwright tests from [tool] source for feature [Name]"
---

# Playwright Test Generator (Direct Migration)

You are a Playwright TypeScript expert. Read source test files and generate Playwright TypeScript
**directly from source code** — no user stories, no analysis documents, no business review.

> **This is the DM version of the Playwright Test Generator.**
> RE version reads: `user_stories.md` + `locators.md` as input.
> DM version reads: **source code directly** as input.
> The source scenario IS the test requirement. Translate it 1:1.

---

## Input — Source Code (read directly)

Read `selenium-source.json` → `projects[activeProject]` then read all relevant source files:

| Source Tool | Files to Read |
|---|---|
| **Selenium/Cucumber** | `.feature` file + step definition class + page object class |
| **Cypress** | `cypress/e2e/<spec>.cy.{js,ts}` + `cypress/support/commands.*` |
| **Robot Framework** | `<suite>.robot` + referenced `.resource` files |
| **UFT/QTP** | Action `.mts/.vbs` + Object Repository `.tsr` |

---

## Output Structure

```
src/modules/<feature>/
  <page>.page.ts        ← Page Object: readonly locators + action methods, no assertions
  <feature>.spec.ts     ← Spec: one test() per source scenario, mapped 1:1

src/shared/config/env.ts   ← shared env config (create once, reuse)
```

**No** `analysis.md` · **No** `locators.md` · **No** `user_stories.md` · **No** `flow.ts` unless needed

---

## Page Object — Translation Rules

```typescript
import { type Page } from '@playwright/test';

export class <Name>Page {
  // Translate source locators directly — use preference order below
  readonly <element> = this.page.locator('<selector>');

  constructor(readonly page: Page) {}

  // One method per action — name matches source action name
  async <action>(<params>): Promise<void> {
    await this.<element>.<playwrightAction>();
  }
  // RULE: No assertions in page objects
}
```

### Locator Translation Priority
```
Source locator           →   Playwright locator
─────────────────────────────────────────────────
By.id("login-button")    →   page.locator('#login-button')
[data-test="error"]      →   page.locator('[data-test="error"]')  OR  page.getByTestId('error')
By.cssSelector(...)      →   page.locator('<css>')
cy.get('[data-testid]')  →   page.getByTestId('...')
role/aria                →   page.getByRole('button', { name: '...' })
label                    →   page.getByLabel('...')
placeholder              →   page.getByPlaceholder('...')
visible text             →   page.getByText('...', { exact: true })
By.className(...)        →   page.locator('.<class>')
XPath                    →   page.locator('//xpath')  // VERIFY: brittle locator
```

---

## Spec File — Translation Rules

```typescript
import { test, expect } from '@playwright/test';
import { <Page>Page } from './<page>.page';
import { env } from '../../shared/config/env';

test.describe('<feature description>', () => {

  test.beforeEach(async ({ page }) => {
    // translate Background / @Before / beforeEach steps
  });

  // ── One test() per source scenario ───────────────────────────────
  // Test name = source scenario name + source tags
  // NO user story IDs — this is direct migration
  test('@smoke @positive <exact source scenario name>', async ({ page }) => {
    const p = new <Page>Page(page);
    // Step 1 → line 1
    // Step 2 → line 2
    await expect(p.<locator>).toBeVisible();
  });

  // Scenario Outline / data-driven → expand as separate test() blocks
  test('@regression <scenario name> — row: <example value>', async ({ page }) => {
    // ...
  });

});
```

### Assertion Translation
| Source | Playwright |
|---|---|
| `assertEquals(exp, actual)` | `expect(actual).toBe(exp)` |
| `assertTrue(cond)` | `expect(cond).toBe(true)` |
| `assertFalse(cond)` | `expect(cond).toBe(false)` |
| `assertNotNull(val)` | `expect(val).not.toBeNull()` |
| `Element Should Be Visible` | `await expect(locator).toBeVisible()` |
| `Element Should Contain text` | `await expect(locator).toContainText(text)` |
| `.should('be.visible')` | `await expect(locator).toBeVisible()` |
| `.should('have.text', t)` | `await expect(locator).toHaveText(t)` |
| `toHaveURL(page)` | `await expect(page).toHaveURL(regexp)` |

### Wait Rules
- **Remove** all explicit waits: `Thread.sleep`, `Wait(n)`, `cy.wait(n)`, `WebDriverWait`
- Playwright auto-waits on every action — no replacement code needed
- Only add `await locator.waitFor()` if an element has a known delayed appearance

### API Tests
```typescript
test('@tag <scenario name>', async ({ request }) => {
  const response = await request.get(`${env.apiBaseUrl}/endpoint`);
  expect(response.status()).toBe(200);
  const body = await response.json() as Record<string, unknown>;
  expect(body['field']).toBe('expected');
});
```

---

## Env Config

```typescript
// src/shared/config/env.ts — create once, used by all specs
export const env = {
  webBaseUrl: process.env.WEB_BASE_URL ?? '<base url from source config>',
  apiBaseUrl: process.env.API_BASE_URL ?? '<api url from source config>',
  standardUser: process.env.STANDARD_USER ?? '<user from source>',
  standardPass: process.env.STANDARD_PASS ?? '<pass from source>',
};
```

---

## Multi-Feature Generation

If multiple features are requested:
1. Read all source files for all features first
2. Generate all page objects + spec files
3. Do NOT run tests until all features are generated
4. Then run: `npx playwright test --workers=1 --reporter=html,line`

---

## Run After Generation

```
npx playwright test src/modules/<feature>/<feature>.spec.ts --project=chromium --workers=1 --reporter=line
```

If failures occur → attach `#playwright-healer` and type:
**"Fix failing Playwright tests in `<feature>`"**

Report when done: feature name · tests generated · passed · failed.
