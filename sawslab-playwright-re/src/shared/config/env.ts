// Shared environment config — reads from .env (loaded by playwright.config.ts via dotenv)
export const env = {
  webBaseUrl:  process.env.WEB_BASE_URL  ?? 'https://www.saucedemo.com',
  apiBaseUrl:  process.env.API_BASE_URL  ?? 'https://jsonplaceholder.typicode.com',
  standardUser: process.env.STANDARD_USER ?? 'standard_user',
  standardPass: process.env.STANDARD_PASS ?? 'secret_sauce',
  lockedUser:  process.env.LOCKED_USER   ?? 'locked_out_user',
};
