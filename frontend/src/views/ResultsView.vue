<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { batchesApi } from '@/api/omr'
import SheetReview from '@/components/SheetReview.vue'
import type { Batch, BatchItem } from '@/types/omr'

const route = useRoute()
const batchId = Number(route.params.id)

const batch = ref<Batch | null>(null)
const items = ref<BatchItem[]>([])
const loading = ref(true)
const reviewingItem = ref<BatchItem | null>(null)

async function refresh() {
  batch.value = await batchesApi.get(batchId)
  items.value = await batchesApi.listItems(batchId)
}

onMounted(async () => {
  await refresh()
  loading.value = false
})

const csvUrl = computed(() => batchesApi.resultsCsvUrl(batchId))

function statusClass(status: string): string {
  switch (status) {
    case 'completed':
      return 'status--completed'
    case 'needs_review':
      return 'status--review'
    case 'failed':
      return 'status--failed'
    default:
      return 'status--pending'
  }
}

function openReview(item: BatchItem) {
  reviewingItem.value = item
}

async function onReviewSubmit(payload: { confirmedAnswers: Record<string, string>; studentIdentifier?: string }) {
  if (reviewingItem.value) {
    await batchesApi.review(batchId, reviewingItem.value.id, payload.confirmedAnswers, payload.studentIdentifier)
  }
  reviewingItem.value = null
  await refresh()
}
</script>

<template>
  <div class="results-view">
    <h2>Batch #{{ batchId }} Results</h2>

    <div v-if="loading">Loading...</div>

    <template v-else-if="batch">
      <div class="summary">
        <span class="summary__stat">{{ batch.total_count }} total</span>
        <span class="summary__stat status--completed">{{ batch.succeeded_count }} completed</span>
        <span class="summary__stat status--review">{{ batch.review_count }} needs review</span>
        <span class="summary__stat status--failed">{{ batch.failed_count }} failed</span>
      </div>

      <table class="results-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>Student</th>
            <th>Status</th>
            <th>Score</th>
            <th>Attempt</th>
            <th>Error</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>#{{ item.id }}</td>
            <td>{{ item.student_identifier ?? '—' }}</td>
            <td>
              <span :class="['status-badge', statusClass(item.status)]">{{ item.status }}</span>
            </td>
            <td>{{ item.score ?? '—' }}</td>
            <td>{{ item.attempt }}</td>
            <td class="error-cell">{{ item.error_message ?? '' }}</td>
            <td>
              <button v-if="item.status === 'needs_review'" @click="openReview(item)">
                Review
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <a :href="csvUrl" class="csv-link">Download results CSV</a>
    </template>

    <SheetReview
      v-if="reviewingItem"
      :item="reviewingItem"
      @submit="onReviewSubmit"
      @close="reviewingItem = null"
    />
  </div>
</template>

<style scoped>
.results-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}
.summary {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  font-size: 0.9rem;
}
.summary__stat {
  padding: 4px 10px;
  border-radius: 4px;
  background: #f0f0f0;
}
.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.results-table th,
.results-table td {
  text-align: left;
  padding: 6px 10px;
  border-bottom: 1px solid var(--paper-line);
}
.status-badge {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.8rem;
}
.status--completed {
  background: var(--success-wash);
  color: var(--success);
}
.status--review {
  background: var(--warning-wash);
  color: var(--warning);
}
.status--failed {
  background: var(--danger-wash);
  color: var(--danger);
}
.status--pending {
  background: #eef0f5;
  color: #556;
}
.error-cell {
  color: var(--danger);
  font-size: 0.8rem;
}
.csv-link {
  display: inline-block;
  margin-top: 20px;
}
</style>
