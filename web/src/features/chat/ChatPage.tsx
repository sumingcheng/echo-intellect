import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Moon, Sun } from 'lucide-react'
import toast from 'react-hot-toast'
import ChatSidebar from './ChatSidebar'
import ConversationView from './ConversationView'
import KnowledgeStatus from './KnowledgeStatus'
import LanguageSwitch from './LanguageSwitch'
import ModelSelector from './ModelSelector'
import TextComposer from './TextComposer'
import VoiceSession from './VoiceSession'
import { API_BASE, type ChatResponse } from './chatApi'
import { useVoiceChatStore, type ChatMessage } from './chatStore'
import { useModelStore } from './modelStore'
import { useSyncTheme, useThemeStore } from './useTheme'
import { useVoiceSession } from './useVoiceSession'

function createMessage(
  role: ChatMessage['role'],
  content: string,
  inputMode: ChatMessage['inputMode'],
  response?: ChatResponse,
): ChatMessage {
  return {
    id: response?.query_id ?? crypto.randomUUID(),
    role,
    content,
    inputMode,
    createdAt: new Date(),
    metadata: response
      ? {
          processingTime: response.processing_time,
          tokensUsed: response.tokens_used,
          relevanceScore: response.relevance_score,
          retrievedChunksCount: response.retrieved_chunks_count,
        }
      : undefined,
  }
}

export default function ChatPage() {
  const { t } = useTranslation()
  useSyncTheme()
  const dark = useThemeStore((s) => s.dark)
  const toggleTheme = useThemeStore((s) => s.toggle)

  const [loading, setLoading] = useState(false)

  const {
    sessions,
    currentSessionId,
    createSession,
    switchSession,
    addMessage,
    updateMessage,
    clearSessions,
    getCurrentMessages,
  } = useVoiceChatStore()

  const messages = getCurrentMessages()

  useEffect(() => {
    if (sessions.length === 0) {
      createSession()
    }
  }, [createSession, sessions.length])

  const ensureSession = useCallback(() => {
    return currentSessionId ?? createSession()
  }, [createSession, currentSessionId])

  const sendMessage = useCallback(
    async (content: string) => {
      const message = content.trim()
      if (!message || loading) {
        return
      }

      const sessionId = ensureSession()
      addMessage(sessionId, createMessage('user', message, 'text'))
      setLoading(true)

      const assistantId = crypto.randomUUID()
      addMessage(sessionId, {
        id: assistantId,
        role: 'assistant',
        content: '',
        inputMode: 'text',
        createdAt: new Date(),
      })

      try {
        const model = useModelStore.getState().selectedModel || undefined
        const resp = await fetch(`${API_BASE}/api/v1/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            session_id: sessionId,
            model,
            response_mode: 'text',
          }),
        })

        if (!resp.ok || !resp.body) {
          throw new Error(`HTTP ${resp.status}`)
        }

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let accumulated = ''
        let buf = ''
        let rafScheduled = false

        const flushToStore = () => {
          rafScheduled = false
          updateMessage(sessionId, assistantId, { content: accumulated })
        }

        while (true) {
          const { done, value } = await reader.read()
          if (done) { break }

          buf += decoder.decode(value, { stream: true })
          const lines = buf.split('\n')
          buf = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) { continue }
            try {
              const payload = JSON.parse(line.slice(6))
              if (payload.token) {
                accumulated += payload.token
                if (!rafScheduled) {
                  rafScheduled = true
                  requestAnimationFrame(flushToStore)
                }
              }
              if (payload.done) {
                updateMessage(sessionId, assistantId, {
                  content: accumulated,
                  references: payload.references ?? [],
                  metadata: {
                    processingTime: payload.processing_time,
                    tokensUsed: payload.tokens_used,
                    retrievedChunksCount: payload.retrieved_chunks_count,
                  },
                })
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }

        // 确保最后一帧的 token 也刷进去
        updateMessage(sessionId, assistantId, { content: accumulated })
      } catch (error) {
        console.error('chat failed:', error)
        updateMessage(sessionId, assistantId, { content: t('chatError') })
        toast.error(t('chatFailed'))
      } finally {
        setLoading(false)
      }
    },
    [addMessage, updateMessage, ensureSession, loading, t],
  )

  const handleVoiceUserMessage = useCallback(
    (sessionId: string, text: string) => {
      addMessage(sessionId, createMessage('user', text, 'voice'))
    },
    [addMessage],
  )

  const handleVoiceAssistantMessage = useCallback(
    (sessionId: string, response: ChatResponse) => {
      addMessage(sessionId, createMessage('assistant', response.answer, 'text', response))
    },
    [addMessage],
  )

  const voiceSession = useVoiceSession({
    ensureSession,
    onUserMessage: handleVoiceUserMessage,
    onAssistantMessage: handleVoiceAssistantMessage,
  })

  return (
    <div className="flex h-screen bg-[#f7f7f5] text-stone-950 dark:bg-[#0a0a0a] dark:text-stone-50">
      <ChatSidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onNewSession={createSession}
        onSwitchSession={switchSession}
        onClearSessions={clearSessions}
      />

      <main className="relative flex min-w-0 flex-1 flex-col bg-[#fbfaf8] dark:bg-[#111111]">
        <header className="flex h-14 items-center justify-between bg-[#fbfaf8]/90 px-6 backdrop-blur dark:bg-[#111111]/90">
          <div className="flex items-center gap-3">
            <div>
              <p className="text-sm font-semibold">{t('appName')}</p>
              <p className="text-xs text-stone-400 dark:text-stone-500">{t('appSubtitle')}</p>
            </div>
            <ModelSelector />
          </div>
          <div className="flex items-center gap-1">
            <LanguageSwitch />
            <button
              type="button"
              onClick={toggleTheme}
              className="flex h-9 w-9 items-center justify-center rounded-full text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 dark:text-stone-500 dark:hover:bg-white/10 dark:hover:text-stone-300"
              aria-label={t('switchTheme')}
            >
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <KnowledgeStatus />
          </div>
        </header>

        <VoiceSession
          status={voiceSession.status}
          transcript={voiceSession.transcript}
          error={voiceSession.error}
          analyserRef={voiceSession.analyserRef}
          onInterrupt={voiceSession.interrupt}
          onExit={voiceSession.exit}
        />

        <section className="min-h-0 flex-1 overflow-y-auto">
          <ConversationView messages={messages} loading={loading} />
        </section>

        <TextComposer
          loading={loading}
          onSendText={(text) => void sendMessage(text)}
          onStartVoice={() => {
            void voiceSession.start()
          }}
        />
      </main>
    </div>
  )
}
