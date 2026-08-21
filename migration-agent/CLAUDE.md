# Reverse Engineering Migration Agent
# Selenium Framework → User Stories → Playwright TypeScript

## Purpose

This is the **Reverse Engineering Migration** path. It first deconstructs the Selenium source into
human-readable analysis documents and business user stories, gets stakeholder sign-off at Gate 1,
then builds the Playwright TypeScript framework from those approved artefacts.

**Compare with the Direct Migration (`direct-migration-agent/`):**

| | Reverse Engineering (this project) | Direct Migration (`direct-migration-agent/`) |
|---|---|---|
| Analysis docs | ✅ `analysis.md + locators.md` | ❌ None |
| User stories | ✅ `user_stories.md` | ❌ None |
| Business review gate | ✅ 2 gates (business + final) | ❌ 1 gate (final only) |
| Documentation | Full business trail | Code only |
| Use when | Stakeholder sign-off required | Technical team, speed priority |

## Recommended Start — Read This First

Before converting any file, read `.claude/knowledge/project-setup.md` for the full checklist.

**Short version:**
1. Point `selenium-source.json` at your EXTERNAL Selenium framework (it stays in its own project — nothing is copied in)
2. Fill in `.env` with your app URL and credentials
3. Run inventory once, then convert the **ENTIRE framework** through two review gates (see below):
   analyze all → generate all user stories → **Gate 1** (business review of all stories) → implement all
   Playwright → **Gate 2** (review specs + results)
4. Approve at each of the two whole-framework gates

The Selenium framework is a **separate project outside this workspace**. Agents scan it in place
(path from `selenium-source.json`, or named in your request) and write all generated artifacts here.

---

## Pipeline

```
<selenium-source>/     →    analysis/<Feature>/     →    analysis/<Feature>/   →    src/
(EXTERNAL Selenium       analysis.md + locators.md      user_stories.md            (Playwright TS)
                            + test-data.md
 framework, read-only)        Stage 1                       Stage 2                   Stage 3
                           Analyze & Extract             Generate Stories          Implement Framework
```

`<selenium-source>` resolves from `selenium-source.json`. Everything to the right of it is generated
inside THIS workspace.

---

## Recommended Workflow — WHOLE FRAMEWORK (with two review gates)

**Convert the ENTIRE framework as one pass, with two human review gates** — analyze every feature,
generate ALL user stories together, get them approved in a single business-review gate, then implement
the Playwright conversion for the whole framework and review it at a second gate.

```
Inventory (once)  — selenium-inventory scans the whole source
      ↓
Analyze ALL features  (Stage 1, every Selenium test class)   → analysis/<Feature>/analysis.md + locators.md
      ↓
Generate ALL user stories  (Stage 2, every feature)          → analysis/<Feature>/user_stories.md
      ↓
┌───────────────────────────────────────────────────────────┐
│  GATE 1 — business review of ALL user stories at once       │  ← stop; await approval
└───────────────────────────────────────────────────────────┘
      ↓  (approved)
Implement Playwright for the WHOLE framework  (Stage 3) + run the full suite
      ↓
┌───────────────────────────────────────────────────────────┐
│  GATE 2 — review the full Playwright output + test results  │  ← stop; await approval
└───────────────────────────────────────────────────────────┘
      ↓
Post-migration review (migration-reviewer)
→ analysis/MIGRATION-REVIEW.html: framework-wide coverage % + reuse % + gaps
  + Screenshot comparison (Selenium vs Playwright, side-by-side visual evidence)
  → analysis/SCREENSHOT-COMPARISON.html
```

At **each** of the two gates, stop and wait for the user. Do NOT auto-advance from Gate 1 into the
Playwright conversion, and do NOT auto-finish past Gate 2 into the migration review. Stage 1 (analyze) and
Stage 2 (stories) run across **all** features before Gate 1; Stage 3 runs across **all** features before
Gate 2 — the gating is at the framework level, not per feature.

## How to Use

### Before conversion (do this once)
> "Run inventory on the Selenium framework"

### Step 1 — analyze the whole framework + generate ALL user stories, then STOP at Gate 1
> "Generate user stories for the entire framework"

Runs Stage 1 (analyze every feature) and Stage 2 (all `user_stories.md`) across the whole source, then
stops for a single business review of all stories together.

### Step 2 — after Gate 1 approval: implement Playwright for the WHOLE framework + run, then STOP at Gate 2
> "Implement Playwright for the entire framework"

Runs Stage 3 across all features and executes the full suite, then stops for review of the specs + results.

### Fix a failing test
> "Fix the failing tests in `src/modules/<module>/`"

### Post-migration review (after Gate 2)
> "Run the post-migration review for the whole framework"

Produces `analysis/MIGRATION-REVIEW.html`: framework-wide coverage %, reuse %, migrated vs missing vs
partial vs intentionally-excluded, and a gap analysis.

---

## Directory Structure

The Selenium source is EXTERNAL (a sibling project inside this workspace); everything below lives in THIS workspace:

```
selenium-source.json          ← Points at the external Selenium framework (seleniumSourceRoot + projects)

selenium-cucumber-web-api-framework/   ← EXTERNAL, read-only Selenium framework
  (.java / .feature)                    Maven / Cucumber-JVM + JUnit 4

analysis/                     ← All generated artifacts, organized PER FEATURE
  INVENTORY.md                ← Produced by selenium-inventory (run once before converting; cross-feature)
  WebLoginAndCart/            ← One folder per feature (PascalCase feature/class name)
    analysis.md               ← Metadata, test methods (+ per-method Business Logic), shared elements, notes
    user_stories.md           ← Stakeholder stories: AC + Validation Points + Business Logic (no locators, no data values)
    locators.md               ← Locator Reference table (Stage 3 use only)
    test-data.md              ← Test Data Reference — extracted source-exact values (Stage 3 use only; single source of truth for data)
  ApiPosts/
    analysis.md
    user_stories.md
    locators.md               ← API endpoint catalogue (analogous to UI locators)
    test-data.md

src/                          ← Playwright framework output
  modules/                    ← All modules live here (scalable root)
    <page>/                   ← One folder PER APPLICATION PAGE (login, inventory, cart, ...)
      <page>.page.ts          ← Page Object: locators + raw actions only
    <journey>/                ← One folder per business journey (from the Selenium test class)
      <journey>.flow.ts       ← Flow: orchestrates page actions into business steps
      <journey>.data.ts       ← Test data and expected messages
      <journey>.spec.ts       ← Specs: test cases, imports from flow/data
  shared/
    fixtures/
      pages.fixture.ts        ← Instantiates all page objects
      flows.fixture.ts        ← Instantiates all flows
      auth.fixture.ts         ← loggedIn fixture (opt-in, programmatic login)
      api.fixture.ts          ← apiRequest fixture for API-only tests (no browser)
    config/
      env.ts                  ← Single source for all env vars (BASE_URL, USERNAME, etc.)
    util/
      relative-date.ts        ← Date helper (dateFromToday)

playwright.config.ts
.env                          ← Local secrets — gitignored, never committed
.env.example                  ← Template for .env
```

---

## Agents

| Agent | Trigger | Purpose |
|-------|---------|---------|
| `selenium-inventory` | **Run first** — before any conversion | Scans all files, plans module structure, recommends order |
| `selenium-conversion-orchestrator` | "Generate user stories for the entire framework" (Gate 1) · "Implement Playwright for the entire framework" (Gate 2) | Orchestration playbook run by the MAIN AGENT with the two gates |
| `selenium-analyzer` | Called by orchestrator | Stage 1: parse Selenium, extract analysis + Locator Reference table |
| `user-story-generator` | Called by orchestrator | Stage 2: analysis → formatted user stories |
| `playwright-test-generator` | Called by orchestrator | Stage 3: live locator discovery when app is accessible |
| `playwright-test-healer` | "Fix failing tests in `src/<module>/`" | Repair broken locators and timing issues |
| `playwright-test-planner` | "Plan tests for `<url>`" | Explore live app and produce a test plan |
| `selenium-migration-reviewer` | "Run the post-migration review for the whole framework" (after Gate 2) | Compares source vs migrated output; framework-wide coverage % + reuse % + missing/partial/excluded + gap analysis + **screenshot comparison** (side-by-side Selenium vs Playwright) → `analysis/MIGRATION-REVIEW.html` + `analysis/SCREENSHOT-COMPARISON.html` |

---

## Knowledge Files

| File | Purpose |
|------|---------|
| `project-setup.md` | Step-by-step pre-conversion checklist |
| `conversion-rules.md` | How Selenium patterns map to user stories and Playwright layers |
| `selenium-patterns.md` | Selenium → Playwright API translation table |
| `user-story-standards.md` | User story format, naming, and quality standards |
| `framework-architecture.md` | Playwright folder structure and layer responsibilities |
| `coding-standards.md` | Locator priority, wait strategy, assertion rules, SPA pitfalls |
| `fixture-standards.md` | Fixture chain pattern (pages → flows → auth → api) |
| `stage3-implementation.md` | Detailed Stage 3 procedure (scaffold, reuse/dup-handling, locator waterfall, layer build, execution) |
| `mcp-execution-rules.md` | How to run/debug/heal tests via MCP |
| `screenshot-comparison.md` | Selenium-vs-Playwright screenshot comparison (side-by-side visual evidence) for the migration report |
| `review-checklist.md` | Pre-commit self-review checklist |
| `project-manifest.md` | Living index of all converted modules and files |

---

## Source Framework

- **Type**: Java 11 / Maven / Cucumber-JVM 7 / JUnit 4 / REST Assured 5
- **Web target**: https://www.saucedemo.com (SauceDemo — public QA practice site)
- **API target**: https://jsonplaceholder.typicode.com (free fake REST API, no auth)
- **Auth model**: SauceDemo — fully automated (username/password, no OTP)
- **Credentials**: `standard_user` / `secret_sauce` (well-known public test credentials)
- **Features**: `WebLoginAndCart` (web UI), `ApiPosts` (REST API)

## Rules (always in force)

- **STRICT SOURCE FIDELITY (governing rule):** convert EXACTLY what the Selenium source does — no adding
  functionality, no reducing/skipping active behaviour. Mirror the source's steps, order, values,
  assertions (including print-only/none), and quirks.
- **Workflow:** convert the **WHOLE framework** in one pass with **two gates** — analyze all + generate ALL
  user stories → **Gate 1** (business review of all stories) → implement ALL Playwright + run → **Gate 2**
  (review specs + results) → post-migration review.
- **Current state:** Migration complete. 17/17 tests passing (7 web + 10 API). Both features implemented.
- **Never** read environment variables via `process.env` outside `src/shared/config/env.ts`.
- **Never** put locators or waits inside `.spec.ts` files — those belong in page objects.
- **Never** call `new Page()` inside a spec — use fixtures.
- **Never** use `waitForTimeout` (hard sleeps) — use Playwright auto-wait or `expect`.
- **Never** copy locators or XPath strings into user story files.
- **Never** put test-data **values** in `analysis.md` or user story files.
- User stories must **not** mention selectors, locators, or implementation details.
- One Selenium test class → one analysis file (+ its `locators.md` and `test-data.md`) → one user story file → one journey module.
- Run inventory once before conversion. Then convert the **whole framework** through the two gates.
