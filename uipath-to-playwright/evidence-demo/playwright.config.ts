import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['line']],
  use: {
    trace: 'on',
    screenshot: 'on',
  },
});
