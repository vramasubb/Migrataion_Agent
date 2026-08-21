# Test Migration Agent UI

A React + Express web application for migrating legacy test automation frameworks to **Playwright TypeScript** using an AI agent.

## Supported Migrations

| From | To |
|---|---|
| Selenium WebDriver (Java / Python / C#) | Playwright TypeScript |
| Selenium UI + REST Assured API (Java) | Playwright TypeScript (UI + API) |
| Robot Framework | Playwright TypeScript |
| UFT / QTP (VBScript) | Playwright TypeScript |
| Cypress (JS / TS) | Playwright TypeScript |

## Quick Start

Double-click **`start-migration-ui.bat`** — it starts both the backend and the UI.

Or start them manually:

```bash
# Terminal 1 — Backend
cd migration-backend
node server.js

# Terminal 2 — UI
cd migration-ui
npm run dev
```

Open **http://localhost:5173** in your browser.

## How It Works

1. **Select migration type** in the UI (e.g. Selenium → Playwright)
2. **Enter paths** — source project folder and desired output folder
3. **Click Start Migration** — the backend writes `migration-source.json` into `migration-agent/`
4. The UI streams setup progress and then **guides you to open VS Code Copilot Chat**
5. In VS Code, invoke the agent prompt (e.g. `@agent #file:.github/prompts/selenium-conversion-orchestrator.agent.md`) and type **"Migrate the framework end to end"**
6. The agent runs the 3-stage pipeline with 2 human review gates

## Agent Prompt Files

Located in `migration-agent/.github/prompts/`:

| Migration | Prompt File |
|---|---|
| Selenium / Selenium+API | `selenium-conversion-orchestrator.agent.md` |
| Robot Framework | `robot-conversion-orchestrator.agent.md` |
| UFT / QTP | `uft-conversion-orchestrator.agent.md` |
| Cypress | `cypress-conversion-orchestrator.agent.md` |

## Project Structure

```
selenium migration/
├── start-migration-ui.bat          ← double-click to launch
├── migration-ui/                   ← React + TypeScript frontend (Vite)
│   └── src/
│       ├── pages/HomePage.tsx
│       ├── components/
│       │   ├── ToolSelector.tsx
│       │   ├── MigrationForm.tsx
│       │   └── MigrationProgress.tsx
│       ├── services/
│       │   ├── api.ts
│       │   └── migrationTools.ts
│       └── types/index.ts
├── migration-backend/              ← Express.js API server
│   └── server.js
└── migration-agent/                ← VS Code Copilot agent project
    ├── migration-source.json       ← written by the UI at runtime
    └── .github/prompts/
        ├── selenium-conversion-orchestrator.agent.md
        ├── robot-conversion-orchestrator.agent.md
        ├── uft-conversion-orchestrator.agent.md
        └── cypress-conversion-orchestrator.agent.md
```
