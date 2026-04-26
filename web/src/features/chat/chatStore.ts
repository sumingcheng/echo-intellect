import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type MessageRole = 'user' | 'assistant'

export interface Reference {
  content: string
  score: number
  collection_id: string
  source?: string
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  createdAt: Date
  inputMode?: 'text' | 'voice'
  references?: Reference[]
  metadata?: {
    processingTime?: number
    tokensUsed?: number
    relevanceScore?: number
    retrievedChunksCount?: number
  }
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: Date
  updatedAt: Date
}

interface ChatState {
  sessions: ChatSession[]
  currentSessionId: string | null
  createSession: () => string
  switchSession: (sessionId: string) => void
  addMessage: (sessionId: string, message: ChatMessage) => void
  updateMessage: (sessionId: string, messageId: string, patch: Partial<ChatMessage>) => void
  clearSessions: () => void
  getCurrentSession: () => ChatSession | null
  getCurrentMessages: () => ChatMessage[]
}

function createTitle(content: string): string {
  const title = content.trim().replace(/\s+/g, ' ').slice(0, 18)
  return title ? `${title}${content.length > 18 ? '...' : ''}` : 'New Chat'
}

function createEmptySession(): ChatSession {
  const now = new Date()
  return {
    id: crypto.randomUUID(),
    title: 'New Chat',
    messages: [],
    createdAt: now,
    updatedAt: now,
  }
}

export const useVoiceChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,

      createSession: () => {
        const session = createEmptySession()
        set((state) => ({
          sessions: [session, ...state.sessions].slice(0, 30),
          currentSessionId: session.id,
        }))
        return session.id
      },

      switchSession: (sessionId) => {
        set({ currentSessionId: sessionId })
      },

      addMessage: (sessionId, message) => {
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id !== sessionId) {
              return session
            }

            const isFirstUserMessage =
              session.messages.length === 0 && message.role === 'user'

            return {
              ...session,
              title: isFirstUserMessage ? createTitle(message.content) : session.title,
              messages: [...session.messages, message],
              updatedAt: new Date(),
            }
          })

          const index = sessions.findIndex((session) => session.id === sessionId)
          if (index > 0) {
            const [session] = sessions.splice(index, 1)
            sessions.unshift(session)
          }

          return { sessions }
        })
      },

      updateMessage: (sessionId, messageId, patch) => {
        set((state) => ({
          sessions: state.sessions.map((session) => {
            if (session.id !== sessionId) {
              return session
            }
            return {
              ...session,
              messages: session.messages.map((msg) =>
                msg.id === messageId ? { ...msg, ...patch } : msg,
              ),
            }
          }),
        }))
      },

      clearSessions: () => {
        set({ sessions: [], currentSessionId: null })
      },

      getCurrentSession: () => {
        const { sessions, currentSessionId } = get()
        return sessions.find((session) => session.id === currentSessionId) ?? null
      },

      getCurrentMessages: () => get().getCurrentSession()?.messages ?? [],
    }),
    {
      name: 'voice-chat-sessions',
      storage: {
        getItem: (name) => {
          const value = localStorage.getItem(name)
          if (!value) {
            return null
          }

          try {
            const parsed = JSON.parse(value)
            return {
              ...parsed,
              state: {
                ...parsed.state,
                sessions: parsed.state.sessions.map((session: ChatSession) => ({
                  ...session,
                  createdAt: new Date(session.createdAt),
                  updatedAt: new Date(session.updatedAt),
                  messages: session.messages.map((message: ChatMessage) => ({
                    ...message,
                    createdAt: new Date(message.createdAt),
                  })),
                })),
              },
            }
          } catch {
            return null
          }
        },
        setItem: (name, value) => {
          localStorage.setItem(name, JSON.stringify(value))
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    },
  ),
)
