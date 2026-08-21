# Locator Map — Web: SauceDemo Login and Shopping Cart

**Stage:** 1 — Analyze & Extract  
**Source:** `pages/LoginPage.java`, `pages/InventoryPage.java`

---

## LoginPage Locators

| Element | Selenium (Java) | Type | Playwright equivalent | Confidence |
|---------|-----------------|------|-----------------------|------------|
| Username input | `By.id("user-name")` | ID | `#user-name` | ✅ High |
| Password input | `By.id("password")` | ID | `#password` | ✅ High |
| Login button | `By.id("login-button")` | ID | `#login-button` | ✅ High |
| Error banner | `By.cssSelector("[data-test='error']")` | CSS attr | `[data-test="error"]` | ✅ High |

## InventoryPage Locators

| Element | Selenium (Java) | Type | Playwright equivalent | Confidence |
|---------|-----------------|------|-----------------------|------------|
| Page title | `By.className("title")` | Class | `.title` | ✅ High |
| Product cards | `By.className("inventory_item")` | Class | `.inventory_item` | ✅ High |
| Product name (child) | `By.className("inventory_item_name")` | Class | `.inventory_item_name` | ✅ High |
| Cart badge | `By.className("shopping_cart_badge")` | Class | `.shopping_cart_badge` | ✅ High |
| Cart link | `By.className("shopping_cart_link")` | Class | `.shopping_cart_link` | ✅ High |
| Add-to-cart buttons | `By.cssSelector("button[id^='add-to-cart']")` | CSS attr-prefix | `button` (scoped to item) | ✅ High |

## CartPage Locators

| Element | Detection method | Playwright check |
|---------|-----------------|-----------------|
| Cart page URL | `driver.getCurrentUrl().contains("cart.html")` | `page.url()` contains `cart.html` |

---

## Locator Quality Notes

- All locators use stable `id` or `data-test` attributes → **no fragile XPath**.
- Class selectors (`.title`, `.inventory_item`) are SauceDemo-specific — stable for this target.
- `button[id^=add-to-cart]` pattern works but scoping to the parent `.inventory_item` is cleaner in Playwright.
