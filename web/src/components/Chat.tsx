import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useChatStore, type Message } from '@/store/chat'
import queryService, { type QueryRequest, type QueryResponse } from '@/http/query'
import Sidebar from './Sidebar'
import ChatHeader from './chat/ChatHeader'
import MessageBubble from './chat/MessageBubble'
import TypingIndicator from './chat/TypingIndicator'
import ChatInput from './chat/ChatInput'
import EmptyState from './chat/EmptyState'

export default function Chat() {
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    sessions,
    currentSessionId,
    createSession,
    addMessage,
    getCurrentSession,
    getCurrentMessages,
  } = useChatStore()

  const currentSession = getCurrentSession()
  const messages = getCurrentMessages()

  // 使用useMemo缓存计算结果
  const isEmpty = useMemo(() => messages.length === 0, [messages.length])

  // 初始化：如果没有会话则创建一个
  useEffect(() => {
    if (sessions.length === 0) {
      createSession()
    }
  }, [sessions.length, createSession])

  // 自动滚动到底部 - 使用useCallback避免重复创建
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading, scrollToBottom])

  // 发送消息 - 使用useCallback避免重复创建
  const handleSend = useCallback(async (content: string) => {
    if (!content.trim() || loading || !currentSessionId) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      type: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }

    // 添加用户消息到当前会话
    addMessage(currentSessionId, userMessage)
    setLoading(true)

    try {
      const queryParams: QueryRequest = {
        question: userMessage.content,
        session_id: currentSessionId,
      }

      const response: QueryResponse = await queryService.query(queryParams)

      const assistantMessage: Message = {
        id: response.query_id,
        type: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        metadata: {
          processing_time: response.processing_time,
          tokens_used: response.tokens_used,
          relevance_score: response.relevance_score,
          retrieved_chunks_count: response.retrieved_chunks_count,
        },
      }

      // 添加AI回复到当前会话
      addMessage(currentSessionId, assistantMessage)
    } catch (error) {
      console.error('查询失败:', error)
      
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: '抱歉，处理您的问题时出现了错误，请稍后重试。',
        timestamp: new Date(),
      }

      addMessage(currentSessionId, errorMessage)
    } finally {
      setLoading(false)
    }
  }, [loading, currentSessionId, addMessage])

  // 处理建议点击 - 使用useCallback
  const handleSuggestionClick = useCallback((suggestion: string) => {
    handleSend(suggestion)
  }, [handleSend])

  return (
    <div className="flex h-screen bg-white">
      {/* 左侧边栏 */}
      <Sidebar />

      {/* 右侧聊天区域 */}
      <div className="flex flex-1 flex-col">
        {/* 头部 */}
        <ChatHeader session={currentSession} />

        {/* 消息区域 */}
        <div className="flex-1 overflow-hidden bg-white">
          {isEmpty ? (
            <EmptyState onSuggestionClick={handleSuggestionClick} />
          ) : (
            <ScrollArea className="h-full">
              <div className="mx-auto max-w-4xl px-4">
                <div className="space-y-6 py-6">
                  {messages.map((message) => (
                    <MessageBubble
                      key={message.id}
                      message={message}
                      showMetadata={message.type === 'assistant'}
                    />
                  ))}

                  {/* 加载指示器 */}
                  {loading && <TypingIndicator />}

                  <div ref={messagesEndRef} />
                </div>
              </div>
            </ScrollArea>
          )}
        </div>

        {/* 输入框 */}
        <ChatInput
          onSend={handleSend}
          disabled={!currentSessionId}
          loading={loading}
        />
      </div>
    </div>
  )
}
