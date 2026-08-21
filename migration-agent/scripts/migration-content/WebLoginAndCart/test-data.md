# Test Data — Web: SauceDemo Login and Shopping Cart

**Stage:** 1 — Analyze & Extract  
**Source:** `features/web_login_and_cart.feature` (inline Examples tables)

---

## Credentials

| Role | Username | Password | Expected outcome |
|------|----------|----------|-----------------|
| Standard user | `standard_user` | `secret_sauce` | Login succeeds → Products page |
| Locked-out user | `locked_out_user` | `secret_sauce` | Error: "locked out" |
| Invalid user | `invalid_user` | `wrong_password` | Error: "Username and password do not match" |

> Source: SauceDemo public test credentials. Safe to store in `.env` / `.env.example`.

---

## Products (Scenario Outline Examples)

| # | Product name | Used in |
|---|-------------|---------|
| 1 | `Sauce Labs Backpack` | Cart badge count (1 item) |
| 2 | `Sauce Labs Bike Light` | Cart badge count (1 item) |
| 3 | `Sauce Labs Bolt T-Shirt` | Cart badge count (1 item) |
| 1+2 | `Sauce Labs Backpack` + `Sauce Labs Bike Light` | Multiple items (badge = 2) + cart page nav |

---

## Parameterisation Strategy

The Selenium Scenario Outline maps to a **`for...of` loop** in Playwright (no framework-level parameterisation needed):

```typescript
const cartProducts = ['Sauce Labs Backpack', 'Sauce Labs Bike Light', 'Sauce Labs Bolt T-Shirt'];
for (const product of cartProducts) {
  test(`Add "${product}" to cart`, async ({ page }) => { ... });
}
```

This preserves individual test names and preserves Outline traceability.
