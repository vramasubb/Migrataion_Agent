import { test, expect } from '@playwright/test';

test.describe('LoginFlow', () => {
  test('migrated UiPath flow', async ({ page }) => {
  let isProductsVisible = undefined;
  await page.goto('https://www.saucedemo.com');
  await page.locator('#user-name').fill('standard_user');
  await page.screenshot({ path: 'evidence/after/loginflow/01-fill.png' });
  await page.locator('#password').fill('secret_sauce');
  await page.screenshot({ path: 'evidence/after/loginflow/02-fill.png' });
  await page.locator('#login-button').click();
  await page.screenshot({ path: 'evidence/after/loginflow/03-click.png' });
  isProductsVisible = await page.locator('text=Products').isVisible();
  expect(isProductsVisible).toBeTruthy();
  });
});
