export const env = {
  webBaseUrl: process.env.WEB_BASE_URL ?? "https://usawsconl0576.us.deloitte.com:8100/sap/bc/ui2/flp",
  username: process.env.UIPATH_USERNAME ?? '',
  password: process.env.UIPATH_PASSWORD ?? '',
  // Mirrors the UiPath project's GlobalVariablesNamespace.GlobalVariables.* framework values.
  folderPath: process.env.REPORTS_FOLDER_PATH ?? './reports',
  testcaseName: process.env.TESTCASE_NAME ?? 'OrderToCash',
};
