import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

export class NavigateToApplicationPage {
  private readonly userActionsMenuHeaderButtonLocator: Locator;
  private readonly sapUshellUserActionsMenuPopoverLocator: Locator;
  private readonly sapMenuButtonLocator: Locator;
  private readonly appFinderSearchLocator: Locator;
  private readonly sapUshellUiAppfinderAppBoxLocator: Locator;
  constructor(readonly page: Page) {
    this.userActionsMenuHeaderButtonLocator = page.locator('#userActionsMenuHeaderButton');
    this.sapUshellUserActionsMenuPopoverLocator = page.locator('#sapUshellUserActionsMenuPopover-3-openCatalogBtn');
    this.sapMenuButtonLocator = page.locator('#sapMenu-button');
    this.appFinderSearchLocator = page.locator('#appFinderSearch');
    this.sapUshellUiAppfinderAppBoxLocator = page.locator('.sap.ushell.ui.appfinder.AppBoxInternal');
  }

  async navigateToApplication({ in_AppSubTitle, in_AppTitle }: { in_AppSubTitle: string; in_AppTitle: string }): Promise<void> {
    const page = this.page;
      let Title = '';
      let SubTitle = '';
      let TestID = '';
      Title = in_AppTitle;
      SubTitle = in_AppSubTitle;
      await this.userActionsMenuHeaderButtonLocator.click();
      await this.sapUshellUserActionsMenuPopoverLocator.click();
      await this.sapMenuButtonLocator.click();
      await this.appFinderSearchLocator.fill(`${Title}[k(enter)]`);
      await this.sapUshellUiAppfinderAppBoxLocator.click();
  }
}
