<script setup lang="ts">
import { computed } from 'vue'
import type { UploadRow } from '@/types/omr'

const props = defineProps<{ row: UploadRow }>()
const emit = defineEmits<{
  review: [row: UploadRow]
  retry: [row: UploadRow]
}>()

const statusLabel = computed(() => {
  const row = props.row
  if (row.uploadError) return `Upload failed: ${row.uploadError}`
  if (row.itemId === null) return 'Uploading…'

  const item = row.item
  if (!item) return 'Uploading…'

  switch (item.status) {
    case 'queued':
      return 'Queued'
    case 'processing':
      return item.stage ? `Processing: ${item.stage}` : 'Processing'
    case 'needs_review':
      return 'Needs review'
    case 'completed':
      return item.score !== null ? `Completed — score ${item.score}` : 'Completed'
    case 'failed':
      return `Failed: ${item.error_message ?? item.error_code ?? 'unknown error'}`
    default:
      return item.status
  }
})

const displayPercent = computed(() => {
  const row = props.row
  if (row.itemId === null) return row.uploadProgress // transfer progress
  return row.item?.progress ?? 0 // server processing progress
})

const barColor = computed(() => {
  const item = props.row.item
  if (props.row.uploadError || item?.status === 'failed') return '#d64545'
  if (item?.status === 'needs_review') return '#d69b1f'
  if (item?.status === 'completed') return '#3f9142'
  return '#4a6fd6'
})
</script>

<template>
  <div class="item-row">
    <div class="item-row__name">{{ row.file.name }}</div>
    <div class="item-row__bar-track">
      <div
        class="item-row__bar-fill"
        :style="{ width: displayPercent + '%', backgroundColor: barColor }"
      />
    </div>
    <div class="item-row__status">{{ statusLabel }}</div>
    <div class="item-row__actions">
      <button
        v-if="row.item?.status === 'needs_review'"
        @click="emit('review', row)"
      >
        Review
      </button>
      <button
        v-if="row.item?.status === 'failed'"
        @click="emit('retry', row)"
      >
        Retry
      </button>
    </div>
  </div>
</template>

<style scoped>
.item-row {
  display: grid;
  grid-template-columns: 1fr 2fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}
.item-row__name {
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-row__bar-track {
  height: 8px;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
}
.item-row__bar-fill {
  height: 100%;
  transition: width 0.2s ease;
}
.item-row__status {
  font-size: 0.85rem;
  color: #555;
  white-space: nowrap;
}
.item-row__actions button {
  font-size: 0.8rem;
  padding: 4px 10px;
  cursor: pointer;
}
</style>
