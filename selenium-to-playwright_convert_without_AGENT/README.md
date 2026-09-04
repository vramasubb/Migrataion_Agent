# Selenium to Playwright Mapper

An isolated, mapper-driven Selenium Java to Playwright TypeScript migration project. It does not modify any existing migration agent or generated Playwright project.

## Why this uses fewer tokens

Known Selenium statements are matched and rendered locally from JSON. An AI agent needs context only for unmatched constructs and their enclosing methods, rather than repeatedly reading and translating the whole framework.

## Structure

```text
selenium-to-playwright/
  .claude/skills/selenium-to-playwright/
  mappers/
    property_mapper.json
    action_mapper.json
    schema/
    clients/
  scripts/
    mapper_loader.py
    convert.py
    batch_convert.py
  input/
  output/
  tests/
```

## Commands

Requires Python 3.10 or newer and has no third-party runtime dependencies.

```powershell
cd selenium-to-playwright
python scripts/mapper_loader.py --validate
python scripts/convert.py input/LoginFlow.java --output output/LoginFlow.spec.ts --report output/LoginFlow.json
python scripts/batch_convert.py input --output-dir output
python scripts/project_convert.py "C:\path\to\selenium-project" --output output/sawslab-playwright-project --client example-saucedemo
python -m unittest discover -s tests -v
```

The project converter reads Cucumber feature files and `config.properties`, expands scenario outlines, generates web page objects plus web/API Playwright specs, and fails when it encounters an unsupported feature step. It does not invoke an AI agent.

## Token usage report

Every converter prints a token summary. When a report path is used, the same data is saved under `tokenUsage` in `migration-report.json`.

- `migrationConversion` is exact: local Python invokes no model, so billable input/output tokens and cost are zero.
- `textEquivalentWorkload` estimates source and generated text at four characters per token. This is useful for comparison but is not billable usage.
- `optionalAgentAssistance` is separate. Actual setup/help tokens cannot be inferred by the Python process; supply counts from the API/provider usage response.

Example using the conservative Sonnet rates shown in the supplied pricing reference, $3/M input and $15/M output:

```powershell
python scripts/project_convert.py "C:\path\to\selenium-project" `
  --output output/sawslab-playwright-project `
  --client example-saucedemo `
  --agent-input-tokens 12000 `
  --agent-output-tokens 4000 `
  --model claude-sonnet `
  --input-rate 3 `
  --output-rate 15
```

If agent counts are omitted, the report marks them `not-supplied` and does not pretend they are known. Change the rates to match the model and provider invoice used for that run.

Validate the generated project with:

```powershell
cd output/sawslab-playwright-project
npm install
npm run typecheck
npx playwright test
```

Use `--strict` to fail on unmatched non-structural lines. Without it, unmatched lines become visible `TODO source line` comments and are counted in the JSON report; they are never silently dropped.

## Scope

The deterministic converter translates statement-level mappings. Framework-level assembly, Cucumber scenario composition, complex collection logic, and target execution follow the skill workflow and must be verified against source behavior.

The requested `Automation_Tool_Migration_Checklist.xlsx` was not present in this workspace. [coverage-tracker.csv](coverage-tracker.csv) records current mappings using the glossary names cited by the migration prompt; reconcile it with the shared workbook before declaring organizational coverage complete.