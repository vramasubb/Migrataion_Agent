# Selenium → Playwright: Direct Migration Agent

## Purpose

Directly translate a Selenium test framework into Playwright TypeScript **in a single pass** —
with no intermediate analysis documents, no user stories, and no first review gate.

## Migration Path

```
┌──────────────────────────────────────┐
│  Selenium Source (External, read-only) │
│  Java + Cucumber-JVM + REST Assured   │
└──────────────────────────────────────┘
              ↓  (one pass — direct code-to-code)
┌──────────────────────────────────────┐
│  sawslab-playwright-dm/              │
│  Playwright TypeScript framework     │
│  src/modules/<feature>/              │
│    <page>.page.ts                    │
│    <feature>.spec.ts                 │
│  src/shared/config/env.ts            │
└──────────────────────────────────────┘
```

**Compare with the Reverse Engineering Migration (`migration-agent/`):**

| | Direct Migration (this project) | Reverse Engineering (`migration-agent/`) |
|---|---|---|
| Analysis docs | ❌ None | ✅ `analysis.md + locators.md` |
| User stories | ❌ None | ✅ `user_stories.md` |
| Business review gate | ❌ 1 gate (final) | ✅ 2 gates (business + final) |
| Speed | ⚡ Faster | 🐢 Slower (more documentation) |
| Use when | Technical team, urgent | Business sign-off required |

## Quick Start

1. Set the Selenium source path in `selenium-source.json`
2. Set the output path in `migration-source.json` → `"outputFolder": "sawslab-playwright-dm"`
3. In Copilot Chat: attach `#selenium-direct-migration` → type **"Migrate the Selenium framework directly"**

## Pipeline

```
PRE-FLIGHT  →  Run Selenium source tests → save to analysis/evidence/selenium/
              →  Create analysis/MIGRATION-EVIDENCE.md (source section)
TRANSLATE   →  Read ALL Selenium source files → generate Playwright TypeScript directly
              →  No analysis.md, no locators.md, no user_stories.md
Run         →  npx playwright test --workers=1 --reporter=html,line
Heal        →  fix failures until green
EVIDENCE    →  Complete MIGRATION-EVIDENCE.md (target + mapping table)
⏸ GATE 1   →  STOP — show evidence report — wait for "approved"
```

**One gate only. Direct code-to-code translation. No reverse engineering required.**

## Output Project

Generated Playwright framework: `../sawslab-playwright-dm/`

Run it independently:
```
cd ../sawslab-playwright-dm
npm install
npx playwright install chromium
npm test
```

## Configuration

- `selenium-source.json` — Selenium source project path and feature list
- `migration-source.json` — output project path and migration strategy

## File Layout

```
direct-migration-agent/
  CLAUDE.md                            ← This file
  package.json
  selenium-source.json                 ← Point at your Selenium source
  migration-source.json                ← Migration config (direct strategy)
  .github/
    copilot-instructions.md            ← Usage guide for Copilot
    prompts/
      selenium-direct-migration.agent.md  ← The direct migration orchestrator
```
