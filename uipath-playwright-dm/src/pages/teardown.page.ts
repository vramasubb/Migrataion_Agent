import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

export class TeardownPage {
  constructor(readonly page: Page) {}

  async teardown(): Promise<void> {
    const page = this.page;
      // browser lifecycle managed by Playwright fixtures (was: kill process ''chrome.exe'')
  }
}
