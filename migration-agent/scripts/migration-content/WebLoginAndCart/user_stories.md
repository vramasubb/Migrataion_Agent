# User Stories — Web: SauceDemo Login and Shopping Cart

**Stage:** 2 — Generate User Stories  
**Derived from:** `analysis/WebLoginAndCart/analysis.md`  
**Status:** ✅ Approved (Gate 1)

---

## US-WEB-01 · Successful Login

**As a** registered SauceDemo customer  
**I want to** log in with my username and password  
**So that** I can access the product catalogue and make purchases

### Acceptance Criteria

- **AC-1.1** Given I am on the login page, when I enter a valid username and password and click Login, then I am redirected to the Products page.
- **AC-1.2** The Products page heading must display the text "Products".

### Test Tags: `@smoke`, `@positive`

---

## US-WEB-02 · Login Rejected — Invalid Credentials

**As a** security-conscious system  
**I want to** reject logins with unrecognised username/password combinations  
**So that** unauthorised users cannot access the store

### Acceptance Criteria

- **AC-2.1** Given I am on the login page, when I enter an unrecognised username or wrong password, then an error banner is displayed.
- **AC-2.2** The error text must contain "Username and password do not match" (case-insensitive).

### Test Tags: `@negative`

---

## US-WEB-03 · Login Rejected — Locked-Out User

**As a** system administrator  
**I want to** prevent locked-out users from logging in  
**So that** suspended accounts cannot access the store

### Acceptance Criteria

- **AC-3.1** Given I am on the login page, when a locked-out user enters valid credentials, then an error banner is displayed.
- **AC-3.2** The error text must contain "locked out" (case-insensitive).

### Test Tags: `@negative`

---

## US-WEB-04 · Add a Single Product to Cart

**As a** logged-in customer  
**I want to** add a product to my shopping cart  
**So that** I can purchase it later

### Acceptance Criteria

- **AC-4.1** Given I am on the Products page, when I click "Add to cart" for a named product, then the cart badge increments to 1.
- **AC-4.2** Products covered: `Sauce Labs Backpack`, `Sauce Labs Bike Light`, `Sauce Labs Bolt T-Shirt`.

### Test Tags: `@regression`

---

## US-WEB-05 · Add Multiple Products and Navigate to Cart

**As a** logged-in customer  
**I want to** add multiple products and open the cart  
**So that** I can review my selections before checkout

### Acceptance Criteria

- **AC-5.1** Given I am on the Products page, when I add two products to the cart, then the cart badge shows "2".
- **AC-5.2** When I click the cart icon, then I am navigated to the cart page (URL contains `cart.html`).

### Test Tags: `@regression`

---

## Traceability Matrix

| User Story | Acceptance Criteria | Selenium Scenario | Playwright Test |
|------------|--------------------|--------------------|-----------------|
| US-WEB-01 | AC-1.1, AC-1.2 | Successful login with valid credentials | `@smoke @positive Successful login…` |
| US-WEB-02 | AC-2.1, AC-2.2 | Login fails with invalid credentials | `@negative Login fails with invalid…` |
| US-WEB-03 | AC-3.1, AC-3.2 | Login fails for locked out user | `@negative Login fails for locked…` |
| US-WEB-04 | AC-4.1 | Add products to cart (Outline × 3) | `@regression Add "…" to cart` × 3 |
| US-WEB-05 | AC-5.1, AC-5.2 | Add multiple products and go to cart page | `@regression Add multiple products…` |
