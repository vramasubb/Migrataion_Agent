from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from mapper_loader import MapperLoader
from token_usage import build_token_report, print_token_summary


@dataclass
class Scenario:
    name: str
    tags: list[str]
    steps: list[str] = field(default_factory=list)
    examples: list[dict[str, str]] = field(default_factory=list)


def read_properties(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def parse_feature(path: Path) -> tuple[str, list[str], list[Scenario]]:
    feature_name = path.stem
    background: list[str] = []
    scenarios: list[Scenario] = []
    pending_tags: list[str] = []
    current: Scenario | None = None
    in_background = False
    in_examples = False
    example_headers: list[str] = []
    doc_lines: list[str] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if doc_lines is not None:
            if line == '"""':
                if current is None:
                    raise ValueError(f"Doc string outside scenario: {path}")
                current.steps[-1] += "\n" + "\n".join(doc_lines)
                doc_lines = None
            else:
                doc_lines.append(raw_line.strip())
            continue
        if line == '"""':
            doc_lines = []
        elif not line or line.startswith("#"):
            continue
        elif line.startswith("@"):
            pending_tags = line.split()
        elif line.startswith("Feature:"):
            feature_name = line.split(":", 1)[1].strip()
        elif line == "Background:":
            in_background = True
            current = None
        elif line.startswith(("Scenario:", "Scenario Outline:")):
            current = Scenario(line.split(":", 1)[1].strip(), pending_tags.copy())
            scenarios.append(current)
            pending_tags.clear()
            in_background = False
            in_examples = False
        elif line == "Examples:":
            in_examples = True
        elif in_examples and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not example_headers:
                example_headers = cells
            elif current:
                current.examples.append(dict(zip(example_headers, cells)))
        elif re.match(r"^(Given|When|Then|And|But)\s+", line):
            step = re.sub(r"^(Given|When|Then|And|But)\s+", "", line)
            if in_background:
                background.append(step)
            elif current:
                current.steps.append(step)

    expanded: list[Scenario] = []
    for scenario in scenarios:
        rows = scenario.examples or [{}]
        for row in rows:
            replace = lambda text: re.sub(r"<([^>]+)>", lambda match: row[match.group(1)], text)
            suffix = f" [{', '.join(row.values())}]" if row else ""
            expanded.append(
                Scenario(replace(scenario.name) + suffix, scenario.tags, [replace(step) for step in background + scenario.steps])
            )
    return feature_name, background, expanded


def quoted(step: str) -> list[str]:
    return re.findall(r'"([^"]*)"', step)


def ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def render_web_step(step: str) -> list[str]:
    values = quoted(step)
    if step == "I am on the SauceDemo login page":
        return ["await loginPage.open();"]
    if step.startswith("I log in with username ") and len(values) == 2:
        return [f"await loginPage.login({ts_string(values[0])}, {ts_string(values[1])});"]
    if step == "I should be redirected to the products page":
        return ["await expect(inventoryPage.pageTitle).toBeVisible();"]
    if step.startswith("the page title should be ") and values:
        return [f"await expect(inventoryPage.pageTitle).toHaveText({ts_string(values[0])});"]
    if step.startswith("I should see an error message containing ") and values:
        return ["await expect(loginPage.errorMessage).toBeVisible();", f"await expect(loginPage.errorMessage).toContainText({ts_string(values[0])});"]
    if step.startswith("I add ") and values:
        return [f"await inventoryPage.addProductToCartByName({ts_string(values[0])});"]
    if step.startswith("the cart badge should show ") and values:
        return [f"await expect(inventoryPage.cartBadge).toHaveText({ts_string(values[0])});"]
    if step == "I open the cart page":
        return ["await inventoryPage.goToCart();"]
    if step == "I should be on the cart page":
        return ["await expect(page).toHaveURL(/cart\\.html$/);"]
    raise ValueError(f"Unsupported web feature step: {step}")


def render_api_step(step: str) -> list[str]:
    values = quoted(step)
    request_match = re.match(r"I send a (GET|POST|PUT|PATCH|DELETE) request to ", step)
    if request_match and values:
        method = request_match.group(1).lower()
        body = step.split("\n", 1)[1] if "\n" in step else None
        options = f", {{ data: {body} }}" if body else ""
        return [f"response = await request.{method}({ts_string(values[0])}{options});", "body = await response.json().catch(() => null);"]
    status_match = re.match(r"the response status code should be (\d+)$", step)
    if status_match:
        return [f"expect(response.status()).toBe({status_match.group(1)});"]
    size_match = re.match(r"the response array size should be (\d+)$", step)
    if size_match:
        return ["expect(Array.isArray(body)).toBe(true);", f"expect(body).toHaveLength({size_match.group(1)});"]
    if step.startswith("the response field ") and len(values) == 2:
        return [f"expect(String(getPath(body, {ts_string(values[0])}))).toBe({ts_string(values[1])});"]
    if step.startswith("the response should contain field ") and values:
        return [f"expect(getPath(body, {ts_string(values[0])})).not.toBeNull();", f"expect(getPath(body, {ts_string(values[0])})).toBeDefined();"]
    if step.startswith("the response array ") and values:
        path = values[0]
        target = "body" if not path else f"getPath(body, {ts_string(path)})"
        return [f"expect(Array.isArray({target})).toBe(true);", f"expect({target}.length).toBeGreaterThan(0);"]
    if step.startswith("every item in the response array should have field ") and len(values) == 2:
        return ["expect(Array.isArray(body)).toBe(true);", f"for (const item of body) expect(String(getPath(item, {ts_string(values[0])}))).toBe({ts_string(values[1])});"]
    raise ValueError(f"Unsupported API feature step: {step}")


def render_spec(feature_name: str, scenarios: list[Scenario], kind: str) -> str:
    tests: list[str] = []
    for scenario in scenarios:
        tags = " ".join(scenario.tags)
        title = f"{tags} {scenario.name}".strip()
        setup = (
            "    const loginPage = new LoginPage(page);\n    const inventoryPage = new InventoryPage(page);"
            if kind == "web"
            else "    let response!: APIResponse;\n    let body: any;"
        )
        statements: list[str] = []
        for step in scenario.steps:
            statements.extend(render_web_step(step) if kind == "web" else render_api_step(step))
        body = "\n".join(f"    {statement}" for statement in statements)
        fixture = "{ page }" if kind == "web" else "{ request }"
        tests.append(f"  test({ts_string(title)}, async ({fixture}) => {{\n{setup}\n{body}\n  }});")

    imports = (
        "import { test, expect } from '@playwright/test';\nimport { LoginPage } from '../src/pages/login.page';\nimport { InventoryPage } from '../src/pages/inventory.page';"
        if kind == "web"
        else "import { test, expect, type APIResponse } from '@playwright/test';\n\nfunction getPath(value: any, path: string): any {\n  if (!path || path === '$') return value;\n  return path.replace(/\\[(\\d+)\\]/g, '.$1').split('.').filter(Boolean).reduce((current, key) => current?.[key], value);\n}"
    )
    return f"{imports}\n\ntest.describe({ts_string(feature_name)}, () => {{\n" + "\n\n".join(tests) + "\n});\n"


def write_project(
    source: Path,
    output: Path,
    agent_input_tokens: int = 0,
    agent_output_tokens: int = 0,
    model: str = "claude-sonnet",
    input_rate: float = 3.0,
    output_rate: float = 15.0,
) -> dict[str, object]:
    resources = source / "src" / "test" / "resources"
    config = read_properties(resources / "config.properties")
    feature_dir = resources / "features"
    parsed = {path.stem: parse_feature(path) for path in sorted(feature_dir.glob("*.feature"))}
    web = next(value for key, value in parsed.items() if "web" in key.lower())
    api = next(value for key, value in parsed.items() if "api" in key.lower())

    files = {
        "package.json": json.dumps({"name": "sawslab-playwright-python-migration", "version": "1.0.0", "private": True, "scripts": {"test": "playwright test", "typecheck": "tsc --noEmit"}, "devDependencies": {"@playwright/test": "^1.55.0", "@types/node": "^24.0.0", "typescript": "^5.9.0"}}, indent=2) + "\n",
        "tsconfig.json": json.dumps({"compilerOptions": {"target": "ES2022", "module": "CommonJS", "moduleResolution": "Node", "strict": True, "noEmit": True, "types": ["node"]}, "include": ["src/**/*.ts", "tests/**/*.ts", "playwright.config.ts"]}, indent=2) + "\n",
        "playwright.config.ts": "import { defineConfig, devices } from '@playwright/test';\n\nexport default defineConfig({\n  testDir: './tests',\n  fullyParallel: true,\n  retries: process.env.CI ? 2 : 0,\n  reporter: [['html', { open: 'never' }], ['line']],\n  use: { trace: 'on-first-retry', screenshot: 'only-on-failure' },\n  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],\n});\n",
        "src/config/env.ts": f"export const env = {{\n  webBaseUrl: process.env.WEB_BASE_URL ?? {ts_string(config['web.base.url'])},\n  apiBaseUrl: process.env.API_BASE_URL ?? {ts_string(config['api.base.url'])},\n}};\n",
        "src/pages/login.page.ts": "import { type Locator, type Page } from '@playwright/test';\nimport { env } from '../config/env';\n\nexport class LoginPage {\n  readonly usernameField: Locator;\n  readonly passwordField: Locator;\n  readonly loginButton: Locator;\n  readonly errorMessage: Locator;\n  constructor(readonly page: Page) {\n    this.usernameField = page.locator('#user-name');\n    this.passwordField = page.locator('#password');\n    this.loginButton = page.locator('#login-button');\n    this.errorMessage = page.locator('[data-test=\"error\"]');\n  }\n  async open() { await this.page.goto(env.webBaseUrl); }\n  async login(username: string, password: string) { await this.usernameField.fill(username); await this.passwordField.fill(password); await this.loginButton.click(); }\n}\n",
        "src/pages/inventory.page.ts": "import { type Locator, type Page } from '@playwright/test';\n\nexport class InventoryPage {\n  readonly pageTitle: Locator;\n  readonly inventoryItems: Locator;\n  readonly cartBadge: Locator;\n  readonly cartLink: Locator;\n  constructor(readonly page: Page) {\n    this.pageTitle = page.locator('.title');\n    this.inventoryItems = page.locator('.inventory_item');\n    this.cartBadge = page.locator('.shopping_cart_badge');\n    this.cartLink = page.locator('.shopping_cart_link');\n  }\n  async addProductToCartByName(name: string) { const item = this.inventoryItems.filter({ hasText: name }); await item.locator('button').click(); }\n  async goToCart() { await this.cartLink.click(); }\n}\n",
        "tests/web-login-and-cart.spec.ts": render_spec(web[0], web[2], "web"),
        "tests/api-posts.spec.ts": render_spec(api[0], api[2], "api").replace("request.get(\"", "request.get(env.apiBaseUrl + \"").replace("request.post(\"", "request.post(env.apiBaseUrl + \"").replace("request.put(\"", "request.put(env.apiBaseUrl + \"").replace("request.patch(\"", "request.patch(env.apiBaseUrl + \"").replace("request.delete(\"", "request.delete(env.apiBaseUrl + \"").replace("import { test, expect, type APIResponse } from '@playwright/test';", "import { test, expect, type APIResponse } from '@playwright/test';\nimport { env } from '../src/config/env';"),
    }
    for relative, content in files.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    token_usage = build_token_report(
        source.rglob("*"),
        (output / relative for relative in files),
        agent_input_tokens,
        agent_output_tokens,
        model,
        input_rate,
        output_rate,
    )
    report: dict[str, object] = {
        "source": str(source),
        "features": len(parsed),
        "webTests": len(web[2]),
        "apiTests": len(api[2]),
        "unsupportedSteps": 0,
        "converter": "Python only; no agent",
        "tokenUsage": token_usage,
    }
    (output / "migration-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a Selenium Java Cucumber project to Playwright TypeScript")
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--client")
    parser.add_argument("--agent-input-tokens", type=int, default=0, help="Actual input tokens reported for optional agent setup help")
    parser.add_argument("--agent-output-tokens", type=int, default=0, help="Actual output tokens reported for optional agent setup help")
    parser.add_argument("--model", default="claude-sonnet", help="Model label used for optional agent assistance")
    parser.add_argument("--input-rate", type=float, default=3.0, help="Agent input price in USD per million tokens")
    parser.add_argument("--output-rate", type=float, default=15.0, help="Agent output price in USD per million tokens")
    args = parser.parse_args()
    loader = MapperLoader(client=args.client)
    errors = loader.validate()
    if errors:
        raise SystemExit("Mapper validation failed:\n- " + "\n- ".join(errors))
    report = write_project(
        args.source.resolve(),
        args.output.resolve(),
        args.agent_input_tokens,
        args.agent_output_tokens,
        args.model,
        args.input_rate,
        args.output_rate,
    )
    print(f"Playwright project generated: {args.output.resolve()}")
    print(f"Migration report: {(args.output.resolve() / 'migration-report.json')}")
    print_token_summary(report["tokenUsage"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())