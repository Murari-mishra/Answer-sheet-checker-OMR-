import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from '@playwright/test'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const reportDir = process.env.PLAYWRIGHT_REPORT_DIR ?? path.join(frontendDir, 'playwright-report')

export default defineConfig({
  testDir: './e2e',
  timeout: 20 * 60 * 1000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  reporter: [
    ['list'],
    ['html', { outputFolder: path.join(reportDir, 'html'), open: 'never' }],
  ],
  outputDir: path.join(reportDir, 'artifacts'),
  use: {
    baseURL: process.env.PLAYWRIGHT_APP_URL ?? 'http://127.0.0.1:5173',
    browserName: 'chromium',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
})
