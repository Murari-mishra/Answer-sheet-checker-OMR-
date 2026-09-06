import { defineStore } from 'pinia'
import { ref } from 'vue'
import { examsApi, batchesApi, uploadSheetItem, retrySheetItem } from '@/api/omr'
import type { Exam, Batch, BatchItem, UploadRow, ItemStatus } from '@/types/omr'

const TERMINAL_STATUSES: ItemStatus[] = ['completed', 'needs_review', 'failed']
const POLL_INTERVAL_MS = 1500
const MAX_CONCURRENT_UPLOADS = 3

export const useOmrStore = defineStore('omr', () => {
  const exams = ref<Exam[]>([])
  const currentBatch = ref<Batch | null>(null)
  const rows = ref<UploadRow[]>([])

  let pollHandle: ReturnType<typeof setInterval> | null = null

  async function fetchExams() {
    exams.value = await examsApi.list()
  }

  async function createBatch(examId: number) {
    currentBatch.value = await batchesApi.create(examId)
    rows.value = []
    return currentBatch.value
  }

  function makeClientId() {
    return `row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  }

  /**
   * Adds files as local rows immediately, then uploads with bounded
   * concurrency. Critically: after pushing into rows.value, we re-read the
   * rows back OUT of rows.value (not the pre-push local objects) before
   * doing anything else with them. Vue's reactivity tracks changes through
   * the reactive proxy - mutating a plain object reference captured before
   * it entered the reactive array bypasses that tracking, which is exactly
   * what caused the stuck "Uploading..." display.
   */
  async function addFiles(files: File[]) {
    const startIndex = rows.value.length
    const plainRows: UploadRow[] = files.map((file) => ({
      clientId: makeClientId(),
      file,
      uploadProgress: 0,
      itemId: null,
      item: null,
      uploadError: null,
    }))
    rows.value.push(...plainRows)

    // re-read as the actual reactive entries, not the pre-push references
    const reactiveRows = rows.value.slice(startIndex)

    const queue = [...reactiveRows]
    async function worker() {
      while (queue.length > 0) {
        const row = queue.shift()
        if (!row) continue
        await uploadRow(row)
      }
    }
    const workers = Array.from({ length: MAX_CONCURRENT_UPLOADS }, () => worker())
    await Promise.all(workers)

    startPolling()
  }

  async function uploadRow(row: UploadRow) {
    if (!currentBatch.value) return
    try {
      const item = await uploadSheetItem(currentBatch.value.id, row.file, (percent) => {
        row.uploadProgress = percent
      })
      row.itemId = item.id
      row.item = item
    } catch (err) {
      row.uploadError = err instanceof Error ? err.message : 'Upload failed'
    }
  }

  async function retryRow(row: UploadRow, replacementFile: File) {
    if (!currentBatch.value || row.itemId === null) return
    row.uploadProgress = 0
    row.uploadError = null
    try {
      const item = await retrySheetItem(currentBatch.value.id, row.itemId, replacementFile, (percent) => {
        row.uploadProgress = percent
      })
      row.item = item
      startPolling()
    } catch (err) {
      row.uploadError = err instanceof Error ? err.message : 'Retry failed'
    }
  }

  function allTerminal(): boolean {
    return rows.value
      .filter((r) => r.itemId !== null)
      .every((r) => r.item && TERMINAL_STATUSES.includes(r.item.status))
  }

  function startPolling() {
    if (pollHandle !== null) return
    pollHandle = setInterval(async () => {
      if (!currentBatch.value) return

      const serverItems = await batchesApi.listItems(currentBatch.value.id)
      const byId = new Map(serverItems.map((it) => [it.id, it]))

      for (const row of rows.value) {
        if (row.itemId === null) continue
        const fresh = byId.get(row.itemId)
        if (fresh) row.item = fresh
      }

      currentBatch.value = await batchesApi.get(currentBatch.value.id)

      if (allTerminal()) {
        stopPolling()
      }
    }, POLL_INTERVAL_MS)
  }

  function stopPolling() {
    if (pollHandle !== null) {
      clearInterval(pollHandle)
      pollHandle = null
    }
  }

  async function submitReview(row: UploadRow, confirmedAnswers: Record<string, string>) {
    if (!currentBatch.value || row.itemId === null) return
    const updated = await batchesApi.review(currentBatch.value.id, row.itemId, confirmedAnswers)
    row.item = updated
    currentBatch.value = await batchesApi.get(currentBatch.value.id)
  }

  return {
    exams,
    currentBatch,
    rows,
    fetchExams,
    createBatch,
    addFiles,
    retryRow,
    submitReview,
    stopPolling,
  }
})
