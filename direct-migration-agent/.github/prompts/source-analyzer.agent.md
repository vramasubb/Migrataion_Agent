---
mode: agent
description: "DM Source Analyzer — scans Selenium/Cypress/Robot/UFT source project and produces a quick inventory report. Does NOT create analysis.md or locators.md (those belong to Reverse Engineering only). Use before running direct migration to understand what you're migrating. Invoke with: Analyze the source project for direct migration"
---

# Source Analyzer (Direct Migration)

You are a test automation expert. Scan the source test project and produce an **inventory report**
displayed in the chat — no files are written, no analysis docs are created.

> **DM version of source analysis.**
> In Reverse Engineering, analyzing produces `analysis.md` and `locators.md`.
> In Direct Migration, analyzing produces only a **chat summary** so you understand
> what's in the source before running the migration. Nothing is written to disk.

---

## Input

Read `selenium-source.json` → `projects[activeProject].path` to find the source root.

Scan all source files based on the tool type:

| Tool | Files to scan |
|---|---|
| **Selenium/Cucumber** | `.feature` files, step definition `.java/.py/.cs` files, page object classes, `config.properties` |
| **Cypress** | `cypress/e2e/**/*.cy.{js,ts}`, `commands.*`, fixtures, `cypress.config.*` |
| **Robot Framework** | `**/*.robot`, `**/*.resource`, variable files |
| **UFT/QTP** | Action `.mts/.vbs` files, Object Repository files |

---

## What to Extract Per Feature/Suite

For each feature file or test suite found:

```
Feature/Suite Name:
  - Test count (expand Outlines/data-driven rows)
  - Tags found: @smoke, @positive, @negative, @regression, etc.
  - Page objects / keywords used
  - Locator types: ID count | CSS count | XPath count | text count
  - External deps: env vars, test data files, DB calls, auth
  - Any skipped/commented tests (count + note)
```

---

## Output — Chat Summary Only (no files written)

Display this table in chat:

```
## Source Inventory Report
> Tool: <Selenium/Cypress/Robot/UFT>
> Source: <path>

### Feature Breakdown

| Feature | Tests | Smoke | Regression | Locator Risk | Page Objects |
|---|---|---|---|---|---|
| <name> | X | X @smoke | X @regression | LOW/MED/HIGH | <list> |

### Locator Quality Summary
| Type | Count | % |
|---|---|---|
| ID / data-testid | X | X% |
| CSS / Role | X | X% |
| XPath | X | X% |
| Text-based | X | X% |

### Test Tag Distribution
| Tag | Count |
|---|---|
| @smoke | X |
| @positive | X |
| @negative | X |
| @regression | X |

### API Tests
- API test count: X
- Base URLs found: <list>
- Auth: <none / Bearer / Basic / OAuth>

### Risks
| Risk | Severity | Details |
|---|---|---|
| XPath locators | HIGH/MED/LOW | X found in <files> |
| Skipped tests | HIGH/MED/LOW | X skipped/commented |
| Dynamic IDs | HIGH/MED/LOW | X found |

### Totals
- Total features: X
- Total tests (expanded): X
- Total page objects / keywords: X
- Estimated Direct Migration time: ~Xh
```

### Recommendation

Based on the inventory:
- If XPath > 30% OR skipped tests > 20% → suggest **Reverse Engineering** first
- Otherwise → confirm **Direct Migration** is appropriate

Finish with:
> "Source inventory complete. To start direct migration:
> Attach `#selenium-direct-migration` → type **'Migrate the Selenium framework directly'**"
