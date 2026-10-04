export type ItemStatus =
  | 'uploading'
  | 'queued'
  | 'processing'
  | 'needs_review'
  | 'completed'
  | 'failed'

export interface Exam {
  id: number
  title: string
  template_version: string
  answer_key: { question: number; correct_option: string }[]
  scoring_policy: Record<string, number | string>
  created_at: string
}

export interface Batch {
  id: number
  exam_id: number
  status: string
  total_count: number
  succeeded_count: number
  review_count: number
  failed_count: number
  created_at: string
}

export interface BatchItem {
  id: number
  batch_id: number
  filename: string | null
  status: ItemStatus
  stage: string | null
  progress: number
  attempt: number
  error_code: string | null
  error_message: string | null
  student_identifier: string | null
  raw_answers: Record<string, string> | null
  confirmed_answers: Record<string, string>
  score: number | null
  created_at: string
}

export interface UploadRow {
  clientId: string
  file: File
  uploadProgress: number
  itemId: number | null
  item: BatchItem | null
  uploadError: string | null
}
