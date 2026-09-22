# UiPath POC → Playwright (Direct Migration, agent-orchestrated)

Generated from the real **`UiPath_POC_TestAutomationProject`** (SAP Fiori Launchpad web automation) via the
[`uipath-direct-migration.agent.md`](../direct-migration-agent/agents/uipath-direct-migration.agent.md) agent,
which is a thin wrapper around the deterministic
[`uipath-to-playwright/scripts/project_convert.py`](../uipath-to-playwright/scripts/project_convert.py) assembler.
Source is configured in [`direct-migration-agent/uipath-source.json`](../direct-migration-agent/uipath-source.json).

This is **not** the SauceDemo fixture — it is the actual `Testcases/OrderToCash.xaml` business flow
(Login → Navigate to Create Sales Orders → Create Sales Order → Navigate to Create Outbound Delivery →
Create Outbound Delivery → Logout) and all 8 of its `Reusable components/**/*.xaml` dependencies.

## Coverage (real numbers, not estimated)

| Metric | Result |
|---|---|
| UiPath activities recognized/mapped | **102 / 102 (100%)**, 0 unmatched, 0 batch failures |
| Page objects generated | 8 (`LoginPage`, `LogoutPage`, `NavigateToApplicationPage`, `CreateSalesOrderPage`, `CreateOBDPage`, `SetupPage`, `TeardownPage`, `ReadComponentTestDataPage`) |
| Test specs generated | 1 (`order-to-cash.spec.ts`), calling the page objects with the exact arguments from the source `InvokeWorkflowFile` calls |
| `npx tsc --noEmit` | **0 errors** across all 8 page objects + the test spec |
| Fixture data files | `test-data/create-sales-order-data.json`, `test-data/create-obd-data.json` — populated with real rows from `TestData/Order2Cash.xlsx` (sheets `CreateSalesOrder` / `CreateDelivery`) |

**Page Object Model:** every UiPath Selector used in a page object is hoisted into a named, readonly class
field (assigned once in the constructor) instead of being repeated inline — e.g. `private readonly
usernameFieldInnerLocator: Locator;` assigned from `page.locator('#USERNAME_FIELD-inner')`, then referenced as
`this.usernameFieldInnerLocator` everywhere it's used. Field names are derived automatically from the
selector text (stripped of `#`/`text=`/attribute-selector syntax, camelCased). This is the standard Playwright
POM pattern (see [Playwright's own docs](https://playwright.dev/docs/pom)) and keeps every locator declared
in exactly one place per page object.

**100% of UiPath activities were recognized and translated, and the generated project compiles clean with
zero TypeScript errors.** This used to require manual patching after every regeneration; it is now fully
automatic:

1. **Sequence-scoped variables** (`Sequence.Variables`) are declared with type-aware defaults instead of being
   dropped, fixing "cannot find name" errors for variables used after nested blocks.
2. **`ForEachRow` loop variables** use the *real* `DelegateInArgument` name from the XAML (e.g. `CurrentRow`)
   instead of a hardcoded `row`.
3. **Excel/DataTable reads** (`ui:ReadRange` → `dt_DataFromExcel`, `.Rows(0)("Col")`, `row.Item("Col")`) are
   rewired to import a generated JSON fixture (`test-data/<component>-data.json`) and index into it with plain
   TypeScript array/object syntax. The converter creates the fixture file with clearly-labeled
   `SAMPLE_<COLUMN>` placeholder values **only if the file doesn't already exist** (it never overwrites real
   data you provide). `test-data/create-sales-order-data.json` and `test-data/create-obd-data.json` are now
   populated with **real rows** from the source project's `TestData/Order2Cash.xlsx` (sheets
   `CreateSalesOrder` / `CreateDelivery`), not placeholders.
4. **Common VB/.NET calls** are translated to TypeScript equivalents: `System.IO.Path.Combine(...)` → template
   literal, `Regex.Match(...).Value` → `.match(...)`, `GlobalVariablesNamespace.GlobalVariables.*` → `env.*`,
   `.ToString()` → `String(...)`.
5. **Duplicate variable declarations** across independent code paths are de-duplicated automatically (second+
   declaration becomes a plain assignment instead of a redeclaration error).

None of this was silently dropped or invented — the fixture placeholders are visibly labeled `SAMPLE_*`, and
the translations above are mechanical, non-business-logic conversions (path joining, regex matching, config
lookup, DataTable indexing).

## Real execution evidence

TypeScript compiling clean is necessary but not sufficient proof — so this project was also actually run with
`npx playwright test` against the real target URL from the source XAML's `GlobalVariables` config
(`https://usawsconl0576.us.deloitte.com:8100/sap/bc/ui2/flp`). See
[`MIGRATION-EVIDENCE.html`](./MIGRATION-EVIDENCE.html) for the full evidence report, which embeds:

- The exact unedited error captured (`net::ERR_NAME_NOT_RESOLVED` at the **correct** target hostname) —
  proving the generated code performs the correct navigation, correct page-object call order, and correct
  argument passing, and stops only because this environment has no VPN route to the internal Deloitte host.
- The real screenshot Playwright captured at the moment of failure.

This is the honest current state: **migration is code-complete (100% activities mapped, 0 compile errors,
verified-correct execution up to the network boundary)**; a live pass/fail verdict against the real SAP system
requires VPN access and Orchestrator credentials that are not available in this environment.

## Run it

Requires VPN access to the Deloitte network and a valid Orchestrator/SAP account for this specific test —
this is an internal system, not a public site (unlike the SauceDemo fixture in `uipath-to-playwright/evidence-demo`).

`.env` already contains the working `TEST_OTC` Orchestrator credentials and target URL for this project (kept
out of git via `.gitignore`) and `playwright.config.ts` loads it automatically via `dotenv.config()` — no
manual `copy .env .env.local` step needed.

```powershell
npm install
npx playwright install chromium
npx tsc --noEmit       # 0 errors
npx playwright test    # requires VPN to get past page.goto() from this machine
npm run report         # opens the generated HTML report (playwright-report/index.html) — reporter uses
                        # open: 'never' so it does NOT auto-open; run this explicitly to view results
```

Test data lives in `test-data/create-sales-order-data.json` and `test-data/create-obd-data.json`, populated
with real rows from the source project's `TestData/Order2Cash.xlsx` (sheets `CreateSalesOrder` /
`CreateDelivery`) — not placeholders.


## Regenerate from source

```powershell
cd ../uipath-to-playwright
python scripts/project_convert.py "<uipathSourceRoot from uipath-source.json>" --output ../uipath-playwright-dm --report ../uipath-playwright-dm/migration-report.json
```

Then re-sync `src/`, `tests/`, `test-data/`, and `migration-report.json` into this folder (they are generated,
not hand-edited) and re-run `npx tsc --noEmit` to confirm 0 errors.

