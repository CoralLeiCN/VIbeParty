import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "combined.spec.ts",
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 120000,
  use: {
    baseURL: process.env.PORTAL_URL || "http://localhost:8000",
    trace: "retain-on-failure",
  },
});
