import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';
import { env } from '../config/env';

export class SetupPage {
  constructor(readonly page: Page) {}

  async setup(): Promise<void> {
    const page = this.page;
      // browser lifecycle managed by Playwright fixtures (was: kill process ''chrome.exe'')
      let FolderPath = 'C:\\UiPathPOC';
      let FilePath = `${env.folderPath}/${env.testcaseName + ".xlsx"}`;
      // reporting handled by the Playwright HTML reporter (was: CreateReport 'GlobalVariablesNamespace.GlobalVariables.TestcaseName')
      // reporting handled by the Playwright HTML reporter (was: StartSuite ''Iteration 1'')
  }
}
