---
applyTo: '**'
---
# Direct Migration Agent
# Source Framework -> Playwright TypeScript
# No user stories. No analysis docs. One final gate.

---

## How This Project Works

**Direct Migration** translates your source test framework directly into Playwright TypeScript
in a single pass. No intermediate documents. No business review gate before code is written.

```
Source Framework
   [SKIP: analysis docs]  [SKIP: user stories]  [SKIP: Gate 1]
          |
          v  (translate directly)
   Playwright TypeScript
          |
          v
   Run + Heal -> all tests green
          |
   GATE 1: Final Review (one gate only)
```

---

## Available Agents — Use with # in Copilot Chat

### Orchestrators — Run the Full Pipeline End-to-End

| # | Agent | Invoke With |
|---|---|---|
| 1 | `#selenium-direct-migration` | "Migrate the Selenium framework directly" |
| 2 | `#cypress-direct-migration` | "Migrate the Cypress project directly" |
| 3 | `#robot-direct-migration` | "Migrate the Robot Framework project directly" |
| 4 | `#uft-direct-migration` | "Migrate the UFT project directly" |
| 5 | `#uipath-direct-migration` | "Migrate the UiPath project directly" |

> Each orchestrator runs: PRE-FLIGHT -> TRANSLATE -> RUN -> HEAL -> EVIDENCE -> GATE 1

---

### Supporting Agents — Use for Individual Steps

| # | Agent | When to Use | Invoke With |
|---|---|---|---|
| 5 | `#migration-planner` | Before migrating — scan source, choose DM vs RE, estimate effort | "Plan the migration for my project" |
| 6 | `#source-analyzer` | Inventory what's in the source (no files created) | "Analyze the source project for direct migration" |
| 7 | `#playwright-test-generator` | Generate Playwright code from source (no user stories needed) | "Generate Playwright tests from Selenium source for feature Login" |
| 8 | `#playwright-healer` | Fix failing Playwright tests after generation | "Fix failing Playwright tests in WebLoginAndCart" |
| 9 | `#playwright-direct-generator` | Alternative generator (same as #7, different entry point) | "Generate Playwright tests from [tool] source directly" |

## Typical End-to-End Workflow

```
STEP 1 — Plan (optional but recommended for new projects)
   Attach: #migration-planner
   Type:   "Plan the migration for my project"
   Output: MIGRATION-PLAN.md with effort estimate + risk list

STEP 2 — Analyze (optional, for quick source inventory)
   Attach: #source-analyzer
   Type:   "Analyze the source project for direct migration"
   Output: Chat summary — test count, locator types, risks (no files written)

STEP 3 — Migrate (pick your tool)
   Attach: #selenium-direct-migration  (or cypress / robot / uft / uipath variant)
   Type:   "Migrate the Selenium framework directly"  (or "Migrate the UiPath project directly")
   Output: src/modules/<feature>/ + analysis/MIGRATION-EVIDENCE.md (+ .html view)

STEP 4 — Fix failures (if any tests fail)
   Attach: #playwright-healer
   Type:   "Fix failing Playwright tests in <feature>"
   Output: Fixed spec/page files + re-run confirmation
```

---

## Key Config Files

| File | Purpose |
|---|---|
| `selenium-source.json` | Set source path + features here first (Selenium/Cypress/Robot/UFT) |
| `uipath-source.json` | Set source path here first for UiPath Studio (XAML) projects |
| `migration-source.json` | Migration strategy = "direct", output folder |
| `agents/` | All agent files (visible in Explorer) |
| `agents/_shared/playwright-target-pipeline.md` | **Shared skill/instructions** — the common RUN → HEAL → EVIDENCE → GATE 1 pipeline, output project shape, and evidence-report contract used identically by all 5 `*-direct-migration` agents (only PRE-FLIGHT/TRANSLATE differ per source) |
| `.github/prompts/` | Same agent files (Copilot Chat discovery location — must stay in sync with `agents/`) |

---

## Output Projects

| Source | Output project |
|---|---|
| Selenium (`selenium-source.json`) | `../sawslab-playwright-dm/` |
| UiPath (`uipath-source.json`) | `../uipath-playwright-dm/` |

Run either independently:
```
cd ../sawslab-playwright-dm   (or ../uipath-playwright-dm)
npm install
npx playwright install chromium
npm test
```
