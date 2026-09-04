# Prompt: Restructure a Tool-to-Tool Automation Converter onto the Shared PropertyMapper / ActionMapper Architecture

> **How to use this**: paste everything below into Claude Code (or hand it to
> whichever assistant/developer is building your converter). It describes
> the target architecture precisely enough to be followed without needing
> the original UFT→TOSCA codebase — but if you have access to that repo,
> attach it as a reference example.

---

## Context

Several teams are independently converting automation scripts from one tool
to another (e.g. UFT → TOSCA, Selenium → Playwright, TestComplete →
Katalon). Each conversion is currently its own one-off script with the
object-type and action mappings hardcoded inline. That doesn't scale: every
new client application introduces new element types and action patterns,
and there's no way to reuse work across teams or eventually merge these
into one application where a user picks **Source Tool → Target Tool** from
a dropdown and runs the conversion.

Your task: **restructure your existing converter (or build a new one) onto
a shared architecture** so every team's tool pair looks the same from the
outside, regardless of which two tools it connects.

Do not skip straight to code. If anything below is ambiguous for your
specific source/target tools, ask before proceeding — the goal is
consistency across teams, not a fast but divergent implementation.

---

## Core principle: separate the knowledge base from the pipeline

Your conversion logic (parsing the source script, walking its structure,
assembling the target file) should contain **zero hardcoded tool-specific
tables** — no dictionaries of `{"Button": "SomeTargetType"}`, no long
if/elif chains matching source syntax patterns. All of that is *data*, not
*code*, and lives in two JSON files:

### 1. `property_mapper.json` — "what is this element, and how do I identify it reliably?"

For every source-tool object/control type, define:
- The equivalent target-tool business type / control type.
- An **ordered fallback chain of identifying properties** (not a single
  property) — e.g. try `id` first, then `name`, then a structural locator.
  Real-world exports don't always have your first-choice identifier
  populated; a fallback chain is what makes generated scripts stable
  across environments, not just correct on the one script you tested.
- Group entries under an `engines` key by **technology**, not just by
  tool — a single source tool (like UFT, like Selenium) often spans
  multiple technologies (web vs. desktop vs. mobile vs. SAP-style
  fat-client), and those need different property vocabularies even
  though they're driven by the same script language.

```json
{
  "schemaVersion": "1.0",
  "engines": {
    "web": {
      "orLookup": { "defaultPropertyPriority": ["id", "name", "xpath"] },
      "objectTypes": {
        "<SourceControlType>": {
          "toscaBusinessType": "<TargetControlType>",
          "propertyPriority": ["id", "name", "xpath"],
          "defaultActionMode": "<target-specific>"
        }
      }
    }
  }
}
```

(Field names above match the UFT→TOSCA implementation exactly so tooling
can eventually treat every tool pair the same way. Keep `engines` and
`objectTypes` as literal keys; rename the business-type field to whatever
your target tool's schema calls it if `toscaBusinessType` doesn't fit —
just say so explicitly in your version so it's not silently inconsistent.)

### 2. `action_mapper.json` — "what does this line/call do, and what does it become?"

For every source-tool action (click, set text, select, wait, verify,
navigate, ...), define:
- A pattern that identifies it in the source script (regex for
  text-based scripts; a node-type check for AST/XML-based ones).
- The target action/module and a **value template**, not a hardcoded
  literal — you need to substitute captured values, resolve variables,
  convert units (e.g. seconds → ms), and so on. Define a small, explicit
  set of template tokens (see the UFT→TOSCA `action_mapper.json` for a
  working example: `{group1}`, `{resolveVar:group2}`, `{group1_x1000}`,
  etc.) rather than inventing ad hoc string formatting inline in code.
- A `skipPatterns` list for source lines that have no target equivalent
  (comments, control-flow keywords, tool-internal bookkeeping calls) —
  make this data too, not a hardcoded regex in your parser.

Same `engines` grouping as above — one array of actions per technology,
evaluated **in order, first match wins**, so more specific patterns must
be listed before more general ones.

### 3. `mapper_loader.py` — the only code allowed to read the JSON

Write one small loader module that:
- Loads `property_mapper.json` + `action_mapper.json`.
- Optionally overlays a **per-client** file (see below).
- Exposes a minimal API your conversion script calls — nothing else in
  your codebase should `json.load()` these files directly:
  - `business_type(engine, source_class) -> str`
  - `property_priority(engine, source_class) -> list[str]`
  - `resolve_or_value(engine, source_class, raw_props: dict) -> (value, matched_property)`
  - `match_action(engine, line_or_node, context) -> action_dict | None`
  - `should_skip(line_or_node) -> bool`
- Validates itself: a `--validate` CLI mode that checks every regex
  compiles, every action's referenced object type actually exists in
  `property_mapper.json`, and there are no duplicate action ids. Run this
  after every edit to the JSON, before converting anything real.

### 4. Per-client overrides — extend the knowledge base without forking it

Applications differ client to client — different frameworks, different
build pipelines that strip or keep certain attributes, occasional
client-specific controls. Handle this with **overlay files**, not
copy-pasted base files:

```
mappers/clients/<client_name>.json
{
  "propertyOverrides": { "<engine>": { "<SourceControlType>": { "propertyPriority": [...] } } },
  "actionOverrides":   { "<engine>": { "add": [ { "id": "...", "pattern": "...", ... } ] } }
}
```

The loader deep-merges this on top of the base files at load time. A
client file should only ever contain what's *different* — if a client
override starts duplicating most of the base file, that's a sign the
difference belongs in the base file behind a more specific pattern, not
in an overlay.

Your conversion script should accept `--client=<name>` (and/or a
`<TOOLPREFIX>_CLIENT` environment variable) to select an overlay at
run time.

---

## Required repo structure (match this exactly)

This is what lets tool pairs eventually plug into one shared application:

```
<source-tool>-to-<target-tool>/
  .claude/skills/<source-tool>-to-<target-tool>/     (if using Claude Code skills)
    SKILL.md
    references/
      mapping_guide.md          ← schema + extension workflow for your two mapper files
      <any other reference docs your target format needs>
    mappers/
      property_mapper.json
      action_mapper.json
      schema/
        property_mapper.schema.json
        action_mapper.schema.json
      clients/
        _template.json
  scripts/
    convert.py                  ← single-file conversion, mapper-driven only
    batch_convert.py            ← runs convert.py over a folder of input pairs
    mapper_loader.py
  input/
  output/
  README.md
```

Keep the folder and file **names** identical across tool pairs even though
their contents differ — `mappers/property_mapper.json`,
`mappers/action_mapper.json`, `scripts/mapper_loader.py`, `--client=` flag,
`--validate` mode. That naming consistency is what makes it possible to
later wrap every tool pair the same way (e.g. a thin dispatcher that picks
which pair's `convert.py` to call based on a Source/Target dropdown)
without bespoke glue per pair.

---

## Use the shared glossary — don't invent your own vocabulary

Before naming object types and action types in your `property_mapper.json`
/ `action_mapper.json`, check the shared workbook
(`Automation_Tool_Migration_Checklist.xlsx`, sheets `Standard_Element_Types`
and `Standard_Action_Types`). Use those canonical names as your
`Standard Element Type` / `Standard Action Type` reference points even
though your JSON keys will be your *source tool's* literal class/method
names — the point is that "Button", "Checkbox", "Table/Grid/DataGrid",
"Click", "Set/Type Text", etc. mean the same thing everywhere, so coverage
can be compared and eventually merged across tool pairs.

If your source or target tool needs an element or action type that isn't
in the glossary yet, add it to the glossary sheet first (so every team
inherits the new standard name), then reference it in your mapper JSON and
in your `Coverage_Tracker` rows.

**Before you finish**, fill in `Coverage_Tracker` in that workbook with one
row per object/action type you've mapped: your Source Tool, Target Tool,
Standard Type (from the glossary), your literal source class/method name,
your literal target type/action, and the exact path into your
`property_mapper.json` / `action_mapper.json` that implements it. Mark
`Status` as `Covered` only once you've validated it against a real script,
not just written the JSON.

---

## Definition of done

- [ ] `mappers/property_mapper.json` and `mappers/action_mapper.json` exist; your conversion script contains no hardcoded object-type or action tables
- [ ] `scripts/mapper_loader.py` implements the API above and a `--validate` CLI mode
- [ ] `mappers/schema/*.schema.json` exist and `--validate` passes with zero errors
- [ ] `mappers/clients/_template.json` exists; at least one real or example client override is included
- [ ] `scripts/convert.py` accepts `--client=<name>`
- [ ] Repo structure matches the layout above, with matching file/folder names
- [ ] `references/mapping_guide.md` documents your value-template tokens and extension workflow, written for someone who has never seen your source tool
- [ ] `Coverage_Tracker` in the shared workbook is updated for every type you mapped
- [ ] At least 2–3 real script fixtures converted successfully and spot-checked in the target tool

If any of these don't fit your specific tools cleanly, say so explicitly
and propose an alternative — the goal is a shared pattern everyone can
recognize, not a rigid template that breaks on the first tool that doesn't
match UFT/TOSCA's shape.
