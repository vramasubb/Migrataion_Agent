# Mapping Guide

## Ownership

- `mappers/property_mapper.json` identifies Selenium control types and ordered locator fallbacks.
- `mappers/action_mapper.json` maps Selenium Java statements to Playwright TypeScript.
- `mappers/clients/<client>.json` contains only client-specific differences.
- `scripts/mapper_loader.py` is the only module permitted to load or merge mapper JSON.

Actions are evaluated in array order; first match wins. Put specific patterns before general patterns.

## Template tokens

| Token | Meaning |
|---|---|
| `{group1}` | Regex capture group 1; any positive group number is supported |
| `{group1_x1000}` | Numeric group multiplied by 1000, for seconds to milliseconds |
| `{first:group1:group2}` | First non-empty listed capture |
| `{locator:group1:group2}` | Convert locator strategy in group 1 and value in group 2 using `locatorStrategies` |

## Add an element type

1. Confirm its canonical name in the shared glossary. If no workbook is available, mark glossary validation as pending.
2. Add the Selenium type under `engines.<engine>.objectTypes` in `property_mapper.json`.
3. Supply `standardElementType`, `targetControlType`, ordered `propertyPriority`, and `defaultActionMode`.
4. Add or update focused tests and `coverage-tracker.csv`.
5. Run mapper validation and a real fixture conversion before marking it `Covered`.

## Add an action

1. Add a stable unique `id` under the correct engine.
2. Record `standardActionType`, an existing `objectType`, regex `pattern`, `targetAction`, and `valueTemplate`.
3. Keep Java syntax matching in JSON. Do not add regex or method names to `convert.py`.
4. Add a test proving first-match selection and rendered TypeScript.
5. Run `python scripts/mapper_loader.py --validate` and `python -m unittest discover -s tests -v`.

## Client overlays

Use `add` to prepend client-specific actions, `replace` to replace an action with the same ID, and `remove` for action IDs to omit. Property values are deep-merged by engine and object type. Select an overlay with `--client name` or `SELENIUM_PLAYWRIGHT_CLIENT=name`.

Never place credentials, URLs containing secrets, or duplicated base mappings in an overlay.