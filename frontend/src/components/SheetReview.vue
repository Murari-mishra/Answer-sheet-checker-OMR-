<script setup lang="ts">
import { ref, computed } from 'vue'
import type { BatchItem } from '@/types/omr'

const props = defineProps<{ item: BatchItem; label?: string }>()
const emit = defineEmits<{
  submit: [payload: { confirmedAnswers: Record<string, string>; studentIdentifier?: string }]
  close: []
}>()

const editedAnswers = ref<Record<string, string>>({ ...(props.item.raw_answers ?? {}) })
const editedStudentIdentifier = ref(props.item.student_identifier ?? '')

const questionNumbers = computed(() =>
  Object.keys(editedAnswers.value)
    .map(Number)
    .sort((a, b) => a - b),
)

function needsAttention(q: number): boolean {
  const val = editedAnswers.value[String(q)]
  return val === undefined || val === '' || val.includes(',')
}

function submit() {
  const studentIdentifier = editedStudentIdentifier.value.trim()
  emit('submit', {
    confirmedAnswers: editedAnswers.value,
    // An uncertain value such as "925??" is left unchanged. A corrected
    // value is sent to the backend and validated there.
    studentIdentifier: /^\d{5}$/.test(studentIdentifier) ? studentIdentifier : undefined,
  })
}
</script>

<template>
  <div class="review-overlay">
    <div class="review-panel">
      <h3>Review: {{ label ?? `Item #${item.id}` }}</h3>
      <p class="hint">
        Highlighted questions were blank or had multiple marks detected. Correct any answer below,
        then confirm.
      </p>

      <label class="roll-number" for="student-identifier">Roll number</label>
      <input
        id="student-identifier"
        v-model="editedStudentIdentifier"
        class="roll-number__input"
        inputmode="numeric"
        maxlength="5"
        pattern="[0-9]{5}"
        placeholder="5 digits"
      />

      <div class="answer-grid">
        <div
          v-for="q in questionNumbers"
          :key="q"
          class="answer-cell"
          :class="{ 'answer-cell--flag': needsAttention(q) }"
        >
          <label :for="`q-${q}`">{{ q }}</label>
          <input :id="`q-${q}`" v-model="editedAnswers[String(q)]" maxlength="3" placeholder="—" />
        </div>
      </div>

      <div class="review-actions">
        <button @click="emit('close')">Cancel</button>
        <button class="primary" @click="submit">Confirm & Score</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.review-overlay {
  position: fixed;
  inset: 0;
  background: rgba(35, 33, 43, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.review-panel {
  background: var(--paper);
  border-radius: 6px;
  padding: 24px;
  max-width: 900px;
  max-height: 85vh;
  overflow-y: auto;
}
.hint {
  color: var(--ink-soft);
  font-size: 0.85rem;
  margin-bottom: 16px;
}
.answer-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 6px;
}
.roll-number {
  display: block;
  font-weight: 600;
  margin-bottom: 4px;
}
.roll-number__input {
  width: 90px;
  margin-bottom: 16px;
  padding: 4px;
  text-align: center;
}
.answer-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 0.75rem;
}
.answer-cell input {
  width: 40px;
  text-align: center;
  padding: 4px;
}
.answer-cell--flag input {
  border-color: var(--warning);
  background: var(--warning-wash);
}
.review-actions {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
