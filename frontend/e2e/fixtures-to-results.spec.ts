import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const fixturesDir = process.env.PLAYWRIGHT_FIXTURES_DIR ?? path.resolve(frontendDir, '../../backend/tests/fixtures/sheets')
const reportDir = process.env.PLAYWRIGHT_REPORT_DIR ?? path.resolve(frontendDir, '../../backend/generated/qa')
const apiUrl = process.env.PLAYWRIGHT_API_URL ?? 'http://127.0.0.1:8000/api/v1'
const appUrl = process.env.PLAYWRIGHT_APP_URL ?? 'http://127.0.0.1:5173'
const terminalStatuses = new Set(['completed', 'needs_review', 'failed'])

type FixtureExpectation = { expected_roll_number?: string; expected_score?: number }
type FixtureManifest = { answer_key?: { question: number; correct_option: string }[]; scoring_policy?: Record<string, number | string>; images?: Record<string, FixtureExpectation> }
type BatchItem = {
  id: number
  filename: string | null
  status: string
  stage: string | null
  error_code: string | null
  error_message: string | null
  student_identifier: string | null
  raw_answers: Record<string, string> | null
  score: number | null
}

test('uploads fixture sheets through UI and reports backend-to-CSV results', async ({ page, request }, testInfo) => {
  test.setTimeout(20 * 60 * 1000)
  await fs.mkdir(reportDir, { recursive: true })

  let observedItems: BatchItem[] = []
  let wroteReport = false
  let fixtureNames: string[] = []
  const manifestPath = path.join(fixturesDir, 'expected.json')
  const manifest: FixtureManifest = await fs
    .readFile(manifestPath, 'utf-8')
    .then((text) => JSON.parse(text) as FixtureManifest)
    .catch(() => ({}))

  const writeReport = async (executionError?: string) => {
    const byFilename = new Map(observedItems.map((item) => [item.filename ?? '', item]))
    const results = fixtureNames.map((filename) => {
      const item = byFilename.get(filename)
      const expected = manifest.images?.[filename] ?? {}
      const detectedRoll = item?.student_identifier ?? null
      const rollStatus = expected.expected_roll_number === undefined
        ? 'unverified'
        : detectedRoll === expected.expected_roll_number && !detectedRoll?.includes('?')
          ? 'pass'
          : 'fail'
      const scoreStatus = item?.score === null || item?.score === undefined
        ? 'not_scored'
        : expected.expected_score === undefined
          ? 'unverified_test_key'
          : item.score === expected.expected_score
            ? 'pass'
            : 'fail'

      const failedStage = !item
        ? 'upload'
        : item.status !== 'failed'
          ? null
          : item.error_code?.includes('marker') || item.error_code === 'alignment_failed'
            ? 'alignment'
            : 'worker'

      return {
        image: filename,
        image_path: path.join('backend', 'tests', 'fixtures', 'sheets', filename),
        api_item_id: item?.id ?? null,
        pipeline_status: !item ? 'not_uploaded' : item.status === 'failed' ? 'failed' : 'passed',
        processing_status: item?.status ?? null,
        failed_stage: failedStage ?? item?.stage ?? null,
        error_code: item?.error_code ?? null,
        error: item?.error_message ?? null,
        expected_roll_number: expected.expected_roll_number ?? null,
        detected_roll_number: detectedRoll,
        roll_number_status: rollStatus,
        questions_read: item?.raw_answers ? Object.keys(item.raw_answers).length : 0,
        score: item?.score ?? null,
        expected_score: expected.expected_score ?? null,
        score_status: scoreStatus,
      }
    })

    const summary = {
      total_images: fixtureNames.length,
      uploaded_items: observedItems.length,
      pipeline_passed: results.filter((row) => row.pipeline_status === 'passed').length,
      pipeline_failed: results.filter((row) => row.pipeline_status === 'failed').length,
      not_uploaded: results.filter((row) => row.pipeline_status === 'not_uploaded').length,
      roll_labeled: results.filter((row) => row.expected_roll_number !== null).length,
      roll_passed: results.filter((row) => row.roll_number_status === 'pass').length,
      roll_failed: results.filter((row) => row.roll_number_status === 'fail').length,
      roll_unverified: results.filter((row) => row.roll_number_status === 'unverified').length,
      scores_calculated: results.filter((row) => row.score !== null).length,
      scores_unverified: results.filter((row) => row.score_status === 'unverified_test_key').length,
      execution_error: executionError ?? null,
    }
    const failures = summary.pipeline_failed + summary.not_uploaded + summary.roll_failed
    const unverified = summary.roll_unverified + summary.scores_unverified
    const report = {
      suite: 'omr-full-stack-playwright',
      generated_at: new Date().toISOString(),
      app_url: appUrl,
      fixtures_directory: fixturesDir,
      answer_key_source: manifest.answer_key ? 'fixture_manifest' : 'synthetic_all_A_smoke_key',
      status: failures || executionError ? 'FAIL' : unverified ? 'INCOMPLETE' : 'PASS',
      summary,
      results,
    }
    await fs.writeFile(path.join(reportDir, 'full_stack_qa_report.json'), `${JSON.stringify(report, null, 2)}\n`)
    wroteReport = true
    return report
  }

  try {
    const manifestEntries = await fs.readdir(fixturesDir, { withFileTypes: true })
    fixtureNames = manifestEntries
      .filter((entry) => entry.isFile() && /\.(jpe?g|png)$/i.test(entry.name))
      .map((entry) => entry.name)
      .sort()
    expect(fixtureNames.length, 'fixture directory should contain image files').toBeGreaterThan(0)

    const scoringPolicy = manifest.scoring_policy ?? {
      points_correct: 1,
      points_incorrect: 0,
      points_blank: 0,
      points_multiple: 0,
      negative_marking: 0,
      rounding: 'none',
    }
    const answerKey = manifest.answer_key ?? Array.from({ length: 200 }, (_, index) => ({
      question: index + 1,
      correct_option: 'A',
    }))
    const examResponse = await request.post(`${apiUrl}/exams`, {
      data: {
        title: `Playwright QA ${Date.now()}`,
        template_version: 'ambition-guru-v1',
        answer_key: answerKey,
        scoring_policy: scoringPolicy,
      },
      timeout: 30_000,
    })
    expect(examResponse.ok(), await examResponse.text()).toBeTruthy()
    const exam = await examResponse.json() as { id: number }

    await page.goto(appUrl)
    const examSelect = page.locator('select').first()
    await expect(examSelect.locator('option').nth(1)).toBeAttached({ timeout: 30_000 })
    await examSelect.selectOption(String(exam.id))

    const batchResponsePromise = page.waitForResponse((response) =>
      response.url().endsWith(`/exams/${exam.id}/batches`) && response.request().method() === 'POST',
    )
    await page.getByRole('button', { name: /start a new batch/i }).click()
    const batchResponse = await batchResponsePromise
    expect(batchResponse.ok(), await batchResponse.text()).toBeTruthy()
    const batch = await batchResponse.json() as { id: number }

    await page.locator('input[type="file"][multiple]').setInputFiles(
      fixtureNames.map((name) => path.join(fixturesDir, name)),
    )

    await expect.poll(async () => {
      const response = await request.get(`${apiUrl}/batches/${batch.id}/items`, { timeout: 15_000 })
      if (!response.ok()) return false
      observedItems = await response.json() as BatchItem[]
      return observedItems.length === fixtureNames.length
        && observedItems.every((item) => terminalStatuses.has(item.status))
    }, {
      timeout: 15 * 60 * 1000,
      intervals: [2_000, 5_000, 10_000],
      message: 'all fixture uploads should reach a terminal backend status',
    }).toBe(true)

    await page.getByRole('link', { name: /view results table/i }).click()
    await expect(page.locator('.results-table tbody tr')).toHaveCount(fixtureNames.length, { timeout: 30_000 })
    await expect(page.locator('.results-table tbody')).toContainText('91314')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('link', { name: /download results csv/i }).click()
    const download = await downloadPromise
    const downloadPath = await download.path()
    expect(downloadPath).not.toBeNull()
    const csv = await fs.readFile(downloadPath!, 'utf-8')
    const csvRows = csv.trim().split(/\r?\n/)
    expect(csvRows).toHaveLength(fixtureNames.length + 1)
    expect(csv).toContain('student_identifier')
    for (const [filename, expected] of Object.entries(manifest.images ?? {})) {
      if (expected.expected_roll_number) expect(csv, filename).toContain(expected.expected_roll_number)
    }

    const report = await writeReport()
    expect(report.summary.uploaded_items).toBe(fixtureNames.length)
    expect(report.summary.pipeline_failed, 'failed fixture images are listed in the JSON report').toBe(0)
    expect(report.summary.roll_failed, 'roll mismatches are listed in the JSON report').toBe(0)
    expect(report.summary.scores_calculated).toBeGreaterThan(0)
  } catch (error) {
    if (!wroteReport) {
      await writeReport(error instanceof Error ? `${error.name}: ${error.message}` : String(error))
    }
    throw error
  } finally {
    if (!wroteReport) await writeReport('Playwright test ended before report generation')
  }
})
