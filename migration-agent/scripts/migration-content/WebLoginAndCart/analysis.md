# Feature Analysis — Web: SauceDemo Login and Shopping Cart

**Stage:** 1 — Analyze & Extract  
**Source file:** `src/test/resources/features/web_login_and_cart.feature`  
**Step defs:** `stepdefinitions/WebSteps.java`  
**Page objects:** `pages/LoginPage.java`, `pages/InventoryPage.java`  
**Generated:** Stage 1 of migration pipeline

---

## Test Intent Summary

This feature validates the SauceDemo e-commerce application's authentication flow and shopping-cart
functionality. It covers three login outcomes and three cart-management variations.

---

## Scenario Inventory

| # | Scenario | Tags | Type | Expanded Tests |
|---|----------|------|------|----------------|
| 1 | Successful login with valid credentials | @smoke @positive | Happy path | 1 |
| 2 | Login fails with invalid credentials | @negative | Error handling | 1 |
| 3 | Login fails for locked out user | @negative | Error handling | 1 |
| 4 | Add products to cart and verify cart badge count | @regression | Outline × 3 rows | 3 |
| 5 | Add multiple products and go to cart page | @regression | Multi-step | 1 |
| **Total** | | | | **7 scenarios → 7 tests** |

> Scenario Outline (scenario 4) has 3 `Examples` rows → expands to 3 parameterised tests.  
> Total expanded test count: **7 tests**.

---

## Step Definition Mapping

| Cucumber step | Java method | Notes |
|---------------|-------------|-------|
| `I am on the SauceDemo login page` | `loginPage.open(ConfigReader.getWebBaseUrl())` | Navigates to BASE_URL |
| `I log in with username … and password …` | `loginPage.login(username, password)` | Fills + clicks |
| `I should be redirected to the products page` | `inventoryPage.isLoaded()` | Waits for `.title` visibility |
| `the page title should be …` | `inventoryPage.getPageTitleText()` | asserts text |
| `I should see an error message containing …` | `loginPage.isErrorDisplayed()` + `getErrorText()` | partial match |
| `I add … to the cart` | `inventoryPage.addProductToCartByName(name)` | Iterates items by name |
| `the cart badge should show … item` | `inventoryPage.getCartItemCount()` | reads `.shopping_cart_badge` |
| `I open the cart page` | `inventoryPage.goToCart()` | clicks `.shopping_cart_link` |
| `I should be on the cart page` | `driver.getCurrentUrl().contains("cart.html")` | URL assertion |

---

## Assertions Extracted

| Scenario | Assertion type | Expected value |
|----------|----------------|----------------|
| Successful login | URL / page element | Inventory page loaded |
| Successful login | Text | Page title == "Products" |
| Invalid credentials | Element visibility | Error banner visible |
| Invalid credentials | Text (partial, case-insensitive) | "Username and password do not match" |
| Locked out | Element visibility | Error banner visible |
| Locked out | Text (partial, case-insensitive) | "locked out" |
| Cart badge | Integer equality | Badge count == 1 (per product) |
| Multiple products | Integer equality | Badge count == 2 |
| Cart page | URL contains | "cart.html" |

---

## Test Data

| Field | Values used |
|-------|-------------|
| Valid username | `standard_user` |
| Valid password | `secret_sauce` |
| Invalid username | `invalid_user` |
| Invalid password | `wrong_password` |
| Locked-out username | `locked_out_user` |
| Products | `Sauce Labs Backpack`, `Sauce Labs Bike Light`, `Sauce Labs Bolt T-Shirt` |

---

## Migration Notes

- **No auth state needed** — SauceDemo credentials are well-known public test credentials.
- **Scenario Outline** → expand to parameterised `test.each`-style loop in Playwright.
- `addProductToCartByName` iterates DOM items by text match — same pattern works in Playwright.
- All waits in Java use `WebDriverWait(15s)` → map to Playwright's built-in auto-waiting.
- Selenium explicit waits → remove entirely (Playwright auto-waits on `fill`, `click`, etc.).
