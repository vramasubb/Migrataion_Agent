import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';
import createSalesOrderData from '../../test-data/create-sales-order-data.json';

export class CreateSalesOrderPage {
  private readonly wnd0UsrCtxtVbakAuartLocator: Locator;
  private readonly salesOrganizationLocator: Locator;
  private readonly wnd0UsrCtxtVbakVtwegLocator: Locator;
  private readonly wnd0UsrCtxtVbakSpartLocator: Locator;
  private readonly iframeLocator: Locator;
  private readonly soldToPartyLocator: Locator;
  private readonly custReferenceLocator: Locator;
  private readonly wnd0SbarMsgLocator: Locator;
  constructor(readonly page: Page) {
    this.wnd0UsrCtxtVbakAuartLocator = page.locator('#wnd[0]/usr/ctxtVBAK-AUART');
    this.salesOrganizationLocator = page.locator('text=Sales Organization');
    this.wnd0UsrCtxtVbakVtwegLocator = page.locator('#wnd[0]/usr/ctxtVBAK-VTWEG');
    this.wnd0UsrCtxtVbakSpartLocator = page.locator('#wnd[0]/usr/ctxtVBAK-SPART');
    this.iframeLocator = page.locator('IFRAME');
    this.soldToPartyLocator = page.locator('text=Sold-to Party');
    this.custReferenceLocator = page.locator('text=Cust. Reference');
    this.wnd0SbarMsgLocator = page.locator('#wnd[0]/sbar_msg');
  }

  async createSalesOrder(): Promise<void> {
    const page = this.page;
      let DistChannel = '';
      let Division = '';
      let SalesOrg = '';
      let OrderType = '';
      let SoldTo = '';
      let CustomerRef = '';
      let Material = '';
      let Quantity = '';
      let dt_DataFromExcel = undefined;
      let SalesOrdSuccessMsg = '';
      let SalesOrderNo = '';
      let TestID = '';
      dt_DataFromExcel = createSalesOrderData.map((row) => ({ ...row }));
      OrderType = String(dt_DataFromExcel[0]['OrderType']);
      SalesOrg = String(dt_DataFromExcel[0]['SalesOrg']);
      DistChannel = String(dt_DataFromExcel[0]['DistChannel']);
      Division = String(dt_DataFromExcel[0]['Division']);
      SoldTo = String(dt_DataFromExcel[0]['SoldTo']);
      CustomerRef = String(dt_DataFromExcel[0]['CustomerRef']);
      Material = String(dt_DataFromExcel[0]['Material']);
      Quantity = String(dt_DataFromExcel[0]['Quantity']);
      await this.wnd0UsrCtxtVbakAuartLocator.fill(OrderType);
      await this.salesOrganizationLocator.fill(SalesOrg);
      await this.wnd0UsrCtxtVbakVtwegLocator.fill(DistChannel);
      await this.wnd0UsrCtxtVbakSpartLocator.fill(Division);
      console.log('[STEP] ' + 'Enter Initial details' + ': ' + "Order Type: "+OrderType+", Sales Org: "+SalesOrg+", Distribution Channel: "+DistChannel+", Division: "+Division);
      await this.iframeLocator.click();
      console.log('[STEP] ' + 'Click on Continue' + ': ' + 'Continue button clicked');
      await this.soldToPartyLocator.fill(SoldTo);
      await this.custReferenceLocator.fill(CustomerRef);
      await page.mouse.wheel(0, 300);
      await this.iframeLocator.fill(Material);
      await this.iframeLocator.fill(Quantity);
      console.log('[STEP] ' + 'Enter details in Overview screen' + ': ' + "Sold To: "+SoldTo+", Customer Reference: "+CustomerRef+", Material: "+Material+", Quantity: "+Quantity);
      await this.iframeLocator.click();
      console.log('[STEP] ' + 'Click on Save' + ': ' + 'Save button clicked');
      if (await this.wnd0SbarMsgLocator.isVisible()) {
        SalesOrdSuccessMsg = await this.wnd0SbarMsgLocator.innerText();
        SalesOrderNo = (SalesOrdSuccessMsg.match(/(\d{8})/) ?? [''])[0];
        dt_DataFromExcel[0]['SalesOrderNo'] = SalesOrderNo;
        console.log('[STEP] ' + 'Validate sales order created' + ': ' + "Sales order created: "+SalesOrderNo);
      } else {
        console.log('[STEP] ' + 'Validate sales order created' + ': ' + 'Sales order not created');
      }
  }
}
