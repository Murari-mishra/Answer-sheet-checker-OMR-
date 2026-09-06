<script setup lang="ts">
import { ref } from 'vue'
import { useOmrStore } from '@/stores/omr'
import ItemProgress from './ItemProgress.vue'
import type { UploadRow } from '@/types/omr'

const store = useOmrStore()
const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

function pickFiles() {
  fileInput.value?.click()
}

function onFileInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    store.addFiles(Array.from(input.files))
    input.value = '' // allow re-selecting the same file later
  }
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    store.addFiles(Array.from(files))
  }
}

const emit = defineEmits<{
  review: [row: UploadRow]
}>()

function handleReview(row: UploadRow) {
  emit('review', row)
}

function handleRetry(row: UploadRow) {
  // trigger a hidden file picker scoped to this specific row for the replacement file
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/jpeg,image/png'
  input.onchange = () => {
    if (input.files && input.files[0]) {
      store.retryRow(row, input.files[0])
    }
  }
  input.click()
}
</script>

<template>
  <div>
    <div
      class="dropzone"
      :class="{ 'dropzone--active': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="pickFiles"
    >
      <p>Drop answer sheets here, or click to select (JPEG/PNG)</p>
      <input
        ref="fileInput"
        type="file"
        accept="image/jpeg,image/png"
        multiple
        style="display: none"
        @change="onFileInputChange"
      />
    </div>

    <div v-if="store.rows.length > 0" class="rows">
      <ItemProgress
        v-for="row in store.rows"
        :key="row.clientId"
        :row="row"
        @review="handleReview"
        @retry="handleRetry"
      />
    </div>
  </div>
</template>

<style scoped>
.dropzone {
  border: 2px dashed #bbb;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  color: #666;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.dropzone--active {
  border-color: #4a6fd6;
  background: #f0f4ff;
}
.rows {
  margin-top: 24px;
}
</style>
