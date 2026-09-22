import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';
import { env } from '../config/env';

export class LoginPage {
  private readonly okLocator: Locator;
  private readonly usernameFieldInnerLocator: Locator;
  private readonly passwordFieldInnerLocator: Locator;
  private readonly loginLinkLocator: Locator;
  private readonly userActionsMenuHeaderButtonLocator: Locator;
  constructor(readonly page: Page) {
    this.okLocator = page.locator('text=OK');
    this.usernameFieldInnerLocator = page.locator('#USERNAME_FIELD-inner');
    this.passwordFieldInnerLocator = page.locator('#PASSWORD_FIELD-inner');
    this.loginLinkLocator = page.locator('#LOGIN_LINK');
    this.userActionsMenuHeaderButtonLocator = page.locator('#userActionsMenuHeaderButton');
  }

  async login(): Promise<void> {
    const page = this.page;
      let Username = '';
      let URL = '';
      let Password = '';
      let TestID = '';
      URL = process.env.UIPATH_ASSET_D22_URL ?? '';
      Username = process.env.UIPATH_USERNAME ?? ''; Password = process.env.UIPATH_PASSWORD ?? '';
      await this.okLocator.click();
      await this.usernameFieldInnerLocator.fill(Username);
      await this.passwordFieldInnerLocator.fill(Password);
      console.log('[STEP] ' + 'Enter Username and Password' + ': ' + 'Username and Password entered');
      await this.loginLinkLocator.click();
      if (await this.userActionsMenuHeaderButtonLocator.isVisible()) {
        console.log("Login Successful");
        console.log('[STEP] ' + 'Validate Login is successful' + ': ' + 'Login successful');
      } else {
        console.log("Login Failed");
        console.log('[STEP] ' + 'Validate Login is successful' + ': ' + 'Login Failed');
      }
  }
}
