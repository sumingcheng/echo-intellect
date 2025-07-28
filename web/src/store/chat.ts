import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: {
    processing_time: number
    tokens_used: number
    relevance_score: number
    retrieved_chunks_count: number
  }
}

export interface Session {
  id: string
  title: string
  messages: Message[]
  lastUpdated: Date
  createdAt: Date
}

interface ChatStore {
  sessions: Session[]
  currentSessionId: string | null

  // Actions
  createSession: () => string
  switchSession: (sessionId: string) => void
  updateSessionTitle: (sessionId: string, title: string) => void
  addMessage: (sessionId: string, message: Message) => void
  deleteSession: (sessionId: string) => void
  clearAllSessions: () => void
  getCurrentSession: () => Session | null
  getCurrentMessages: () => Message[]
}

// 生成会话标题
const generateSessionTitle = (firstMessage?: string): string => {
  if (!firstMessage) return '新对话'

  // 取前20个字符作为标题
  const title = firstMessage.trim().slice(0, 20)
  return title.length < firstMessage.trim().length ? title + '...' : title
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,

      createSession: () => {
        const newSession: Session = {
          id: crypto.randomUUID(),
          title: '新对话',
          messages: [],
          lastUpdated: new Date(),
          createdAt: new Date(),
        }

        set((state) => {
          const sessions = [newSession, ...state.sessions].slice(0, 20) // 最多保留20个会话
          return {
            sessions,
            currentSessionId: newSession.id,
          }
        })

        return newSession.id
      },

      switchSession: (sessionId: string) => {
        set({ currentSessionId: sessionId })
      },

      updateSessionTitle: (sessionId: string, title: string) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId ? { ...session, title } : session
          ),
        }))
      },

      addMessage: (sessionId: string, message: Message) => {
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id === sessionId) {
              const updatedMessages = [...session.messages, message]
              const updatedSession = {
                ...session,
                messages: updatedMessages,
                lastUpdated: new Date(),
                // 如果是第一条用户消息，更新会话标题
                title: session.messages.length === 0 && message.type === 'user'
                  ? generateSessionTitle(message.content)
                  : session.title,
              }
              return updatedSession
            }
            return session
          })

          // 将当前会话移到最前面
          const currentSessionIndex = sessions.findIndex(s => s.id === sessionId)
          if (currentSessionIndex > 0) {
            const currentSession = sessions.splice(currentSessionIndex, 1)[0]
            sessions.unshift(currentSession)
          }

          return { sessions }
        })
      },

      deleteSession: (sessionId: string) => {
        set((state) => {
          const newSessions = state.sessions.filter(s => s.id !== sessionId)
          const newCurrentId = state.currentSessionId === sessionId
            ? (newSessions.length > 0 ? newSessions[0].id : null)
            : state.currentSessionId

          return {
            sessions: newSessions,
            currentSessionId: newCurrentId,
          }
        })
      },

      clearAllSessions: () => {
        set({
          sessions: [],
          currentSessionId: null,
        })
      },

      getCurrentSession: () => {
        const { sessions, currentSessionId } = get()
        return sessions.find(s => s.id === currentSessionId) || null
      },

      getCurrentMessages: () => {
        const currentSession = get().getCurrentSession()
        return currentSession?.messages || []
      },
    }),
    {
      name: 'chat-sessions',
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name)
          if (!str) return null

          try {
            const parsed = JSON.parse(str)
            // 转换Date字符串为Date对象
            return {
              ...parsed,
              state: {
                ...parsed.state,
                sessions: parsed.state.sessions.map((session: {
                  id: string
                  title: string
                  lastUpdated: string
                  createdAt: string
                  messages: { id: string; type: string; content: string; timestamp: string; metadata?: unknown }[]
                }) => ({
                  ...session,
                  lastUpdated: new Date(session.lastUpdated),
                  createdAt: new Date(session.createdAt),
                  messages: session.messages.map((msg: {
                    id: string
                    type: string
                    content: string
                    timestamp: string
                    metadata?: unknown
                  }) => ({
                    ...msg,
                    timestamp: new Date(msg.timestamp),
                  })),
                })),
              },
            }
          } catch {
            return null
          }
        },
        setItem: (name, value) => {
          try {
            // 转换Date对象为字符串
            const serialized = JSON.stringify({
              ...value,
              state: {
                ...value.state,
                sessions: value.state.sessions.map((session: Session) => ({
                  ...session,
                  lastUpdated: session.lastUpdated.toISOString(),
                  createdAt: session.createdAt.toISOString(),
                  messages: session.messages.map((msg: Message) => ({
                    ...msg,
                    timestamp: msg.timestamp.toISOString(),
                  })),
                })),
              },
            })
            localStorage.setItem(name, serialized)
          } catch {
            // 忽略序列化错误
          }
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    }
  )
) 