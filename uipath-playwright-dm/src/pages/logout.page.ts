import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

export class LogoutPage {
  private readonly avatarLocator: Locator;
  private readonly signOutLocator: Locator;
  private readonly areYouSureYouWantToLocator: Locator;
  private readonly okLocator: Locator;
  constructor(readonly page: Page) {
    this.avatarLocator = page.locator('text=Avatar');
    this.signOutLocator = page.locator('text=Sign Out');
    this.areYouSureYouWantToLocator = page.locator('text=Are you sure you want to sign out?');
    this.okLocator = page.locator('text=OK');
  }

  async logout(): Promise<void> {
    const page = this.page;
      let TestID = '';
      if (await this.avatarLocator.isVisible()) {
        await this.avatarLocator.click();
        console.log("Profile icon clicked");
        await this.signOutLocator.click();
        console.log("Signout option clicked");
      } else {
        console.log("Profile Icon not available");
      }
      if (await this.areYouSureYouWantToLocator.isVisible()) {
        await this.okLocator.click();
        console.log('[STEP] ' + 'Validate Logout is successful' + ': ' + 'Logout successful');
        console.log("Ok Button clicked");
      } else {
        console.log("Logout popup not appeared");
      }
  }
}
