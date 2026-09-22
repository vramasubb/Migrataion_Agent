import { test, expect } from '@playwright/test';
import { env } from '../src/config/env';
import { CreateOBDPage } from '../src/pages/create-obd.page';
import { CreateSalesOrderPage } from '../src/pages/create-sales-order.page';
import { LoginPage } from '../src/pages/login.page';
import { LogoutPage } from '../src/pages/logout.page';
import { NavigateToApplicationPage } from '../src/pages/navigate-to-application.page';

test.describe('OrderToCash', () => {
  test('OrderToCash', async ({ page }) => {
    await page.goto(env.webBaseUrl);
    const createOBDPage = new CreateOBDPage(page);
    const createSalesOrderPage = new CreateSalesOrderPage(page);
    const loginPage = new LoginPage(page);
    const logoutPage = new LogoutPage(page);
    const navigateToApplicationPage = new NavigateToApplicationPage(page);
  await loginPage.login();
  await navigateToApplicationPage.navigateToApplication({ in_AppSubTitle: 'VA01', in_AppTitle: 'Create Sales Orders' });
  await createSalesOrderPage.createSalesOrder();
  await navigateToApplicationPage.navigateToApplication({ in_AppSubTitle: 'With Order Reference', in_AppTitle: 'Create Outbound Delivery' });
  await createOBDPage.createOBD({ in_sheetName: 'CreateDelivery' });
  await logoutPage.logout();
  });
});
