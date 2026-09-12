import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  timeout: 90000,
  workers: 1,
  reporter: "list",
  outputDir: "../../../../../.local/prompt-royale-browser",
  use: {
    baseURL: process.env.ROYALE_URL || "http://localhost:5175",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
