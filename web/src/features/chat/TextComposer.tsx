import { useCallback, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowUp, Paperclip } from 'lucide-react'
import toast from 'react-hot-toast'
import VoiceModeButton from './VoiceModeButton'
import { useKnowledgeStore } from './knowledgeStore'

interface TextComposerProps {
  loading: boolean
  onSendText: (text: string) => void
  onStartVoice: () => void
}

export default function TextComposer({
  loading,
  onSendText,
  onStartVoice,
}: TextComposerProps) {
  const { t } = useTranslation()
  const [text, setText] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploading = useKnowledgeStore((s) => s.uploading)
  const upload = useKnowledgeStore((s) => s.upload)

  const sendText = useCallback(() => {
    const message = text.trim()
    if (!message || loading) {
      return
    }
    onSendText(message)
    setText('')
  }, [loading, onSendText, text])

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) { return }
      e.target.value = ''

      try {
        await upload(file)
        toast.success(t('uploadSuccess', { name: file.name }))
      } catch {
        toast.error(t('uploadFailed'))
      }
    },
    [upload, t],
  )

  const hasText = text.trim().length > 0

  return (
    <div className="bg-gradient-to-t from-[#fbfaf8] via-[#fbfaf8] to-transparent px-4 pb-6 pt-10 dark:from-[#111111] dark:via-[#111111]">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-[28px] border border-stone-200/80 bg-white p-2 shadow-[0_8px_60px_rgba(41,37,36,0.08)] dark:border-white/10 dark:bg-[#1a1a1a] dark:shadow-[0_8px_60px_rgba(0,0,0,0.3)]">
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.pdf"
            className="hidden"
            onChange={(e) => void handleFileChange(e)}
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-stone-400 transition hover:bg-stone-100 hover:text-stone-600 disabled:opacity-50 dark:text-stone-500 dark:hover:bg-white/10 dark:hover:text-stone-300"
            aria-label={t('uploadFile')}
            title={t('uploadFileFormats')}
          >
            <Paperclip size={18} />
          </button>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendText()
              }
            }}
            rows={1}
            placeholder={t('composerPlaceholder')}
            className="max-h-32 min-h-12 flex-1 resize-none bg-transparent px-4 py-3 text-[15px] leading-6 text-stone-950 outline-none placeholder:text-stone-400 dark:text-stone-50 dark:placeholder:text-stone-500"
          />

          <VoiceModeButton onClick={onStartVoice} />

          <button
            type="button"
            onClick={sendText}
            disabled={!hasText || loading}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-stone-950 text-white transition-all hover:bg-stone-800 disabled:bg-stone-200 disabled:text-stone-400 dark:bg-white dark:text-stone-950 dark:hover:bg-stone-200 dark:disabled:bg-stone-700 dark:disabled:text-stone-500"
            aria-label={t('send')}
          >
            <ArrowUp size={18} strokeWidth={2.5} />
          </button>
        </div>

        <p className="mt-3 text-center text-xs text-stone-400 dark:text-stone-500">
          {t('composerHint')}
        </p>
      </div>
    </div>
  )
}
