import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';
import createObdData from '../../test-data/create-obd-data.json';

export class CreateOBDPage {
  private readonly shippingPointLocator: Locator;
  private readonly orderLocator: Locator;
  private readonly continueLocator: Locator;
  private readonly shellAppTitleButtonLocator: Locator;
  private readonly saveLocator: Locator;
  private readonly successMessageBarOutboundDeliveryHasLocator: Locator;
  constructor(readonly page: Page) {
    this.shippingPointLocator = page.locator('text=Shipping Point');
    this.orderLocator = page.locator('text=Order');
    this.continueLocator = page.locator('text=Continue');
    this.shellAppTitleButtonLocator = page.locator('[data-testid="shellAppTitle-button"]');
    this.saveLocator = page.locator('text=Save');
    this.successMessageBarOutboundDeliveryHasLocator = page.locator('text=Success Message Bar Outbound Delivery * has been saved');
  }

  async createOBD({ in_sheetName }: { in_sheetName: string }): Promise<void> {
    const page = this.page;
      let Out_Delivery = '';
      let variable1 = '';
      let in_ShippingPt = 'MDH1';
      let in_Order = '70000971';
      let TestID = '';
      let in_ExcelFilePath = undefined;
      let out_Datatable = undefined;
      out_Datatable = createObdData.map((row) => ({ ...row }));
      for (const CurrentRow of out_Datatable) {
        in_ShippingPt = String(CurrentRow['ShippingPoint']);
        in_Order = String(CurrentRow['OrderNumber']);
      }
      await this.shippingPointLocator.fill(in_ShippingPt);
      console.log("Shipping Point entered : "+in_ShippingPt);
      await this.orderLocator.fill(in_Order);
      console.log("Order entered : "+in_Order);
      console.log('[STEP] ' + 'Enter initial details' + ': ' + "Shipping Point: "+in_ShippingPt+", Sales order number: "+in_Order);
      await this.continueLocator.click();
      console.log('[STEP] ' + 'Click on Continue' + ': ' + 'Continue button clicked');
      console.log("Continue Button Clicked");
      if (await this.shellAppTitleButtonLocator.isVisible()) {
        await this.saveLocator.click();
        console.log('[STEP] ' + 'Click on Save' + ': ' + 'Save button clicked');
        Out_Delivery = await this.successMessageBarOutboundDeliveryHasLocator.innerText();
        Out_Delivery = (Out_Delivery.match(/\d+/) ?? [''])[0];
        console.log('[STEP] ' + 'Validate Outbound delivery created' + ': ' + "Outbound delivery created: "+Out_Delivery);
        console.log("OBD Created - "+Out_Delivery);
      } else {
        console.log("Outbound Delivery create Screen not visible");
        console.log('[STEP] ' + 'Validate Outbound delivery created' + ': ' + 'Outbound delivery not created');
      }
  }
}
