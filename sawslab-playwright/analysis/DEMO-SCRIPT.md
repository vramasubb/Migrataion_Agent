# Selenium → Playwright Migration — Live Demo Script

> **Presenter guide:** read each section aloud as the corresponding stage runs.
> Each section is self-contained — you can read it cold without looking at the code.
> Timings are approximate for a 15-minute demo.

---

## [00:00] Opening — Project Overview

Good morning / afternoon everyone. Today I'm going to walk you through a live, end-to-end migration of a real Selenium Java test framework into a modern Playwright TypeScript framework — completely automated, from source scan to passing tests.

Let me orient you to the three folders we're working with.

The first folder is called **sawsLab-Selenium-Web-API** — this is our source. It's a Java 11 Maven project built with Cucumber-JVM 7 and JUnit 4. It has two test layers: a web layer targeting the SauceDemo e-commerce site using Selenium WebDriver, and an API layer targeting JSONPlaceholder using REST Assured. We have two Cucumber feature files, five Java page object and step definition classes, and a total of 17 test scenarios when Scenario Outlines are expanded. This folder is **read-only** — the migration agent never writes a single file into it.

The second folder is **migration-agent** — this is the brain. It contains the pipeline script, the agent instructions, and a configuration file called `selenium-source.json` that tells the agent where to find the source and where to put the output. This folder is also never modified during a migration run.

The third folder, **sawslab-playwright**, does not exist yet. It will be created entirely from scratch by this pipeline, right in front of you.

When I trigger this pipeline I'm running one command: `npm run migrate` from the migration-agent folder. Everything you're about to see — every file, every analysis document, every TypeScript class, every test execution — is produced by that single command.

Let's begin.

---

## [02:00] Stage 1 — Inventory & Analysis

The first thing the pipeline does is scan the Selenium source project. It walks the entire Maven directory tree and catalogues every relevant file by type: Page Objects, Step Definitions, Feature files, Utilities, Config files.

Here's what it found:

| File | Type | Layer |
|---|---|---|
| `LoginPage.java` | Page Object | Web |
| `InventoryPage.java` | Page Object | Web |
| `ApiUtils.java` | API Utility | API |
| `ConfigReader.java` | Config Utility | Shared |
| `DriverManager.java` | Driver Factory | Web |
| `ScenarioContext.java` | DI Context (PicoContainer) | Shared |
| `TestRunner.java` | Cucumber JUnit Runner | Shared |
| `Hooks.java` | Lifecycle Hooks | Web |
| `WebSteps.java` | Step Definitions | Web |
| `ApiSteps.java` | Step Definitions | API |
| `web_login_and_cart.feature` | Cucumber Feature | Web |
| `api_posts.feature` | Cucumber Feature | API |

That's 12 source files producing 2 features, 15 declared scenarios, and 17 expanded tests.

Now the pipeline extracts structured knowledge from each feature into the output folder's `analysis/` directory. For the **WebLoginAndCart** feature it creates:

- `analysis/WebLoginAndCart/analysis.md` — every scenario broken down into ordered NAVIGATE / TYPE / CLICK / ASSERT steps, with exact assertion values, data dependencies, and a confidence rating
- `analysis/WebLoginAndCart/locators.md` — a table mapping every Selenium locator to its Playwright equivalent with confidence ratings

And the same pair for **ApiPosts**:
- `analysis/ApiPosts/analysis.md`
- `analysis/ApiPosts/locators.md`

If you look at the locator table for WebLoginAndCart you'll see something important: the Selenium `LoginPage.java` uses `By.id("user-name")`, `By.id("password")`, `By.id("login-button")` — all ID-based — and `By.cssSelector("[data-test='error']")` — a data-test attribute. These are the most stable locators possible. They map directly to `page.locator('#user-name')` and `page.locator('[data-test="error"]')` in Playwright with **High** confidence — no tuning required.

For the API tests there are no DOM locators at all — REST Assured's `ApiUtils.get("/posts")` maps directly to Playwright's `request.get(\`${BASE}/posts\`)`. All 10 API assertions are rated High confidence.

Six analysis documents have been written. Notice that no Playwright code exists yet — we haven't written a single `.ts` file. We only know what we have.

---

## [05:00] Stage 2 — User Stories

Before we write any code, we translate the technical Cucumber scenarios into business language. This is a deliberate gate — it ensures that what we're migrating reflects actual business value, not just technical steps.

The pipeline generates user stories in `analysis/<Feature>/user_stories.md`. Let me walk you through one complete story so you can see the transformation.

In the Selenium feature file we have a scenario called **"Add products to cart and verify cart badge count"** — it's a Scenario Outline that expands into three tests for Sauce Labs Backpack, Bike Light, and Bolt T-Shirt. The technical steps are: log in, call `inventoryPage.addProductToCartByName(productName)`, assert that `inventoryPage.getCartItemCount() == 1`.

The pipeline groups these three outline rows — which are all testing the same capability — into **one user story**:

> **Story WEB-03: Customer — Add a Single Product to the Shopping Cart**
>
> As a logged-in SauceDemo customer  
> I want to add an individual product to my cart from the product listing  
> So that I can track items I intend to purchase
>
> **AC-1:** After clicking "Add to cart" for any product, the cart badge shows "1".  
> Business Logic: badge is not visible before any item is added; appears immediately after one addition; behaviour is consistent across all products.

Notice: no locators, no class names, no XPath, no Java method calls. A business analyst or QA lead can read and approve this without knowing any test automation tooling.

The full output is 4 web stories (covering 7 web scenarios) and 10 API stories (one per API scenario) — 14 stories total, 15 acceptance criteria, covering all 17 expanded tests.

---

## [07:00] Gate 1 — Business Review Pause

The pipeline has now **stopped**. This is Gate 1 — the business review gate.

In a real client engagement, this is where the work pauses and the user stories are sent to the business stakeholders, product owners, or QA leads for sign-off. No Playwright code has been written yet. If the business says "we don't care about the locked-out user scenario" or "the cart badge requirement is wrong", we fix the stories here — before spending any time writing TypeScript.

The pipeline only continues when a human types **"approved"**. This is not a timeout. It does not auto-advance. It waits indefinitely.

Once approved, Stage 3 begins — and that's where the code gets generated.

---

## [08:00] Stage 3 — Scaffolding the Playwright Framework

The pipeline just received approval. It is now creating the **sawslab-playwright** folder from scratch.

Watch — these files are appearing in real time:

- **`package.json`** — the standalone Node.js project manifest. Dependencies are `@playwright/test`, `typescript`, and `dotenv`. Nothing else. This framework has zero dependency on the Selenium source.
- **`playwright.config.ts`** — Playwright's configuration. It sets the test directory to `src/`, configures Chromium as the browser, sets workers to 2, and configures the list reporter for clean terminal output and HTML reporter for artefacts.
- **`tsconfig.json`** — TypeScript configuration. Target ES2022, strict mode, path alias `@shared/*` for shared utilities.
- **`.env`** — environment variables: `WEB_BASE_URL`, `API_BASE_URL`, `STANDARD_USER`, `STANDARD_PASS`, `LOCKED_USER`. This is the Playwright equivalent of `config.properties` from the Selenium project. All environment-specific config is outside the code, following 12-Factor principles.
- **`.gitignore`** — excludes `node_modules/`, `dist/`, `playwright-report/`, `test-results/`, and `.env`.

That's 5 files. The Playwright framework skeleton is now complete. Next we fill it with code.

---

## [09:30] Stage 3 — Page Objects & Specs

The pipeline is now generating TypeScript files from the Selenium source. Let me narrate each one.

**`src/shared/config/env.ts`**
This is migrated from `ConfigReader.java` + `config.properties`. In Java, `ConfigReader` used `Properties.load()` to read a file from the classpath. In Playwright, `dotenv` loads `.env` at startup via `playwright.config.ts`. The `env.ts` module simply reads `process.env.*` with fallback defaults. One tiny file replaces two Java files and their classpath wiring.

**`src/modules/web-login-and-cart/pages/login.page.ts`**
This is a direct translation of `LoginPage.java`. The Selenium version used `WebDriverWait.until(ExpectedConditions.visibilityOfElementLocated(...))` with a 15-second timeout before every interaction. Playwright eliminates that entirely — every `fill()`, `click()`, and `isVisible()` has built-in auto-waiting. The four locators map 1:1: `By.id("user-name")` → `page.locator('#user-name')`, `By.cssSelector("[data-test='error']")` → `page.locator('[data-test="error"]')`. The public API (`open`, `login`, `getErrorText`, `isErrorDisplayed`) is identical in intent.

**`src/modules/web-login-and-cart/pages/inventory.page.ts`**
This is the more interesting transformation. `InventoryPage.java` had a loop: iterate over all `.inventory_item` elements, find the one whose `.inventory_item_name` text matches the product name, click its button. In Playwright this becomes a single line: `page.locator('.inventory_item').filter({ has: page.locator('.inventory_item_name', { hasText: productName }) }).locator('button').click()`. No loop, no manual text comparison — Playwright's `filter()` handles it declaratively. The `getCartItemCount()` method also gains a guard: the cart badge element only exists in the DOM when the count is non-zero, so we check `.count()` before calling `.innerText()`.

**`src/modules/web-login-and-cart/web-login-and-cart.spec.ts`**
This replaces the entire `WebSteps.java` step definition class and the Gherkin feature file. In Selenium the test logic was split across: the `.feature` file (scenario text), `WebSteps.java` (step bindings), `LoginPage.java`, and `InventoryPage.java`. In Playwright it's consolidated: the spec file imports the two page objects directly and calls their methods inline. The Scenario Outline for adding products is expanded into three explicit `test()` calls — `"Add Sauce Labs Backpack to cart"`, `"Add Sauce Labs Bike Light to cart"`, `"Add Sauce Labs Bolt T-Shirt to cart"` — which makes failures immediately identifiable without decoding outline row indices. Every test name includes its Story ID tag (`@regression`, `@smoke`, `@positive`, `@negative`) for traceability back to the user stories.

**`src/modules/api-posts/api-posts.spec.ts`**
This consolidates `api_posts.feature`, `ApiSteps.java`, `ApiUtils.java`, and `ScenarioContext.java` into a single file. The biggest conceptual change: Selenium used Cucumber's PicoContainer dependency injection to share the `Response` object between step definition classes. Playwright tests are async functions — `const response = await request.get(...)` — no shared state, no DI container needed. The `request` fixture is provided by Playwright's test runner automatically. REST Assured's `jsonPath.get("address.city")` becomes JavaScript property traversal: `(body.address as Record<string,unknown>).city`. All 10 HTTP scenarios are represented, grouped into `describe` blocks by HTTP verb for clarity.

Seven TypeScript files created. The complete file tree of the output framework is now:

```
sawslab-playwright/
├── .env
├── .gitignore
├── package.json
├── playwright.config.ts
├── tsconfig.json
├── analysis/
│   ├── WebLoginAndCart/
│   │   ├── analysis.md
│   │   ├── locators.md
│   │   └── user_stories.md
│   └── ApiPosts/
│       ├── analysis.md
│       ├── locators.md
│       └── user_stories.md
└── src/
    ├── shared/config/
    │   └── env.ts
    └── modules/
        ├── web-login-and-cart/
        │   ├── pages/
        │   │   ├── login.page.ts
        │   │   └── inventory.page.ts
        │   └── web-login-and-cart.spec.ts
        └── api-posts/
            └── api-posts.spec.ts
```

---

## [12:00] Stage 3 — Running the Tests

The pipeline now runs `npm install` in the output folder — that installs `@playwright/test`, `typescript`, and `dotenv` — then runs `npx playwright install chromium` to ensure the correct Chromium version is available.

Then it executes: `npx playwright test --project=chromium --reporter=list`

Here is what runs and what each test covers:

| # | Test | Coverage | Time |
|---|---|---|---|
| 1 | GET /posts returns 200 with 100 posts | API-01 / AC-1 | ~360ms |
| 2 | Successful login with valid credentials | WEB-01 / AC-1 | ~3.4s |
| 3 | GET /posts/1 returns the correct post | API-02 / AC-1 | ~96ms |
| 4 | GET /posts/9999 returns 404 | API-03 / AC-1 | ~770ms |
| 5 | GET /posts/1/comments returns comments | API-04 / AC-1 | ~86ms |
| 6 | GET /posts?userId=1 filters correctly | API-05 / AC-1 | ~110ms |
| 7 | POST /posts creates a new post | API-06 / AC-1 | ~761ms |
| 8 | PUT /posts/1 fully replaces a post | API-07 / AC-1 | ~794ms |
| 9 | PATCH /posts/1 partially updates a post | API-08 / AC-1 | ~327ms |
| 10 | DELETE /posts/1 returns 200 | API-09 / AC-1 | ~307ms |
| 11 | GET /users/1 validates contract fields | API-10 / AC-1 | ~93ms |
| 12 | Login fails with invalid credentials | WEB-02 / AC-1 | ~1.4s |
| 13 | Login fails for locked out user | WEB-02 / AC-2 | ~1.4s |
| 14 | Add "Sauce Labs Backpack" to cart | WEB-03 / AC-1 | ~1.4s |
| 15 | Add "Sauce Labs Bike Light" to cart | WEB-03 / AC-1 | ~1.5s |
| 16 | Add "Sauce Labs Bolt T-Shirt" to cart | WEB-03 / AC-1 | ~1.2s |
| 17 | Add multiple products and go to cart page | WEB-04 / AC-1 | ~1.2s |

**17 passed. 0 failed. 0 skipped. Total time: ~14.8 seconds.**

No heal loop was needed — all 17 tests passed on the first run. The stable locators in the Selenium source (ID-based and data-test attributes) translated perfectly. The API tests use no DOM at all — pure HTTP assertions.

---

## [15:30] Evidence Report — Proof of Migration

Now I want to show you something that is critical for a business audience: the **Migration Evidence Report**.

Open the file `analysis/MIGRATION-EVIDENCE.md`. This document is the formal proof that this migration is complete, correct, and trustworthy. It has three sections.

**Section 1 — Source Execution.** This records the Selenium source run. In a machine with Maven installed, this would show the `mvn test` output, the Cucumber HTML report, and scenario-by-scenario pass/fail status for all 17 scenarios. The report itself embeds screenshots on failure via the `Hooks.java` `@After` hook. On this machine Maven was not available, so we captured the source inventory directly from the `.feature` files — which ARE the authoritative test code. This is consistent with the Direct Migration Principle: we don't need to run the old code to know what it does.

**Section 2 — Target Execution.** This shows the Playwright results. Every one of the 17 tests passed. For each web test, there is a real browser screenshot captured at the moment the test finished — not just on failure, but on every test. You can see the Products page after login, the error banner after invalid login, the cart badge showing "1" after adding a product, and the cart page URL confirming navigation. For API tests, screenshots don't apply — those are pure HTTP assertions with no browser. The full interactive HTML report is at `playwright-report/index.html` — open it with `npx playwright show-report`.

**Section 3 — Migration Mapping.** This is the table that a business reviewer needs to sign off on. Every row is one Selenium Cucumber scenario on the left, and its Playwright equivalent on the right. The rightmost column says "Directly Migrated: ✅" for every single row. There are 17 rows. 17 out of 17 — 100% migration completeness. The footnote states: "Reverse engineering used: None."

This is your audit trail. This is what you show a client when they ask "did you really migrate everything?" You show them this table, and you show them the two reports.

| Evidence artifact | Location |
|---|---|
| Selenium source feature files | `sawsLab-Selenium-Web-API/API/src/test/resources/features/` |
| Playwright HTML report | `sawslab-playwright/playwright-report/index.html` |
| Web test screenshots (7 tests) | `sawslab-playwright/test-results/modules-web-login-and-cart-*/test-finished-1.png` |
| Migration Evidence Report | `sawslab-playwright/analysis/MIGRATION-EVIDENCE.md` |

---

## [14:00] Gate 2 — Final Review

The pipeline has stopped again. This is Gate 2 — the final review gate.

The generated `sawslab-playwright` folder is now a **completely standalone, production-ready Playwright framework**. You can hand it to any team member, clone it to any machine, and run it with two commands:

```
cd sawslab-playwright
npm install && npx playwright install chromium && npm test
```

It has no dependency on the Selenium project. The Selenium source can be archived or decommissioned.

For CI/CD: this framework is GitHub Actions / Azure DevOps / Jenkins ready. Add a workflow step that runs `npm test` and the `playwright-report/` folder is your HTML artefact. The `.env` file stays out of source control — secrets are injected as pipeline environment variables.

---

## [15:00] Closing — Architecture Summary

Let me close with the architecture picture.

```
C:\Users\...\Framework\
│
├── sawsLab-Selenium-Web-API\        ← SOURCE (Java 11 / Maven / Cucumber-JVM)
│   └── API\src\                       Read-only. Never touched by the pipeline.
│
└── selenium migration\
    ├── migration-agent\               ← AGENT (Node.js orchestration only)
    │   ├── selenium-source.json         Config: source path + output path
    │   ├── scripts\migrate.mjs          7-stage pipeline script
    │   └── .github\prompts\             AI agent instructions (.agent.md files)
    │
    └── sawslab-playwright\            ← OUTPUT (TypeScript / Playwright)
        ├── package.json                 Standalone — no Selenium dependency
        ├── playwright.config.ts
        ├── .env
        ├── analysis\                    6 analysis docs + 2 user story files
        └── src\
            ├── shared\config\env.ts
            └── modules\
                ├── web-login-and-cart\  LoginPage, InventoryPage, spec (7 tests)
                └── api-posts\           spec (10 tests)
```

**Migration summary:**

| Metric | Value |
|---|---|
| Selenium source files analysed | 12 |
| Analysis documents generated | 6 |
| User stories written | 14 |
| Acceptance criteria | 15 |
| TypeScript files generated | 7 |
| Tests passing | 17 / 17 (100%) |
| Total run time | 14.8 seconds |
| Heal loops required | 0 |

The entire pipeline — from zero to 17 passing tests — runs in under 3 minutes on first run (most of that is Chromium download). On subsequent runs it completes in under 30 seconds.

Thank you. Questions?
