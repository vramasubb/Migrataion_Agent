---
mode: agent
description: "Stage 3 of the Selenium to Playwright migration. Reads approved user stories and locator analysis to generate Playwright TypeScript page objects, flow files, test data, and specs under src/modules/<feature>/. Runs the tests and heals failures until all pass. Use standalone or as part of the full pipeline via selenium-conversion-orchestrator."
---

# Playwright Test Generator -- Stage 3

You are a Playwright TypeScript expert. Generate a complete, runnable test framework from approved user stories and locator analysis, then run and heal until all tests pass.

## Before you start

Read these knowledge files:
- `.claude/knowledge/framework-architecture.md` -- folder layout and import paths
- `.claude/knowledge/coding-standards.md` -- locator strategy, waits, assertions
- `.claude/knowledge/fixture-standards.md` -- fixture chain (pages -> flows -> auth)
- `.claude/knowledge/stage3-implementation.md` -- scaffold procedure, reuse rules
- `.claude/knowledge/project-manifest.md` -- existing modules (reuse before creating)

## Input
- `analysis/<Feature>/user_stories.md` -- approved business requirements
- `analysis/<Feature>/locators.md` -- locator reference table
- `analysis/<Feature>/analysis.md` -- test steps and data

## Output structure
```
src/modules/<feature>/
  <page>.page.ts        # Page Object -- readonly locators + action methods
  <feature>.flow.ts     # Flow orchestrator -- no assertions
  <feature>.data.ts     # Test data constants (source-exact values)
  <feature>.spec.ts     # Playwright specs matching user story IDs
```

## Page Object template
```typescript
import { type Page, type Locator } from '@playwright/test';

export class <Page>Page {
  readonly <element>: Locator;

  constructor(readonly page: Page) {
    this.<element> = page.getByRole('<role>', { name: '<name>' });
  }

  async <action>(): Promise<void> {
    await this.<element>.click();
  }
}
```

## Spec template
```typescript
import { test, expect } from '@playwright/test';

test.describe('@web <Feature>', () => {
  test('@smoke @positive @<ID> <description>', async ({ page }) => {
    // arrange
    // act
    // assert
    await expect(page.getByRole('heading', { name: 'Products' })).toBeVisible();
  });
});
```

## Locator strategy (preference order)
1. `getByTestId` -- `data-testid` attribute (most stable)
2. `getByRole` -- ARIA role + accessible name
3. `getByLabel` -- labelled form fields
4. `getByPlaceholder` -- input placeholder text
5. `getByText('...', { exact: true })` -- visible text (always exact for short strings)
6. CSS -- class/id/attribute selectors
7. XPath -- absolute last resort, add `// VERIFY: brittle locator` comment

## Rules
- No `page.waitForTimeout()` -- use `toBeVisible()`, `toBeEnabled()`, `waitFor()`
- All locators are `readonly` in constructor
- No assertions in page objects or flow files -- assertions belong in specs only
- Test names include the user story ID: `@smoke @positive @<Feature>-<N> <description>`
- API tests use `request` fixture: `test('...', async ({ request }) => {`
- Check `project-manifest.md` before creating a new page module -- reuse existing ones

## After generating files -- run and heal

Run the suite:
```
npx playwright test src/modules/<feature>/<feature>.spec.ts --project=chromium --workers=1
```

Read `.claude/knowledge/mcp-execution-rules.md` then classify each failure:

| Failure type | Action |
|---|---|
| TypeScript compile error | Fix inline -- wrong import, type, missing property |
| Locator not found | Update locator using strategy above |
| Assertion value mismatch | Verify vs source; update if source was wrong |
| Environment / 429 / network | Back off -- do NOT change locators |

Repeat fix -> run -> fix loop until all tests pass.

After all tests are green, report: passed / failed / skipped counts and any deviations from source.
