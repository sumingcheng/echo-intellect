import { useTranslation } from 'react-i18next'
import type { ChatSession } from './chatStore'

interface ChatSidebarProps {
  sessions: ChatSession[]
  currentSessionId: string | null
  onNewSession: () => void
  onSwitchSession: (sessionId: string) => void
  onClearSessions: () => void
}

function formatDate(date: Date, lang: string): string {
  return date.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
  })
}

export default function ChatSidebar({
  sessions,
  currentSessionId,
  onNewSession,
  onSwitchSession,
  onClearSessions,
}: ChatSidebarProps) {
  const { t, i18n } = useTranslation()

  return (
    <aside className="hidden h-screen w-64 shrink-0 flex-col bg-[#f7f7f5] text-stone-900 dark:bg-[#0a0a0a] dark:text-stone-100 md:flex">
      <div className="p-4">
        <button
          type="button"
          onClick={onNewSession}
          className="w-full rounded-2xl bg-stone-950 px-4 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-stone-800 dark:bg-white dark:text-stone-950 dark:hover:bg-stone-200"
        >
          {t('newChat')}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <div className="mb-3 flex items-center justify-between px-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-stone-400 dark:text-stone-500">
            {t('history')}
          </p>
          {sessions.length > 0 && (
            <button
              type="button"
              onClick={onClearSessions}
              className="text-xs text-stone-400 transition hover:text-red-500 dark:text-stone-500"
            >
              {t('clear')}
            </button>
          )}
        </div>

        <div className="space-y-1">
          {sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              onClick={() => onSwitchSession(session.id)}
              className={[
                'w-full rounded-2xl px-3 py-3 text-left transition',
                session.id === currentSessionId
                  ? 'bg-white shadow-sm dark:bg-white/10'
                  : 'text-stone-500 hover:bg-white/60 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-white/5 dark:hover:text-stone-200',
              ].join(' ')}
            >
              <div className="truncate text-sm font-medium">
                {session.title}
              </div>
              <div className="mt-1 text-xs text-stone-400 dark:text-stone-500">
                {formatDate(session.updatedAt, i18n.language)}
              </div>
            </button>
          ))}
        </div>
      </div>

    </aside>
  )
}
