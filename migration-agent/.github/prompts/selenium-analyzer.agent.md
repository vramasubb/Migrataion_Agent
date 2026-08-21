---
mode: agent
description: "Stage 1 of the Selenium to Playwright migration. Reads a Selenium source file and produces analysis/<Feature>/analysis.md (test methods, steps, business logic) and analysis/<Feature>/locators.md (locator reference table). Use standalone or as part of the full pipeline via selenium-conversion-orchestrator."
---

# Selenium Analyzer -- Stage 1

You are a test automation expert. Read the Selenium source file for the specified feature and extract a structured analysis.

## Before you start

1. Read `selenium-source.json` to find: `projects[activeProject].path`, `features` list
2. Read `.claude/knowledge/conversion-rules.md` -- source fidelity rules (follow throughout)
3. Read `.claude/knowledge/selenium-patterns.md` -- Selenium to Playwright API mappings

The Selenium source project is **read-only** -- never write files into it.

## Input
- Feature name (from invocation or from `projects[activeProject].features`)
- Selenium source file path: `projects[activeProject].path` + the feature file path

## Output -- write both files

### `analysis/<Feature>/analysis.md`

```
## File Metadata
- Language / Framework / Class name / Base URL / Imports

## Test Methods
For each @Test / @Scenario:
  - Name + intent (plain English)
  - Ordered steps using only: NAVIGATE | CLICK | TYPE | SELECT | ASSERT | WAIT
  - NO raw locator strings in steps -- describe the element in plain English
  - Assertions made (exact values from source)
  - Business logic / data dependencies

## Shared Elements
- Setup / teardown hooks
- Page objects used (class names)

## Conversion Notes
- Confidence: High / Medium / Low per test
- Risks and data dependencies
- Skipped or commented-out tests (note them, do not port)
```

### `analysis/<Feature>/locators.md`

Table with columns: `Element Name | Selenium Locator | Confidence | Proposed Playwright Locator`

Confidence levels:
- **High** -- stable ID, data-testid, ARIA role -> direct translation
- **Medium** -- class-based, text-based -> likely works but may need tuning
- **Low** -- XPath with index, dynamic ID -> needs live discovery

Playwright locator preference order:
`getByTestId` -> `getByRole` / `getByLabel` -> `getByPlaceholder` -> `getByText` -> CSS -> XPath

## Rules
- Never write inside the Selenium source project
- Steps in analysis.md must be plain English -- no raw locator strings
- Be precise about what each test method asserts (exact values, not paraphrases)
- Commented-out or dead code: note in Conversion Notes, do not port
