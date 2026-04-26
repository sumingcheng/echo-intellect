import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BookOpen, Keyboard, Mic, X } from 'lucide-react'
import { Streamdown } from 'streamdown'
import { code } from '@streamdown/code'
import { math } from '@streamdown/math'
import { cjk } from '@streamdown/cjk'
import 'katex/dist/katex.min.css'
import type { ChatMessage, Reference } from './chatStore'

const plugins = { code, math, cjk }

function ReferenceModal({ references, onClose }: { references: Reference[]; onClose: () => void }) {
  const { t } = useTranslation()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose() }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) { onClose() } }}
    >
      <div className="mx-4 flex max-h-[70vh] w-full max-w-lg flex-col rounded-2xl border border-stone-200/80 bg-white shadow-2xl dark:border-white/10 dark:bg-[#1a1a1a]">
        <div className="flex items-center justify-between border-b border-stone-100 px-5 py-3.5 dark:border-white/10">
          <p className="text-sm font-medium text-stone-700 dark:text-stone-200">
            {t('references', { count: references.length })}
          </p>
          <button
            type="button"
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-full text-stone-400 transition hover:bg-stone-100 hover:text-stone-600 dark:text-stone-500 dark:hover:bg-white/10 dark:hover:text-stone-300"
          >
            <X size={15} />
          </button>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-5">
          {references.map((ref, i) => (
            <div
              key={i}
              className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 dark:border-white/10 dark:bg-white/5"
            >
              <p className="whitespace-pre-wrap text-[13px] leading-6 text-stone-700 dark:text-stone-300">
                {ref.content}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-stone-400 dark:text-stone-500">
                <span>{t('refScore', { score: ref.score })}</span>
                {ref.source && <span>{ref.source}</span>}
                <span>{ref.collection_id}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function RefTrigger({ references }: { references: Reference[] }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-stone-400 transition hover:text-stone-600 dark:text-stone-500 dark:hover:text-stone-300"
      >
        <BookOpen size={11} />
        {t('references', { count: references.length })}
      </button>
      {open && <ReferenceModal references={references} onClose={() => setOpen(false)} />}
    </>
  )
}

interface ConversationViewProps {
  messages: ChatMessage[]
  loading: boolean
}

function formatTime(date: Date, lang: string): string {
  return date.toLocaleTimeString(lang === 'zh' ? 'zh-CN' : 'en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ConversationView({ messages, loading }: ConversationViewProps) {
  const { t, i18n } = useTranslation()
  const bottomRef = useRef<HTMLDivElement>(null)
  const prevLenRef = useRef(messages.length)
  const lastContent = messages[messages.length - 1]?.content

  useEffect(() => {
    const isNewMessage = messages.length !== prevLenRef.current
    prevLenRef.current = messages.length
    // 流式追加 token → instant，避免 smooth 排队抖动
    const behavior = isNewMessage ? 'smooth' : 'auto'
    bottomRef.current?.scrollIntoView({ behavior })
  }, [lastContent, messages.length])

  if (messages.length === 0) {
    return (
      <div className="mx-auto flex h-full max-w-3xl flex-col justify-center px-6 pb-24">
        <div>
          <p className="text-[42px] font-semibold leading-tight tracking-[-0.04em]">
            {t('emptyTitle')}
          </p>
          <p className="mt-5 max-w-xl text-[15px] leading-7 text-stone-500 dark:text-stone-400">
            {t('emptyDescription')}
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {[t('emptySuggestion1'), t('emptySuggestion2')].map((text) => (
              <div
                key={text}
                className="cursor-pointer rounded-3xl border border-stone-200 bg-white/80 p-4 text-sm leading-6 text-stone-600 shadow-sm transition hover:shadow-md dark:border-white/10 dark:bg-white/5 dark:text-stone-300"
              >
                {text}
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const lastAssistantIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant') { return i }
    }
    return -1
  })()

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-7 px-6 py-10 pb-32">
      {messages.map((message, idx) => {
        const isUser = message.role === 'user'
        const isStreaming = loading && idx === lastAssistantIdx

        return (
          <div
            key={message.id}
            className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={[
                'max-w-[82%] text-[15px] leading-7',
                isUser
                  ? 'rounded-[26px] bg-stone-950 px-5 py-3 text-white shadow-sm dark:bg-stone-700'
                  : 'px-1 py-1 text-stone-900 dark:text-stone-100',
              ].join(' ')}
            >
              {isUser ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              ) : (
                <div className="prose prose-stone prose-sm max-w-none dark:prose-invert">
                  <Streamdown plugins={plugins} isAnimating={isStreaming}>
                    {message.content}
                  </Streamdown>
                </div>
              )}
              <div
                className={[
                  'mt-2 flex items-center justify-between text-[11px]',
                  isUser ? 'text-white/55' : 'text-stone-400 dark:text-stone-500',
                ].join(' ')}
              >
                <div className="flex items-center gap-1.5">
                  {message.inputMode === 'voice' ? (
                    <Mic size={11} />
                  ) : (
                    <Keyboard size={11} />
                  )}
                  {formatTime(message.createdAt, i18n.language)}
                </div>
                {!isUser && message.references && message.references.length > 0 && (
                  <RefTrigger references={message.references} />
                )}
              </div>
            </div>
          </div>
        )
      })}

      {loading && (lastAssistantIdx === -1 || !messages[lastAssistantIdx]?.content) && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2 px-1 py-1 text-sm text-stone-400 dark:text-stone-500">
            <span className="h-2 w-2 animate-pulse rounded-full bg-stone-300 dark:bg-stone-600" />
            {t('thinking')}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
