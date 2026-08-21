# Reverse Engineering Migration Agent
# Selenium Framework >> User Stories >> Playwright TypeScript

## What this project does

This is the **Reverse Engineering (RE) Migration** path.

The source Selenium/Cypress/Robot/UFT framework is first DECONSTRUCTED into:
1. Analysis documents (analysis.md + locators.md per feature)
2. Business user stories (user_stories.md per feature)

Stakeholders review and approve the user stories at Gate 1.
ONLY after approval does the agent generate Playwright TypeScript code.

## Migration Path

```
Source Framework
      |
      v  Stage 1 -- Analyze
  analysis/<Feature>/analysis.md + locators.md
      |
      v  Stage 2 -- User Stories
  analysis/<Feature>/user_stories.md
      |
  GATE 1: Business Review -- stop for stakeholder approval
      |
      v  Stage 3 -- Implement
  src/modules/<feature>/ (Playwright TypeScript)
      |
      v  Run + Heal
  All tests green
      |
      v  Evidence Report
  analysis/MIGRATION-EVIDENCE.md
      |
  GATE 2: Final Review
```

## Key difference from Direct Migration

| | Reverse Engineering (this project) | Direct Migration (../direct-migration-agent/) |
|---|---|---|
| Analysis docs | YES -- analysis.md + locators.md | NO |
| User stories | YES -- user_stories.md | NO |
| Gates | 2 (business + final) | 1 (final only) |
| Use when | Business sign-off required | Technical team, speed priority |

## Available Agents

### Orchestrators
- selenium-re-migration.agent.md -- Selenium >> User Stories >> Playwright
- cypress-conversion-orchestrator.agent.md -- Cypress >> User Stories >> Playwright
- robot-conversion-orchestrator.agent.md -- Robot >> User Stories >> Playwright
- uft-conversion-orchestrator.agent.md -- UFT >> User Stories >> Playwright

### Supporting Agents
- selenium-analyzer.agent.md -- Stage 1: analyze Selenium source
- user-story-generator.agent.md -- Stage 2: generate user stories
- playwright-test-generator.agent.md -- Stage 3: generate Playwright code from user stories

## Config files
- selenium-source.json -- Selenium source path + features
- migration-source.json -- migration strategy = "reverse-engineering"
