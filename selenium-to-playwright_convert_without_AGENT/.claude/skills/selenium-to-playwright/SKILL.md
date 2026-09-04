---
name: selenium-to-playwright
description: Mapper-first migration of Selenium Java frameworks to Playwright TypeScript with client overrides, validation, tests, and minimal context usage.
---

# Selenium Java to Playwright TypeScript

Use this skill only for Selenium-to-Playwright migration. The Selenium source is read-only and the target must be a separate output directory.

## Non-negotiable rules

1. Run `python scripts/mapper_loader.py --validate` before conversion and after every mapper edit.
2. Read mappings from `mappers/property_mapper.json` and `mappers/action_mapper.json` only through `MapperLoader`. Never add mapping dictionaries, Selenium-method switch statements, or migration regexes to converter code.
3. Put client differences in `mappers/clients/<client>.json`; do not fork base mappings.
4. Preserve every test scenario, assertion, data row, tag, hook, retry, timeout intent, API call, and configuration key. Never invent behavior missing from source.
5. Prefer Playwright user-facing locators: test id, role, label, placeholder, stable id/name, text, CSS, then XPath. Use the ordered property mapper for fallback.
6. Use Playwright auto-waiting and web-first assertions. Do not migrate `Thread.sleep`, implicit waits, or Selenium driver lifecycle code literally.
7. Generated TypeScript must contain no Selenium imports or APIs and no secrets copied into source.

## Low-token workflow

### 1. Preflight

- Resolve source and target paths once.
- Inventory paths with file-name searches; do not paste entire files into context.
- Read configuration, test runner, hooks, feature files, referenced step definitions, and referenced page objects only.
- Run the Selenium suite if its toolchain is available; record command and result. Never modify source.

### 2. Validate and map

```powershell
python scripts/mapper_loader.py --validate
python scripts/batch_convert.py <source-java-folder> --output-dir output --client <client>
```

- Omit `--client` when no overlay applies.
- Use the compact `output/migration-report.json` to identify unmatched lines.
- Do not re-read mapped source. Read only unmatched lines with the enclosing method and direct dependencies.
- Add a reusable mapping to JSON when the behavior is general. Add it to a client overlay only when application-specific.

### 3. Assemble the Playwright project

- `playwright.config.ts`: base URL, projects, retries, trace, screenshot, video, and reporter settings matching source intent.
- `src/shared/config`: environment parsing with secrets supplied by environment variables.
- `src/pages` or `src/modules/<feature>`: typed page/component objects with `Page` and `Locator`.
- `tests`: Playwright Test specs preserving source scenario names, tags, setup, data, and assertions.
- Cucumber may be retained only when explicitly required; otherwise convert scenarios to Playwright Test.

Required API conversions include navigation, click, fill/type, clear, select, checkbox/radio, keyboard, hover, drag/drop, frames, windows/popups, dialogs, upload/download, cookies/storage, JavaScript execution, tables/lists, screenshots, waits, and assertions. If a mapping is absent, report it and extend the mapper; do not silently omit it.

### 4. Verify incrementally

Run in this order:

```powershell
npx tsc --noEmit
npx playwright test <one-generated-spec> --project=chromium --workers=1
npx playwright test --workers=1
```

Classify failures as compile, configuration, locator, timing, assertion, data, environment, or application. Fix the root mapping or generated code, rerun the narrow test, then rerun the suite. Never weaken an assertion merely to make a test pass.

### 5. Evidence and completion

Create a migration report containing source/target counts, mapping IDs used, unmatched constructs, test results, intentional deviations, and report paths. Completion requires:

- mapper validation passes;
- source scenarios and target tests have traceable one-to-one coverage;
- zero unexplained unmatched constructs;
- TypeScript compile passes;
- target tests pass, or environment/application blockers are evidenced;
- `coverage-tracker.csv` reflects validated mappings.

Read [references/mapping_guide.md](references/mapping_guide.md) before changing mapper data.