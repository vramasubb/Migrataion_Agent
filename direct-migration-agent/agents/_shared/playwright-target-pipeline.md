# Shared Skill: Common Playwright-Target Pipeline (read by every `*-direct-migration` agent)

> **Why this file exists:** `selenium-direct-migration`, `cypress-direct-migration`, `robot-direct-migration`,
> `uft-direct-migration`, and `uipath-direct-migration` each have a **different source** technology, but they
> all migrate to the **same target**: a standard Playwright TypeScript project. Everything below this line is
> identical across all five agents and MUST be followed the same way regardless of source. Only the
> **PRE-FLIGHT** (how to run the source suite) and **TRANSLATE/MAP** (source syntax → Playwright syntax) steps
> are source-specific and live in each agent's own file.

## Common Pipeline (applies to all 5 source technologies)

```
Source Framework (Selenium / Cypress / Robot / UFT / UiPath)
      ↓  PRE-FLIGHT   — run the ORIGINAL source suite/test case first, capture real evidence (screenshots/logs)
      |                  [source-specific — see that agent's own file]
      ↓  TRANSLATE/MAP — read ALL source files, generate Playwright TypeScript in one pass
      |                  [source-specific — see that agent's own file]
      ↓  RUN           — npx playwright test --workers=1 --reporter=html,line
      ↓  HEAL           — fix failures until green (use #playwright-healer for complex cases)
      ↓  EVIDENCE       — build MIGRATION-EVIDENCE.md + .html (see contract below) — never hand-write this
      ⏸  GATE 1         — STOP, show the evidence report, wait for "approved"
```

**One gate only.** If you find yourself writing `analysis.md`, `locators.md`, or `user_stories.md`, STOP —
those belong only to the Reverse Engineering pipeline, not Direct Migration.

## Common Output Project Shape

Every source technology assembles the same standard Playwright project shape:

```
<outputProject>/
  package.json / playwright.config.ts / tsconfig.json
  src/
    config/env.ts            ← base URL + credential env vars (never hardcode secrets)
    pages/ (or modules/**)   ← one page-object class per source page/component/reusable unit
  tests/ (or modules/**)     ← one spec per source test case, calling the page objects
  evidence/before/<slug>/    ← reference screenshots (from the real source run when possible)
  evidence/after/<slug>/     ← real screenshots captured by the generated Playwright spec
  MIGRATION-EVIDENCE.md      ← generated evidence report (+ .html view)
```

Page objects follow the standard Playwright **Page Object Model** pattern: every locator/selector used is
declared once as a named `private readonly ...: Locator` class field (assigned in the constructor), never
repeated as an inline literal at each call site. When building a page object from source, hoist locators the
same way — one field per unique selector, named from the selector text (readable camelCase + `Locator`
suffix), referenced as `this.<name>` everywhere it's used.

## Evidence Report Contract — every migration must produce all of this, for both technical and business reviewers

Build the report with `python uipath-to-playwright/scripts/build_evidence_report.py` (this script is source
agnostic — it only needs a JSON conversion report with ordered `action_ids` per file, before/after screenshot
folders, and pass/fail flags). Never hand-write `MIGRATION-EVIDENCE.md` — the script guarantees the report
always contains all four evidence layers below, consistently, across every source technology:

1. **Business Summary** (plain language, no code, for non-technical stakeholders) — auto-generated from
   coverage %, pass/fail, and compile status. Answers: what was migrated, did it actually run, why it matters.
2. **UiPath/Source Object → Playwright Conversion Details** — aggregated table of every distinct
   activity/keyword/command type seen, its standard category, and its Playwright translation template, with
   occurrence counts.
3. **Screenshot Comparison with per-step activity** — before/after screenshots paired by step, each row also
   naming the exact source activity/command that produced that step (technical, reviewable evidence).
4. **Full Before/After Traceability appendix** — one collapsible block per converted source file, listing
   **every single activity in execution order** (not aggregated) next to its Playwright method — the complete
   what-test-case / what-object / what-method mapping for a full technical audit.
5. **Source Project Inventory** (pass `--source-project <sourceRoot>`) — scans the real source project
   directory directly (independent of the migration output) and lists every test case / reusable component
   found, cross-checked against the migration output. Use this whenever someone questions "did you migrate
   ALL the test cases?" — it's self-verifying proof, not just an assertion.

```powershell
python uipath-to-playwright/scripts/build_evidence_report.py --test-name "<TestCase>" \
  --before-dir evidence/before/<slug> --after-dir evidence/after/<slug> \
  --output analysis/MIGRATION-EVIDENCE.md \
  --passed <true|false> --mapped-actions <N> --unmatched-actions <N> \
  --report <conversion-report.json path(s), repeatable --report flag> \
  --source-project "<sourceRoot>"
```

### If live execution can't complete for a reason unrelated to code quality

(e.g. the target needs VPN/Orchestrator/enterprise credentials not available in this environment, or the
original source tool itself — UiPath Studio/Robot, a licensed UFT install, etc. — isn't installed here either)
— do **not** report a bare FAILED with no context. Prove the code is correct up to the exact boundary instead:

```powershell
python uipath-to-playwright/scripts/build_evidence_report.py --test-name "<TestCase>" \
  --before-dir evidence/before/<slug> --after-dir evidence/after/<slug> \
  --output analysis/MIGRATION-EVIDENCE.md --passed false --compiled true \
  --blocked-reason "<exact reason, e.g. 'VPN/network access to <host> required'>" \
  --error-log <path to the real captured Playwright error output> \
  --mapped-actions <N> --unmatched-actions <N> --report <conversion-report.json>
```

`--compiled true` + `--blocked-reason` together produce a **green** "Code-complete — 100% mapped, TypeScript
compiles clean. Execution blocked only by <reason> (not a code defect)" banner instead of amber/FAILED. This
is the honest signal for "the migration is done and correct, but this sandbox can't reach the real target."
`--error-log` must always be a **real captured error** (never fabricated) — it is the strongest evidence
because it shows the generated code reached the exact right point before stopping.

## Non-negotiable rules (all 5 agents)

- Never invent business data, credentials, or "realistic-looking" fake values. If real source data (Excel
  sheets, config files, fixtures) doesn't exist or doesn't match, generate clearly-labeled `SAMPLE_*`
  placeholders instead — visible to every reviewer, never silently guessed.
- No analysis docs, no user stories, no first gate — the source code IS the specification.
- Attach the generated `.html` evidence file; do not just describe results in chat.
