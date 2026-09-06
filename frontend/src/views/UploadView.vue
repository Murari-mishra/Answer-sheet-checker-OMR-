<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useOmrStore } from '@/stores/omr'
import type { UploadRow, Exam } from '@/types/omr'
import BatchUploader from '@/components/BatchUploader.vue'
import SheetReview from '@/components/SheetReview.vue'
import AnswerKeyEditor from '@/components/AnswerKeyEditor.vue'

const store = useOmrStore()
const selectedExamId = ref<number | null>(null)
const reviewingRow = ref<UploadRow | null>(null)

const newExamTitle = ref('')
const newExamQuestionCount = ref(200)
const showKeyEditor = ref(false)
const examCreateError = ref<string | null>(null)

onMounted(() => {
  store.fetchExams()
})

const csvUrl = computed(() => {
  const batch = store.currentBatch
  return batch ? `http://127.0.0.1:8000/api/v1/batches/${batch.id}/results.csv` : ''
})

const showCsvLink = computed(() => {
  const batch = store.currentBatch
  return batch !== null && batch.total_count > 0
})

function openKeyEditor() {
  examCreateError.value = null
  if (!newExamTitle.value.trim()) {
    examCreateError.value = 'Enter an exam title first'
    return
  }
  const count = newExamQuestionCount.value
  if (!Number.isInteger(count) || count < 1 || count > 200) {
    examCreateError.value = 'Question count must be between 1 and 200 (the sheet has 200 positions)'
    return
  }
  showKeyEditor.value = true
}

async function createExamWithKey(answerKey: { question: number; correct_option: string }[]) {
  try {
    const exam = await fetch('http://127.0.0.1:8000/api/v1/exams', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: newExamTitle.value,
        template_version: 'ambition-guru-v1',
        answer_key: answerKey,
        scoring_policy: {
          points_correct: 1,
          points_incorrect: 0,
          points_blank: 0,
          points_multiple: 0,
          negative_marking: 0,
          rounding: 'none',
        },
      }),
    }).then((r) => r.json() as Promise<Exam>)
    await store.fetchExams()
    selectedExamId.value = exam.id
    showKeyEditor.value = false
    newExamTitle.value = ''
  } catch {
    examCreateError.value = 'Failed to create exam'
  }
}

async function startBatch() {
  if (selectedExamId.value === null) return
  await store.createBatch(selectedExamId.value)
}

function onReviewRequested(row: UploadRow) {
  reviewingRow.value = row
}

async function onReviewSubmit(confirmedAnswers: Record<string, string>) {
  if (reviewingRow.value) {
    await store.submitReview(reviewingRow.value, confirmedAnswers)
  }
  reviewingRow.value = null
}
</script>

<template>
  <div class="upload-view">
    <h1>OMR Batch Upload</h1>

    <section v-if="!store.currentBatch" class="setup">
      <div class="setup-block">
        <h2 class="step-label">1. Choose or create an exam</h2>
        <select v-model="selectedExamId">
          <option :value="null">-- select --</option>
          <option v-for="exam in store.exams" :key="exam.id" :value="exam.id">
            {{ exam.title }} (#{{ exam.id }})
          </option>
        </select>

        <details class="new-exam">
          <summary>Create a new exam</summary>
          <input v-model="newExamTitle" placeholder="Exam title" />
          <label class="question-count-label">
            Number of questions
            <input
              v-model.number="newExamQuestionCount"
              type="number"
              min="1"
              max="200"
              class="question-count-input"
            />
          </label>
          <button @click="openKeyEditor">Set answer key</button>
          <p v-if="examCreateError" class="error">{{ examCreateError }}</p>
        </details>
      </div>

      <button class="primary" :disabled="selectedExamId === null" @click="startBatch">
        2. Start a new batch
      </button>
    </section>

    <section v-else>
      <div class="batch-header">
        <strong>Batch #{{ store.currentBatch.id }}</strong>
        <span class="batch-header__stats">
          {{ store.currentBatch.succeeded_count }} completed
          / {{ store.currentBatch.review_count }} needs review
          / {{ store.currentBatch.failed_count }} failed
          / {{ store.currentBatch.total_count }} total
        </span>
      </div>

      <RouterLink :to="`/batches/${store.currentBatch.id}/results`" class="results-link">
        View results table
      </RouterLink>

      <BatchUploader @review="onReviewRequested" />

      <a v-if="showCsvLink" :href="csvUrl" class="csv-link">Download results CSV</a>
    </section>

    <div v-if="showKeyEditor" class="key-editor-overlay">
      <div class="key-editor-panel">
        <h2>Answer key for "{{ newExamTitle }}"</h2>
        <AnswerKeyEditor
          :question-count="newExamQuestionCount"
          @submit="createExamWithKey"
          @cancel="showKeyEditor = false"
        />
      </div>
    </div>

    <SheetReview
      v-if="reviewingRow && reviewingRow.item"
      :item="reviewingRow.item"
      :label="reviewingRow.file.name"
      @submit="onReviewSubmit"
      @close="reviewingRow = null"
    />
  </div>
</template>

<style scoped>
.upload-view {
  max-width: 820px;
  margin: 0 auto;
  padding: 40px 24px;
}
.setup-block {
  margin-bottom: 20px;
}
.step-label {
  font-size: 1rem;
  margin-bottom: 10px;
}
.setup-block select {
  display: block;
  width: 100%;
  margin-bottom: 12px;
}
.new-exam summary {
  cursor: pointer;
  color: var(--ink-soft);
  font-size: 0.9rem;
  margin-bottom: 10px;
}
.new-exam input {
  display: block;
  width: 100%;
  margin-bottom: 10px;
}
.question-count-label {
  display: block;
  font-size: 0.8rem;
  color: var(--ink-soft);
  margin-bottom: 10px;
}
.question-count-input {
  display: block;
  width: 100px;
  margin-top: 4px;
}
.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--paper-line);
}
.batch-header strong {
  font-family: var(--font-mono);
  font-size: 0.9rem;
}
.batch-header__stats {
  font-size: 0.85rem;
  color: var(--ink-soft);
}
.results-link {
  display: inline-block;
  margin: 12px 0;
  font-size: 0.85rem;
}
.csv-link {
  display: inline-block;
  margin-top: 20px;
  font-size: 0.9rem;
}
.error {
  color: var(--danger);
  font-size: 0.85rem;
}
.key-editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(35, 33, 43, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.key-editor-panel {
  background: var(--paper);
  border-radius: 6px;
  padding: 28px;
  max-width: 640px;
  width: 90vw;
  max-height: 88vh;
  overflow-y: auto;
}
</style>
