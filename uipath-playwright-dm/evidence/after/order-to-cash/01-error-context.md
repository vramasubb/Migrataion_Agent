# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: order-to-cash.spec.ts >> OrderToCash >> OrderToCash
- Location: tests\order-to-cash.spec.ts:10:7

# Error details

```
Error: page.goto: net::ERR_NAME_NOT_RESOLVED at https://usawsconl0576.us.deloitte.com:8100/sap/bc/ui2/flp
Call log:
  - navigating to "https://usawsconl0576.us.deloitte.com:8100/sap/bc/ui2/flp", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { env } from '../src/config/env';
  3  | import { CreateOBDPage } from '../src/pages/create-obd.page';
  4  | import { CreateSalesOrderPage } from '../src/pages/create-sales-order.page';
  5  | import { LoginPage } from '../src/pages/login.page';
  6  | import { LogoutPage } from '../src/pages/logout.page';
  7  | import { NavigateToApplicationPage } from '../src/pages/navigate-to-application.page';
  8  | 
  9  | test.describe('OrderToCash', () => {
  10 |   test('OrderToCash', async ({ page }) => {
> 11 |     await page.goto(env.webBaseUrl);
     |                ^ Error: page.goto: net::ERR_NAME_NOT_RESOLVED at https://usawsconl0576.us.deloitte.com:8100/sap/bc/ui2/flp
  12 |     const createOBDPage = new CreateOBDPage(page);
  13 |     const createSalesOrderPage = new CreateSalesOrderPage(page);
  14 |     const loginPage = new LoginPage(page);
  15 |     const logoutPage = new LogoutPage(page);
  16 |     const navigateToApplicationPage = new NavigateToApplicationPage(page);
  17 |   await loginPage.login();
  18 |   await navigateToApplicationPage.navigateToApplication({ in_AppSubTitle: 'VA01', in_AppTitle: 'Create Sales Orders' });
  19 |   await createSalesOrderPage.createSalesOrder();
  20 |   await navigateToApplicationPage.navigateToApplication({ in_AppSubTitle: 'With Order Reference', in_AppTitle: 'Create Outbound Delivery' });
  21 |   await createOBDPage.createOBD({ in_sheetName: 'CreateDelivery' });
  22 |   await logoutPage.logout();
  23 |   });
  24 | });
  25 | 
```