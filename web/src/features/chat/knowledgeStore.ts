import { create } from 'zustand'
import {
  type ImportJob,
  type KnowledgeFile,
  getImportJobs,
  getKnowledgeFiles,
  uploadKnowledgeFile,
} from './chatApi'

interface KnowledgeState {
  files: KnowledgeFile[]
  jobs: ImportJob[]
  uploading: boolean
  pollTimer: ReturnType<typeof setInterval> | null

  fetchFiles: () => Promise<void>
  fetchJobs: () => Promise<void>
  fetchAll: () => Promise<void>
  upload: (file: File) => Promise<void>
  startPolling: () => void
  stopPolling: () => void
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  files: [],
  jobs: [],
  uploading: false,
  pollTimer: null,

  fetchFiles: async () => {
    try {
      const { files } = await getKnowledgeFiles()
      set({ files })
    } catch (e) {
      console.error('fetch knowledge files failed:', e)
    }
  },

  fetchJobs: async () => {
    try {
      const { jobs } = await getImportJobs()
      set({ jobs })
    } catch (e) {
      console.error('fetch import jobs failed:', e)
    }
  },

  fetchAll: async () => {
    await Promise.all([get().fetchFiles(), get().fetchJobs()])
  },

  upload: async (file: File) => {
    set({ uploading: true })
    try {
      await uploadKnowledgeFile(file)
      get().startPolling()
      await get().fetchAll()
    } finally {
      set({ uploading: false })
    }
  },

  startPolling: () => {
    const { pollTimer } = get()
    if (pollTimer) { return }

    const timer = setInterval(async () => {
      await get().fetchAll()
      const { jobs } = get()
      const hasActive = jobs.some((j) => j.status === 'pending' || j.status === 'processing')
      if (!hasActive) {
        get().stopPolling()
      }
    }, 2000)

    set({ pollTimer: timer })
  },

  stopPolling: () => {
    const { pollTimer } = get()
    if (pollTimer) {
      clearInterval(pollTimer)
      set({ pollTimer: null })
    }
  },
}))
