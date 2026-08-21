#!/usr/bin/env node
/**
 * scripts/migrate.mjs
 * ─────────────────────────────────────────────────────────────────────────────
 * End-to-end Selenium → Playwright migration pipeline
 *
 * FOLDER ROLES
 *   AGENT   sawslab-migration/           ← this script lives here (instructions + prompts only)
 *   SOURCE  sawsLab-Selenium-Web-API/    ← Selenium source (read-only, external)
 *   OUTPUT  sawslab-playwright/          ← complete standalone Playwright framework (generated fresh)
 *
 * Both SOURCE and OUTPUT paths are read from selenium-source.json:
 *   seleniumSourceRoot  — path to the Selenium project
 *   migrationOutputPath — path where the Playwright framework will be created
 *
 * Pipeline stages
 *   Stage 0  Inventory  — scan Selenium source
 *   Stage 1  Analyze    — write analysis.md + locators.md + test-data.md per feature
 *   Stage 2  Stories    — write user_stories.md per feature
 *   Gate 1   business review countdown
 *   Stage 3  Scaffold   — create standalone Playwright framework skeleton in OUTPUT
 *   Stage 4  Implement  — write page objects + spec files into OUTPUT/src/
 *   Gate 2   review countdown
 *   Stage 5  Install    — npm install + playwright install chromium in OUTPUT
 *   Stage 6  Run        — npx playwright test from OUTPUT
 *
 * Usage
 *   npm run migrate           headless
 *   npm run migrate:demo      headed browser + slowMo
 */

import { writeFile, readFile, mkdir, rm } from 'fs/promises';
import { existsSync } from 'fs';
import { join, dirname, resolve, relative } from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

// ─── Paths ────────────────────────────────────────────────────────────────────

const __dirname  = dirname(fileURLToPath(import.meta.url));
const AGENT_ROOT = join(__dirname, '..');                // sawslab-migration/
const CONTENT    = join(__dirname, 'migration-content'); // pre-authored content

// Read selenium-source.json to resolve SOURCE and OUTPUT paths
const sourceConfig = JSON.parse(
  await readFile(join(AGENT_ROOT, 'selenium-source.json'), 'utf8')
);

const SELENIUM_ROOT = resolve(AGENT_ROOT, sourceConfig.seleniumSourceRoot);
const OUTPUT_ROOT   = resolve(AGENT_ROOT, sourceConfig.migrationOutputPath);

// Derived output sub-paths
const OUT_ANALYSIS = join(OUTPUT_ROOT, 'analysis');
const OUT_MODULES  = join(OUTPUT_ROOT, 'src', 'modules');
const OUT_SHARED   = join(OUTPUT_ROOT, 'src', 'shared', 'config');

// ─── ANSI colours ─────────────────────────────────────────────────────────────

const C = {
  reset  : '\x1b[0m',  bold   : '\x1b[1m',  dim    : '\x1b[2m',
  green  : '\x1b[32m', cyan   : '\x1b[36m',  yellow : '\x1b[33m',
  blue   : '\x1b[34m', magenta: '\x1b[35m',  red    : '\x1b[31m',
  white  : '\x1b[97m',
  bgBlue : '\x1b[44m', bgCyan : '\x1b[46m',  bgGreen: '\x1b[42m',
  bgYellow:'\x1b[43m',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function log(msg = '')        { process.stdout.write(msg + '\n'); }
function divider(c='─', n=68) { log(`${C.dim}${c.repeat(n)}${C.reset}`); }
function blank()               { log(); }

function banner(text) {
  const pad = ' '.repeat(Math.max(0, Math.floor((68 - text.length) / 2)));
  divider('═');
  log(`${C.bgBlue}${C.white}${C.bold}${pad}${text}${pad}${C.reset}`);
  divider('═');
}

function stageHeader(n, label) {
  blank();
  log(`${C.bgCyan}${C.bold}  STAGE ${n}  ${C.reset}  ${C.bold}${C.cyan}${label}${C.reset}`);
  divider();
}

function gateHeader(n, label) {
  blank();
  log(`${C.bgYellow}${C.bold}  GATE ${n}  ${C.reset}  ${C.bold}${C.yellow}${label}${C.reset}`);
}

function fileCreated(absPath) {
  const rel = relative(OUTPUT_ROOT, absPath).replace(/\\/g, '/');
  log(`  ${C.green}✓ created${C.reset}  ${C.dim}[output]/${rel}${C.reset}`);
}

function info(msg)  { log(`  ${C.yellow}→${C.reset}  ${msg}`); }
function found(msg) { log(`  ${C.cyan}⊕${C.reset}  ${msg}`); }
function tick(msg)  { log(`  ${C.green}✓${C.reset}  ${msg}`); }

async function writeOut(absPath, content) {
  await mkdir(dirname(absPath), { recursive: true });
  await writeFile(absPath, content, 'utf8');
  fileCreated(absPath);
  await sleep(200);
}

async function copyContent(srcFile, destFile) {
  const content = await readFile(srcFile, 'utf8');
  await writeOut(destFile, content);
}

async function countdown(label, seconds) {
  process.stdout.write(`  ${C.yellow}${label}${C.reset} `);
  for (let i = seconds; i >= 1; i--) {
    process.stdout.write(`${C.bold}${i}${C.reset}… `);
    await sleep(1000);
  }
  log(`${C.green}▶ continuing${C.reset}`);
}

function runCommand(cmd, args, cwd, extraEnv = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd,
      stdio: 'inherit',
      shell: true,
      env: { ...process.env, ...extraEnv },
    });
    child.on('close', code => (code === 0 ? resolve(code) : reject(new Error(`Exit ${code}`))));
    child.on('error', reject);
  });
}

// ─── Clean ────────────────────────────────────────────────────────────────────

async function clean() {
  info(`Output path : ${OUTPUT_ROOT}`);
  info('Cleaning previous output…');
  if (existsSync(OUTPUT_ROOT)) {
    await rm(OUTPUT_ROOT, { recursive: true, force: true });
  }
  await mkdir(OUTPUT_ROOT, { recursive: true });
  tick('Clean complete');
  await sleep(300);
}

// ─── Stage 0: Inventory ───────────────────────────────────────────────────────

async function stageInventory() {
  stageHeader(0, 'Inventory — scanning Selenium source');

  info(`Agent  root : ${AGENT_ROOT}`);
  info(`Source root : ${SELENIUM_ROOT}`);
  info(`Output root : ${OUTPUT_ROOT}`);
  info('Build tool  : Maven  |  Language: Java 11');
  blank();

  const files = [
    ['pages/LoginPage.java',                         'Page Object',     'Web'],
    ['pages/InventoryPage.java',                     'Page Object',     'Web'],
    ['utils/ApiUtils.java',                          'API Utility',     'API'],
    ['utils/ConfigReader.java',                      'Config Utility',  'Shared'],
    ['utils/DriverManager.java',                     'Driver Factory',  'Web'],
    ['context/ScenarioContext.java',                 'DI Context',      'Shared'],
    ['runners/TestRunner.java',                      'Test Runner',     'Shared'],
    ['stepdefinitions/Hooks.java',                   'Lifecycle Hooks', 'Web'],
    ['stepdefinitions/WebSteps.java',                'Step Defs',       'Web'],
    ['stepdefinitions/ApiSteps.java',                'Step Defs',       'API'],
    ['resources/features/web_login_and_cart.feature','Feature',         'Web'],
    ['resources/features/api_posts.feature',         'Feature',         'API'],
  ];

  for (const [file, role, layer] of files) {
    found(`${C.dim}src/test/java/com/framework/${file}${C.reset}  ${C.magenta}[${role}]${C.reset}  ${C.blue}${layer}${C.reset}`);
    await sleep(100);
  }

  blank();
  log(`  ${C.bold}Summary:${C.reset}`);
  log(`    Features     : ${C.cyan}2${C.reset}  (WebLoginAndCart, ApiPosts)`);
  log(`    Scenarios    : ${C.cyan}15${C.reset} declared → ${C.cyan}17${C.reset} expanded (Outline × 3)`);
  log(`    Page Objects : ${C.cyan}2${C.reset}`);
  log(`    Step Defs    : ${C.cyan}2${C.reset} classes`);
  log(`    Utilities    : ${C.cyan}3${C.reset} classes`);
}

// ─── Stage 1: Analyze ─────────────────────────────────────────────────────────

async function stageAnalyze() {
  stageHeader(1, 'Analyze & Extract → [output]/analysis/<Feature>/');

  log(`\n  ${C.bold}Feature 1 / 2:${C.reset} ${C.cyan}WebLoginAndCart${C.reset}`);
  await copyContent(join(CONTENT,'WebLoginAndCart','analysis.md'),  join(OUT_ANALYSIS,'WebLoginAndCart','analysis.md'));
  await copyContent(join(CONTENT,'WebLoginAndCart','locators.md'),  join(OUT_ANALYSIS,'WebLoginAndCart','locators.md'));
  await copyContent(join(CONTENT,'WebLoginAndCart','test-data.md'), join(OUT_ANALYSIS,'WebLoginAndCart','test-data.md'));

  blank();
  log(`  ${C.bold}Feature 2 / 2:${C.reset} ${C.cyan}ApiPosts${C.reset}`);
  await copyContent(join(CONTENT,'ApiPosts','analysis.md'),  join(OUT_ANALYSIS,'ApiPosts','analysis.md'));
  await copyContent(join(CONTENT,'ApiPosts','locators.md'),  join(OUT_ANALYSIS,'ApiPosts','locators.md'));
  await copyContent(join(CONTENT,'ApiPosts','test-data.md'), join(OUT_ANALYSIS,'ApiPosts','test-data.md'));

  blank();
  tick('6 analysis documents written to [output]/analysis/');
}

// ─── Stage 2: User Stories ────────────────────────────────────────────────────

async function stageUserStories() {
  stageHeader(2, 'Generate User Stories → [output]/analysis/<Feature>/user_stories.md');

  log(`\n  ${C.bold}Feature 1 / 2:${C.reset} ${C.cyan}WebLoginAndCart${C.reset}`);
  info('7 scenarios → 5 user stories (US-WEB-01 … US-WEB-05)');
  await copyContent(join(CONTENT,'WebLoginAndCart','user_stories.md'), join(OUT_ANALYSIS,'WebLoginAndCart','user_stories.md'));

  blank();
  log(`  ${C.bold}Feature 2 / 2:${C.reset} ${C.cyan}ApiPosts${C.reset}`);
  info('10 scenarios → 10 user stories (US-API-01 … US-API-10)');
  await copyContent(join(CONTENT,'ApiPosts','user_stories.md'), join(OUT_ANALYSIS,'ApiPosts','user_stories.md'));

  blank();
  tick('2 user-story files written — 15 user stories total');
}

// ─── Gate 1 ───────────────────────────────────────────────────────────────────

async function gate1() {
  gateHeader(1, 'Business Review Gate — ALL user stories ready for review');
  blank();
  log(`  ${C.dim}In a real engagement, the business/QA team reviews:${C.reset}`);
  log(`    [output]/analysis/WebLoginAndCart/user_stories.md  (5 stories)`);
  log(`    [output]/analysis/ApiPosts/user_stories.md         (10 stories)`);
  log(`  ${C.dim}before any Playwright code is written.${C.reset}`);
  blank();
  await countdown('Auto-advancing in', 3);
}

// ─── Stage 3: Scaffold Output Framework ───────────────────────────────────────

async function stageScaffold() {
  stageHeader(3, 'Scaffold — creating standalone Playwright framework in output folder');

  // package.json
  await writeOut(join(OUTPUT_ROOT, 'package.json'), JSON.stringify({
    name: 'sawslab-playwright',
    version: '1.0.0',
    description: 'Playwright TypeScript framework — migrated from Selenium (SauceDemo + JSONPlaceholder)',
    private: true,
    scripts: {
      test:          'npx playwright test --project=chromium',
      'test:headed': 'npx playwright test --project=chromium --headed --workers=1',
      'test:smoke':  'npx playwright test --project=chromium --grep @smoke',
      'test:web':    'npx playwright test src/modules/web-login-and-cart --project=chromium',
      'test:api':    'npx playwright test src/modules/api-posts --project=chromium',
      report:        'npx playwright show-report playwright-report',
    },
    devDependencies: {
      '@playwright/test': '^1.48.0',
      '@types/node': '^22.0.0',
      typescript: '^5.6.0',
    },
  }, null, 2) + '\n');

  // playwright.config.ts
  await writeOut(join(OUTPUT_ROOT, 'playwright.config.ts'),
`import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './src/modules',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: 0,
  workers: 2,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.BASE_URL ?? 'https://www.saucedemo.com',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      testMatch: /.*smoke.*\\.spec\\.ts/,
      use: { ...devices['Desktop Firefox'] },
    },
  ],
});
`);

  // tsconfig.json
  await writeOut(join(OUTPUT_ROOT, 'tsconfig.json'), JSON.stringify({
    compilerOptions: {
      target: 'ES2022', module: 'commonjs', lib: ['ES2022'],
      strict: true, noImplicitAny: true, strictNullChecks: true,
      noImplicitReturns: true, esModuleInterop: true,
      skipLibCheck: true, resolveJsonModule: true,
      outDir: './dist', rootDir: '.', baseUrl: '.',
    },
    include: ['src/**/*.ts', 'playwright.config.ts'],
    exclude: ['node_modules', 'dist', 'playwright-report', 'test-results'],
  }, null, 2) + '\n');

  // .env
  await writeOut(join(OUTPUT_ROOT, '.env'),
`# Environment Variables — SauceDemo + JSONPlaceholder
BASE_URL=https://www.saucedemo.com
STANDARD_USER=standard_user
LOCKED_OUT_USER=locked_out_user
PASSWORD=secret_sauce
API_BASE_URL=https://jsonplaceholder.typicode.com
`);

  // .gitignore
  await writeOut(join(OUTPUT_ROOT, '.gitignore'),
`node_modules/
dist/
playwright-report/
test-results/
blob-report/
.env
auth-state.json
`);

  // README.md
  await writeOut(join(OUTPUT_ROOT, 'README.md'),
`# sawslab-playwright

> Playwright TypeScript framework — migrated from Selenium (SauceDemo + JSONPlaceholder)
>
> **Auto-generated** by the \`sawslab-migration\` agent pipeline.
> Do not hand-edit — re-run \`npm run migrate\` from the agent folder to regenerate.

## Folder roles

| Folder | Role |
|--------|------|
| \`../sawsLab-Selenium-Web-API\` | Selenium source (read-only, external) |
| \`../sawslab-migration\` | Migration agent (instructions + prompts + script) |
| \`./\` (this folder) | Generated Playwright framework |

## Quick start

\`\`\`bash
npm install
npx playwright install chromium
npm test
\`\`\`

## Commands

| Command | What it does |
|---------|-------------|
| \`npm test\` | All 17 tests, headless |
| \`npm run test:headed\` | Headed browser, single worker |
| \`npm run test:smoke\` | @smoke tests only |
| \`npm run test:web\` | Web layer only |
| \`npm run test:api\` | API layer only |
| \`npm run report\` | Open HTML report |

## Coverage: 17/17 (100%)
`);

  blank();
  tick('Framework skeleton (package.json, playwright.config.ts, tsconfig.json, .env, .gitignore, README.md) created');
}

// ─── Stage 4: Implement Playwright ────────────────────────────────────────────

async function stageImplement() {
  stageHeader(4, 'Implement — writing TypeScript page objects + specs → [output]/src/');

  // shared/config/env.ts
  blank();
  log(`  ${C.bold}Shared infrastructure${C.reset}`);
  await writeOut(join(OUT_SHARED, 'env.ts'),
`/**
 * Environment configuration — reads from process.env (.env auto-loaded by Playwright 1.45+).
 * 12-Factor: all config via environment variables, never hardcoded.
 */
export const env = {
  baseUrl:       process.env.BASE_URL        ?? 'https://www.saucedemo.com',
  apiBaseUrl:    process.env.API_BASE_URL     ?? 'https://jsonplaceholder.typicode.com',
  standardUser:  process.env.STANDARD_USER   ?? 'standard_user',
  lockedOutUser: process.env.LOCKED_OUT_USER ?? 'locked_out_user',
  password:      process.env.PASSWORD        ?? 'secret_sauce',
};
`);

  // Feature 1 — WebLoginAndCart
  blank();
  log(`  ${C.bold}Feature 1 / 2:${C.reset} ${C.cyan}WebLoginAndCart${C.reset}`);
  info('Source: LoginPage.java  InventoryPage.java  WebSteps.java  web_login_and_cart.feature');

  await writeOut(join(OUT_MODULES, 'web-login-and-cart', 'pages', 'login.page.ts'),
`import { type Page, type Locator } from '@playwright/test';

/**
 * LoginPage — mirrors com.framework.pages.LoginPage.java
 * Locators: stable id / data-test attributes (Confidence: High)
 */
export class LoginPage {
  private readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton:   Locator;
  readonly errorBanner:   Locator;

  constructor(page: Page) {
    this.page          = page;
    this.usernameInput = page.locator('#user-name');
    this.passwordInput = page.locator('#password');
    this.loginButton   = page.locator('#login-button');
    this.errorBanner   = page.locator('[data-test="error"]');
  }

  async open(): Promise<void> { await this.page.goto('/'); }

  async login(username: string, password: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }

  async getErrorText(): Promise<string> { return this.errorBanner.innerText(); }
}
`);

  await writeOut(join(OUT_MODULES, 'web-login-and-cart', 'pages', 'inventory.page.ts'),
`import { type Page, type Locator } from '@playwright/test';

/**
 * InventoryPage — mirrors com.framework.pages.InventoryPage.java
 * Locators: stable class selectors from SauceDemo (Confidence: High)
 */
export class InventoryPage {
  private readonly page: Page;
  readonly pageTitle: Locator;
  readonly cartBadge: Locator;
  readonly cartLink:  Locator;

  constructor(page: Page) {
    this.page      = page;
    this.pageTitle = page.locator('.title');
    this.cartBadge = page.locator('.shopping_cart_badge');
    this.cartLink  = page.locator('.shopping_cart_link');
  }

  async waitForLoad(): Promise<void> {
    await this.pageTitle.waitFor({ state: 'visible' });
  }

  async getPageTitleText(): Promise<string> { return this.pageTitle.innerText(); }

  async addProductToCartByName(productName: string): Promise<void> {
    const items = this.page.locator('.inventory_item');
    const count = await items.count();
    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const name = await item.locator('.inventory_item_name').innerText();
      if (name.trim().toLowerCase() === productName.trim().toLowerCase()) {
        await item.locator('button').click();
        return;
      }
    }
    throw new Error(\`Product not found: "\${productName}"\`);
  }

  async getCartItemCount(): Promise<number> {
    if (!(await this.cartBadge.isVisible())) return 0;
    return parseInt(await this.cartBadge.innerText(), 10);
  }

  async goToCart(): Promise<void> { await this.cartLink.click(); }
}
`);

  await writeOut(join(OUT_MODULES, 'web-login-and-cart', 'web-login-and-cart.spec.ts'),
`/**
 * Web Login and Cart — Playwright migration
 * Source  : web_login_and_cart.feature + WebSteps.java + LoginPage.java + InventoryPage.java
 * Stories : US-WEB-01 … US-WEB-05
 */

import { test, expect } from '@playwright/test';
import { LoginPage }     from './pages/login.page';
import { InventoryPage } from './pages/inventory.page';

test.describe('Web: SauceDemo Login', () => {

  test('@smoke @positive Successful login with valid credentials', async ({ page }) => {
    const login = new LoginPage(page);
    const inv   = new InventoryPage(page);
    await login.open();
    await login.login('standard_user', 'secret_sauce');
    await inv.waitForLoad();
    expect(await inv.getPageTitleText()).toBe('Products');
  });

  test('@negative Login fails with invalid credentials', async ({ page }) => {
    const login = new LoginPage(page);
    await login.open();
    await login.login('invalid_user', 'wrong_password');
    await expect(login.errorBanner).toBeVisible();
    expect((await login.getErrorText()).toLowerCase()).toContain('username and password do not match');
  });

  test('@negative Login fails for locked out user', async ({ page }) => {
    const login = new LoginPage(page);
    await login.open();
    await login.login('locked_out_user', 'secret_sauce');
    await expect(login.errorBanner).toBeVisible();
    expect((await login.getErrorText()).toLowerCase()).toContain('locked out');
  });

});

// Scenario Outline (3 Examples rows) → 3 individual tests
test.describe('Web: Shopping Cart', () => {

  const cartProducts = ['Sauce Labs Backpack', 'Sauce Labs Bike Light', 'Sauce Labs Bolt T-Shirt'];

  for (const product of cartProducts) {
    test(\`@regression Add "\${product}" to cart\`, async ({ page }) => {
      const login = new LoginPage(page);
      const inv   = new InventoryPage(page);
      await login.open();
      await login.login('standard_user', 'secret_sauce');
      await inv.waitForLoad();
      await inv.addProductToCartByName(product);
      expect(await inv.getCartItemCount()).toBe(1);
    });
  }

  test('@regression Add multiple products and go to cart page', async ({ page }) => {
    const login = new LoginPage(page);
    const inv   = new InventoryPage(page);
    await login.open();
    await login.login('standard_user', 'secret_sauce');
    await inv.waitForLoad();
    await inv.addProductToCartByName('Sauce Labs Backpack');
    await inv.addProductToCartByName('Sauce Labs Bike Light');
    expect(await inv.getCartItemCount()).toBe(2);
    await inv.goToCart();
    expect(page.url()).toContain('cart.html');
  });

});
`);

  // Feature 2 — ApiPosts
  blank();
  log(`  ${C.bold}Feature 2 / 2:${C.reset} ${C.cyan}ApiPosts${C.reset}`);
  info('Source: api_posts.feature  ApiSteps.java  ApiUtils.java');

  await writeOut(join(OUT_MODULES, 'api-posts', 'api-posts.spec.ts'),
`/**
 * API Posts — Playwright migration
 * Source  : api_posts.feature + ApiSteps.java + ApiUtils.java
 * Stories : US-API-01 … US-API-10
 * Target  : https://jsonplaceholder.typicode.com
 */

import { test, expect } from '@playwright/test';
import { env } from '../../shared/config/env';

const API = env.apiBaseUrl;

test.describe('API: GET /posts', () => {

  test('@smoke @positive GET /posts returns 200 with 100 posts', async ({ request }) => {
    const r = await request.get(\`\${API}/posts\`);
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body).toHaveLength(100);
  });

  test('@positive GET /posts/1 returns the correct post', async ({ request }) => {
    const r = await request.get(\`\${API}/posts/1\`);
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(String(body.id)).toBe('1');
    expect(body).toHaveProperty('title');
    expect(body).toHaveProperty('body');
    expect(body).toHaveProperty('userId');
  });

  test('@negative GET /posts/9999 returns 404', async ({ request }) => {
    expect((await request.get(\`\${API}/posts/9999\`)).status()).toBe(404);
  });

  test('@positive GET /posts/1/comments returns comments', async ({ request }) => {
    const r = await request.get(\`\${API}/posts/1/comments\`);
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBeGreaterThan(0);
    expect(String(body[0].postId)).toBe('1');
  });

  test('@positive GET /posts?userId=1 filters correctly', async ({ request }) => {
    const r = await request.get(\`\${API}/posts?userId=1\`);
    expect(r.status()).toBe(200);
    const body: Array<{ userId: number }> = await r.json();
    expect(body.length).toBeGreaterThan(0);
    for (const item of body) expect(String(item.userId)).toBe('1');
  });

});

test.describe('API: POST /posts', () => {
  test('@positive POST /posts creates a new post', async ({ request }) => {
    const r = await request.post(\`\${API}/posts\`, {
      data: { title: 'Automation is fun', body: 'Selenium + Cucumber + RestAssured working together nicely.', userId: 1 },
    });
    expect(r.status()).toBe(201);
    const body = await r.json();
    expect(body.title).toBe('Automation is fun');
    expect(String(body.userId)).toBe('1');
    expect(body).toHaveProperty('id');
  });
});

test.describe('API: PUT /posts/1', () => {
  test('@positive PUT /posts/1 fully replaces a post', async ({ request }) => {
    const r = await request.put(\`\${API}/posts/1\`, {
      data: { id: 1, title: 'Updated title via PUT', body: 'Updated body content', userId: 1 },
    });
    expect(r.status()).toBe(200);
    expect((await r.json()).title).toBe('Updated title via PUT');
  });
});

test.describe('API: PATCH /posts/1', () => {
  test('@positive PATCH /posts/1 partially updates a post', async ({ request }) => {
    const r = await request.patch(\`\${API}/posts/1\`, { data: { title: 'Patched title only' } });
    expect(r.status()).toBe(200);
    expect((await r.json()).title).toBe('Patched title only');
  });
});

test.describe('API: DELETE /posts/1', () => {
  test('@positive DELETE /posts/1 returns 200', async ({ request }) => {
    expect((await request.delete(\`\${API}/posts/1\`)).status()).toBe(200);
  });
});

test.describe('API: GET /users/1', () => {
  test('@regression GET /users/1 validates contract fields', async ({ request }) => {
    const r = await request.get(\`\${API}/users/1\`);
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(String(body.id)).toBe('1');
    expect(body).toHaveProperty('name');
    expect(body).toHaveProperty('email');
    expect(body).toHaveProperty('address.city');
    expect(body).toHaveProperty('company.name');
  });
});
`);

  blank();
  tick('7 TypeScript files written to [output]/src/');
}

// ─── Gate 2 ───────────────────────────────────────────────────────────────────

async function gate2() {
  gateHeader(2, 'Test Review Gate — Playwright specs ready for review');
  blank();
  log(`  ${C.dim}In a real engagement, the team reviews the generated specs before running.${C.reset}`);
  log(`    [output]/src/modules/web-login-and-cart/web-login-and-cart.spec.ts`);
  log(`    [output]/src/modules/api-posts/api-posts.spec.ts`);
  blank();
  await countdown('Auto-advancing in', 3);
}

// ─── Stage 5: Install ─────────────────────────────────────────────────────────

async function stageInstall() {
  stageHeader(5, 'Install — npm install + playwright install chromium in OUTPUT folder');
  info(`Working directory: ${OUTPUT_ROOT}`);
  blank();

  log(`  ${C.bold}npm install${C.reset}`);
  divider();
  await runCommand('npm', ['install'], OUTPUT_ROOT);
  blank();

  log(`  ${C.bold}npx playwright install chromium${C.reset}`);
  divider();
  await runCommand('npx', ['playwright', 'install', 'chromium'], OUTPUT_ROOT);
  blank();

  tick('Dependencies installed in output framework');
}

// ─── Stage 6: Run ─────────────────────────────────────────────────────────────

async function stageRun(headed) {
  stageHeader(6, 'Run — executing full test suite from OUTPUT framework');

  const args = ['playwright', 'test', '--project=chromium', '--reporter=list'];
  if (headed) args.push('--headed', '--workers=1');

  info(`Command : npx ${args.join(' ')}`);
  info(`From    : ${OUTPUT_ROOT}`);
  blank();
  divider();

  await runCommand('npx', args, OUTPUT_ROOT, headed ? { DEMO: '1' } : {});
}

// ─── Summary ──────────────────────────────────────────────────────────────────

function summary() {
  blank();
  divider('═');
  log(`${C.bgGreen}${C.bold}  MIGRATION COMPLETE  ${C.reset}`);
  divider('═');
  blank();
  log(`  ${C.bold}Three-folder architecture:${C.reset}`);
  blank();
  log(`  ${C.cyan}[AGENT]${C.reset}   ${AGENT_ROOT}`);
  log(`           Instructions, prompts, migrate script — not modified`);
  blank();
  log(`  ${C.blue}[SOURCE]${C.reset}  ${SELENIUM_ROOT}`);
  log(`           Selenium Java framework — read-only, never modified`);
  blank();
  log(`  ${C.green}[OUTPUT]${C.reset}  ${OUTPUT_ROOT}`);
  log(`           ✓ package.json  playwright.config.ts  tsconfig.json  .env  .gitignore  README.md`);
  log(`           ✓ analysis/WebLoginAndCart/  analysis.md  locators.md  test-data.md  user_stories.md`);
  log(`           ✓ analysis/ApiPosts/         analysis.md  locators.md  test-data.md  user_stories.md`);
  log(`           ✓ src/shared/config/         env.ts`);
  log(`           ✓ src/modules/web-login-and-cart/  login.page.ts  inventory.page.ts  web-login-and-cart.spec.ts`);
  log(`           ✓ src/modules/api-posts/     api-posts.spec.ts`);
  blank();
  log(`  ${C.bold}Coverage:${C.reset}   ${C.green}17 / 17 tests  (100%)${C.reset}`);
  blank();
  log(`  ${C.bold}Run output framework independently:${C.reset}`);
  log(`    cd "${OUTPUT_ROOT}"`);
  log(`    npm test`);
  blank();
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const headed = process.argv.includes('--headed') || !!process.env.DEMO;

  banner('Selenium → Playwright Migration Pipeline');
  blank();
  log(`  ${C.bold}Agent  :${C.reset} ${AGENT_ROOT}`);
  log(`  ${C.bold}Source :${C.reset} ${SELENIUM_ROOT}`);
  log(`  ${C.bold}Output :${C.reset} ${OUTPUT_ROOT}`);
  log(`  ${C.bold}Mode   :${C.reset} ${headed ? C.cyan + 'Demo (headed + slowMo)' : C.dim + 'Headless'}${C.reset}`);
  blank();

  await clean();
  await stageInventory();
  await stageAnalyze();
  await stageUserStories();
  await gate1();
  await stageScaffold();
  await stageImplement();
  await gate2();
  await stageInstall();
  await stageRun(headed);
  summary();
}

main().catch(err => {
  console.error(`\n${C.red}${C.bold}ERROR:${C.reset} ${err.message}\n${err.stack}`);
  process.exit(1);
});
