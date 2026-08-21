---
applyTo: '**'
---
# Reverse Engineering Migration Agent
# Source Framework -> User Stories -> Playwright TypeScript

> **This is the Reverse Engineering migration path.**
> Source is deconstructed into analysis docs and business user stories.
> Gate 1 requires stakeholder approval before any code is written.
> For direct code-to-code translation (no docs, one gate), use `../direct-migration-agent/`.

---

## Available Reverse Engineering Migration Agents

| Source Framework | Agent File | Invoke With |
|---|---|---|
| **Selenium** (Java/Python/C#) | `selenium-re-migration.agent.md` | "Migrate the Selenium framework using reverse engineering" |
| **Cypress** (JS/TS) | `cypress-conversion-orchestrator.agent.md` | "Migrate the Cypress project end to end" |
| **Robot Framework** | `robot-conversion-orchestrator.agent.md` | "Migrate the Robot Framework end to end" |
| **UFT/QTP** (VBScript) | `uft-conversion-orchestrator.agent.md` | "Migrate the UFT project end to end" |

Attach the agent file via `#<agent-name>` in Copilot Chat then type the invoke phrase.

---

## Key Files

| File / Folder | Purpose |
|---|---|
| `selenium-source.json` | **Set this first.** Source path, features, targets |
| `migration-source.json` | Migration config (`migrationStrategy: "reverse-engineering"`) |
| `.github/prompts/<tool>-*.agent.md` | RE orchestrators per source tool |
| `../sawslab-playwright-re/` | Default Playwright output project |

---

## Pipeline (all tools)

```
PRE-FLIGHT  ->  Run source suite -> analysis/evidence/<tool>/
              ->  Create analysis/MIGRATION-EVIDENCE.md
Stage 1     ->  analysis/<Feature>/analysis.md + locators.md (all features)
Stage 2     ->  analysis/<Feature>/user_stories.md (all features)
GATE 1      ->  STOP -- business review of all user stories -- wait for "approved"
Stage 3     ->  src/modules/<feature>/ (page objects + spec) (all features)
Run         ->  npx playwright test --workers=1 --reporter=html,line
Heal        ->  fix failures until green
EVIDENCE    ->  Complete MIGRATION-EVIDENCE.md (target + mapping)
GATE 2      ->  STOP -- show evidence report -- wait for "approved"
```

---

## Single-Stage Agents (partial pipeline)

| Agent | Purpose |
|---|---|
| `selenium-analyzer.agent.md` | Stage 1 only -- analyze one feature |
| `user-story-generator.agent.md` | Stage 2 only -- generate user stories |
| `playwright-test-generator.agent.md` | Stage 3 only -- implement Playwright tests |

---

## Environment

- Source runs: `mvn test` (Selenium) / `npx cypress run` (Cypress) / `python -m robot` (Robot) / UFT CMD (UFT)
- Playwright run: `npx playwright test --workers=1 --reporter=html,line`
- Evidence report: `analysis/MIGRATION-EVIDENCE.md`
- Playwright report: `playwright-report/index.html`
