import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

export class ReadComponentTestDataPage {
  constructor(readonly page: Page) {}

  async readComponentTestData({ in_SheetName }: { in_SheetName: string }): Promise<void> {
    const page = this.page;
      console.log("Reading data from sheet : "+ in_SheetName);
      // TODO: load test data from 'TestData\Input.xlsx' sheet in_SheetName into a TypeScript fixture
      console.log("Data uploaded succesfully to data table");
  }
}
