import api from '@/http/axios'

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export interface ChatRequest {
  message: string
  session_id?: string
  model?: string
  response_mode?: 'text' | 'voice'
  max_tokens?: number
  relevance_threshold?: number
  template_name?: string
  enable_rerank?: boolean
  enable_optimization?: boolean
  enable_expansion?: boolean
  tts_voice?: string
  tts_format?: 'mp3' | 'opus' | 'aac' | 'flac' | 'wav' | 'pcm'
}

export interface ModelGroup {
  key: string
  label: string
  models: string[]
}

export interface ModelsResponse {
  groups: ModelGroup[]
  default: string
}

export interface ChatResponse {
  message: string
  answer: string
  query_id: string
  session_id?: string
  processing_time: number
  tokens_used: number
  relevance_score: number
  retrieved_chunks_count: number
  metadata: Record<string, unknown>
  speech?: {
    endpoint: string
    text: string
    voice?: string
    response_format?: string
  } | null
}

export interface SpeechTranscriptionResponse {
  text: string
  model: string
}

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return api.post('/api/v1/chat', request)
}

export async function transcribeAudio(blob: Blob): Promise<SpeechTranscriptionResponse> {
  const formData = new FormData()
  formData.append('file', blob, 'voice.webm')

  return api.post('/api/v1/speech/transcriptions', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export async function getModels(): Promise<ModelsResponse> {
  return api.get('/api/v1/models')
}

export async function synthesizeSpeech(params: {
  text: string
  voice?: string
  response_format?: string
}): Promise<Blob> {
  return api.post('/api/v1/speech/audio', params, {
    responseType: 'blob',
  })
}

// ── 知识库导入 ──

export interface ImportJob {
  id: string
  file_name: string
  file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  data_created: number
  vectors_created: number
  error: string | null
  created_at: string
  finished_at: string | null
}

export async function uploadKnowledgeFile(file: File): Promise<{ job_id: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/api/v1/import/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function getImportJobs(): Promise<{ jobs: ImportJob[] }> {
  return api.get('/api/v1/import/jobs')
}

export async function getSupportedFormats(): Promise<{ formats: string[] }> {
  return api.get('/api/v1/import/formats')
}

export interface KnowledgeFile {
  id: string
  name: string
  file_type: string
  data_count: number
  total_tokens: number
  created_at: string | null
}

export async function getKnowledgeFiles(): Promise<{ files: KnowledgeFile[] }> {
  return api.get('/api/v1/import/files')
}
