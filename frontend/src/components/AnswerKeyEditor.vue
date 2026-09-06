<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{ questionCount: number }>()
const emit = defineEmits<{
  submit: [answerKey: { question: number; correct_option: string }[]]
  cancel: []
}>()

const OPTIONS = ['A', 'B', 'C', 'D'] as const

const answers = ref<Record<number, string>>({})

const questionNumbers = computed(() =>
  Array.from({ length: props.questionCount }, (_, i) => i + 1),
)

const filledCount = computed(
  () => Object.values(answers.value).filter((v) => v !== '' && v !== undefined).length,
)

function selectOption(q: number, opt: string) {
  answers.value[q] = answers.value[q] === opt ? '' : opt
}

function submit() {
  const answerKey = questionNumbers.value.map((q) => ({
    question: q,
    correct_option: answers.value[q] ?? '',
  }))
  emit('submit', answerKey)
}
</script>

<template>
  <div class="key-editor">
    <div class="key-editor__header">
      <span>{{ filledCount }} / {{ questionCount }} answered</span>
    </div>

    <div class="key-editor__grid">
      <div v-for="q in questionNumbers" :key="q" class="key-editor__cell">
        <span class="key-editor__qnum">{{ q }}</span>
        <div class="key-editor__options">
          <button
            v-for="opt in OPTIONS"
            :key="opt"
            type="button"
            class="opt-btn"
            :class="{ 'opt-btn--active': answers[q] === opt }"
            @click="selectOption(q, opt)"
          >
            {{ opt }}
          </button>
        </div>
      </div>
    </div>

    <div class="key-editor__actions">
      <button @click="emit('cancel')">Cancel</button>
      <button class="primary" :disabled="filledCount < questionCount" @click="submit">
        Use this answer key
      </button>
    </div>
  </div>
</template>

<style scoped>
.key-editor__header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--ink-soft);
  margin-bottom: 10px;
}
.key-editor__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 6px 12px;
  max-height: 420px;
  overflow-y: auto;
  padding: 4px 4px 4px 0;
  border-top: 1px solid var(--paper-line);
  border-bottom: 1px solid var(--paper-line);
  padding-top: 10px;
  padding-bottom: 10px;
}
.key-editor__cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
.key-editor__qnum {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--ink-soft);
  width: 26px;
  text-align: right;
  flex-shrink: 0;
}
.key-editor__options {
  display: flex;
  gap: 3px;
}
.opt-btn {
  width: 24px;
  height: 24px;
  padding: 0;
  font-size: 0.72rem;
  font-weight: 600;
  border-radius: 50%;
  border: 1px solid var(--paper-line);
  background: white;
  color: var(--ink-soft);
}
.opt-btn:hover:not(:disabled) {
  background: var(--rose-wash);
  color: var(--ink);
}
.opt-btn--active {
  background: var(--rose);
  border-color: var(--rose);
  color: white;
}
.key-editor__actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
