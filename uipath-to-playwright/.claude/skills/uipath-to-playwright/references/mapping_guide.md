# Mapping Guide

## Ownership

- `mappers/property_mapper.json` identifies UiPath UI Automation control types and ordered locator fallbacks (parsed from the UiPath `Selector`/`FullSelectorArgument` string).
- `mappers/action_mapper.json` maps XAML activity **tags** to Playwright TypeScript statements.
- `mappers/clients/<client>.json` contains only client-specific differences.
- `scripts/mapper_loader.py` is the only module permitted to load, merge, or parse mapper JSON and UiPath selector strings.
- `scripts/convert.py` (`ProjectWalker`) is the only module permitted to walk the XAML tree; it dispatches to the JSON-driven action registry for leaf activities and to a small fixed set of structural handlers (`Sequence`, `NApplicationCard`, `MultipleAssign`/`Assign`, `ForEachRow`, `NCheckState`, `CommentOut` exclusion) for control flow.

Actions are matched by **XML tag name**, not regex or line position — UiPath source is well-formed XML, so `MapperLoader` reads attributes straight from the parsed element regardless of attribute order or line wrapping. When two actions share a tag (e.g. `CheckBox` true/false), add a `match` condition; entries are tried in list order and the first satisfied `match` wins.

## Selector modes

| `selector.mode` | Where the selector comes from |
|---|---|
| `attribute` | A flat attribute on the activity itself, e.g. classic `ui:Click Selector="..."` |
| `target` | A nested `<Tag.Target><TargetAnchorable FullSelectorArgument="..." ScopeSelectorArgument="...">`, used by modern `UiPath.UIAutomationNext` activities (`uix:NClick`, `uix:NTypeInto`, `uix:NGetText`, `uix:NCheckState`) |

Both modes resolve through the same `property_mapper.json` priority list and `locatorStrategies`, so adding a new selector attribute alias (e.g. a client's custom `automationid`) only touches `property_mapper.json`, never the action entries.

## Template tokens

| Token | Meaning |
|---|---|
| `{selector}` | The Playwright locator fragment already resolved for this action (from `selector.mode`) |
| `{attr:Name}` / `{attr:Name1,Name2}` | First present attribute, converted with `_vb_value`: `[varName]` becomes the bare variable reference; a literal becomes a quoted, escaped TypeScript string |
| `{bareAttr:Name}` | Strip the `[...]` wrapper from a UiPath output-variable binding (e.g. `Result="[isVisible]"` → `isVisible`) with no quoting |
| `{rawAttr:Name}` | Bracket-stripped attribute with **no** quoting/escaping — for embedding raw text into a regex literal (`/{rawAttr:Pattern}/`) |
| `{exprVar:Name}` | Extracts the bare variable name from a `[varName] = True/False` style expression attribute |
| `{scrollDelta:Name}` | Converts a UiPath `Direction` attribute (`Up`/`Down`) into a signed pixel delta for `page.mouse.wheel` |

## Add a leaf activity (JSON only)

1. Confirm its canonical name in the shared glossary. If no workbook is available, mark glossary validation as pending.
2. Add an entry to `engines.web.actions` in `action_mapper.json`: `id`, `standardActionType`, an existing `objectType` (add one to `property_mapper.json` first if needed), `tag` (the XAML local element name, no namespace prefix), optional `selector`, optional `match`, and `valueTemplate`.
3. Keep UiPath tag/attribute names in JSON. Do not add tag checks or attribute lookups to `convert.py`.
4. Add a test proving it converts correctly (extend a fixture in `input/` or add a focused unit test) and run `python scripts/mapper_loader.py --validate` + `python -m unittest discover -s tests -v`.
5. Update `coverage-tracker.csv`.

## Add a structural/control-flow construct (code, deliberately)

Only add a new Python handler in `ProjectWalker` when the construct expresses **nesting or branching**, not a single automation statement — e.g. a new loop or conditional activity type. Register the tag check in `ProjectWalker.walk()`'s dispatch chain, and prefer reusing existing helpers (`_find_child_by_suffix`, `_find_descendant_by_local_name`, `_emit_assignment`) over writing new ones.

## excludeSubtree and noOpTags

- `excludeSubtree`: element local names (property-element syntax like `NApplicationCard.OCREngine`, or Studio metadata like `WorkflowViewStateService.ViewState`) whose entire subtree is skipped — no output, no unmatched warning. Use this for pure designer/config metadata and `CommentOut` (Studio's "disabled" state).
- `noOpTags`: activities that need no Playwright equivalent at all (e.g. `NSetRuntimeBrowser`) — skipped silently, not reported as unmatched.

Never add real automation activities to either list — anything with test-relevant behavior must render an action or an explicit `// TODO`, never disappear silently.

## Client overlays

Use `add` to prepend client-specific actions, `replace` to replace an action with the same ID, and `remove` for action IDs to omit. Property values are deep-merged by engine and object type. Select an overlay with `--client name` or `UIPATH_PLAYWRIGHT_CLIENT=name`.

Never place credentials, Orchestrator asset values, URLs containing secrets, or duplicated base mappings in an overlay.
