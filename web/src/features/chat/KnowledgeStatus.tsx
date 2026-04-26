import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BookOpen, CheckCircle, FileText, Loader2, XCircle } from 'lucide-react'
import { useKnowledgeStore } from './knowledgeStore'

function formatTime(iso: string | null): string {
  if (!iso) { return '' }
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const STATUS_ICON = {
  pending: <Loader2 size={14} className="animate-spin text-amber-500" />,
  processing: <Loader2 size={14} className="animate-spin text-blue-500" />,
  completed: <CheckCircle size={14} className="text-emerald-500" />,
  failed: <XCircle size={14} className="text-red-500" />,
} as const

const STATUS_LABEL_KEY = {
  pending: 'jobPending',
  processing: 'jobProcessing',
  completed: 'jobCompleted',
  failed: 'jobFailed',
} as const

const JOB_BG = {
  pending: 'bg-amber-50 dark:bg-amber-900/15',
  processing: 'bg-blue-50 dark:bg-blue-900/20',
  completed: 'bg-emerald-50 dark:bg-emerald-900/15',
  failed: 'bg-red-50 dark:bg-red-900/15',
} as const

export default function KnowledgeStatus() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const files = useKnowledgeStore((s) => s.files)
  const jobs = useKnowledgeStore((s) => s.jobs)
  const fetchAll = useKnowledgeStore((s) => s.fetchAll)

  const hasActive = jobs.some((j) => j.status === 'pending' || j.status === 'processing')
  const totalCount = files.length + jobs.length

  useEffect(() => {
    void fetchAll()
  }, [fetchAll])

  useEffect(() => {
    if (!open) { return }
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const toggle = useCallback(() => {
    setOpen((v) => {
      if (!v) { void fetchAll() }
      return !v
    })
  }, [fetchAll])

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={toggle}
        className="relative flex h-9 w-9 items-center justify-center rounded-full text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 dark:text-stone-500 dark:hover:bg-white/10 dark:hover:text-stone-300"
        aria-label={t('knowledgeStatus')}
      >
        <BookOpen size={16} />
        {hasActive && (
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-blue-500 ring-2 ring-[#fbfaf8] dark:ring-[#111111]" />
        )}
        {!hasActive && totalCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-stone-700 text-[9px] font-bold text-white ring-2 ring-[#fbfaf8] dark:bg-stone-300 dark:text-stone-900 dark:ring-[#111111]">
            {totalCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-50 w-80 rounded-2xl border border-stone-200/80 bg-white p-4 shadow-xl dark:border-white/10 dark:bg-[#1a1a1a]">
          <p className="mb-3 text-sm font-medium text-stone-700 dark:text-stone-200">
            {t('knowledgeFiles')}
          </p>

          {jobs.length === 0 && files.length === 0 ? (
            <p className="py-6 text-center text-sm text-stone-400 dark:text-stone-500">
              {t('noFilesYet')}
            </p>
          ) : (
            <div className="max-h-72 space-y-1.5 overflow-y-auto">
              {/* 所有 upload jobs，按状态着色 */}
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 ${JOB_BG[job.status]}`}
                >
                  <div className="shrink-0">{STATUS_ICON[job.status]}</div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-stone-800 dark:text-stone-200">
                      {job.file_name}
                    </p>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-stone-400 dark:text-stone-500">
                      <span>{t(STATUS_LABEL_KEY[job.status])}</span>
                      {job.status === 'completed' && job.data_created > 0 && (
                        <>
                          <span>·</span>
                          <span>{job.data_created} chunks</span>
                        </>
                      )}
                      {job.error && (
                        <>
                          <span>·</span>
                          <span className="truncate text-red-400">{job.error}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* MongoDB 持久化文件（去重：跳过 jobs 中已 completed 的同名文件） */}
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-2.5 rounded-xl bg-stone-50 px-3 py-2.5 dark:bg-white/5"
                >
                  <FileText size={14} className="shrink-0 text-stone-400 dark:text-stone-500" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-stone-800 dark:text-stone-200">
                      {file.name}{file.file_type}
                    </p>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-stone-400 dark:text-stone-500">
                      <span>{file.data_count} chunks</span>
                      <span>·</span>
                      <span>{formatTime(file.created_at)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
