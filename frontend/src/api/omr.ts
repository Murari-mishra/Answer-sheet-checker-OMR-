import { apiClient, BASE_URL } from './client'
import type { Exam, Batch, BatchItem } from '@/types/omr'

export const examsApi = {
  list: () => apiClient.get<Exam[]>('/exams'),
  get: (id: number) => apiClient.get<Exam>(`/exams/${id}`),
}

export const batchesApi = {
  create: (examId: number) => apiClient.post<Batch>(`/exams/${examId}/batches`),
  get: (batchId: number) => apiClient.get<Batch>(`/batches/${batchId}`),
  listItems: (batchId: number) => apiClient.get<BatchItem[]>(`/batches/${batchId}/items`),
  getItem: (batchId: number, itemId: number) =>
    apiClient.get<BatchItem>(`/batches/${batchId}/items/${itemId}`),
  review: (batchId: number, itemId: number, confirmedAnswers: Record<string, string>) =>
    apiClient.post<BatchItem>(`/batches/${batchId}/items/${itemId}/review`, {
      confirmed_answers: confirmedAnswers,
    }),
  resultsCsvUrl: (batchId: number) => `${BASE_URL}/batches/${batchId}/results.csv`,
}

/**
 * Uploads one sheet via XMLHttpRequest (not fetch) specifically to get
 * real upload.onprogress events - fetch has no broadly-supported way to
 * report upload (request body) progress, only download progress.
 */
export function uploadSheetItem(
  batchId: number,
  file: File,
  onProgress: (percent: number) => void,
): Promise<BatchItem> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE_URL}/batches/${batchId}/items`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Failed to parse upload response'))
        }
      } else {
        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`))
      }
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))

    const formData = new FormData()
    formData.append('file', file)
    xhr.send(formData)
  })
}

export function retrySheetItem(
  batchId: number,
  itemId: number,
  file: File,
  onProgress: (percent: number) => void,
): Promise<BatchItem> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE_URL}/batches/${batchId}/items/${itemId}/retry`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Failed to parse retry response'))
        }
      } else {
        reject(new Error(`Retry failed: ${xhr.status} ${xhr.statusText}`))
      }
    }
    xhr.onerror = () => reject(new Error('Network error during retry'))

    const formData = new FormData()
    formData.append('file', file)
    xhr.send(formData)
  })
}
