import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Bot, User } from 'lucide-react'
import { type Message } from '@/store/chat'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

interface MessageBubbleProps {
  message: Message
  showMetadata?: boolean
}

export default function MessageBubble({ message, showMetadata = true }: MessageBubbleProps) {
  const isUser = message.type === 'user'

  return (
    <div className={`flex w-full items-start gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-emerald-500 text-white">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
      
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
        <div 
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          {isUser ? (
            // 用户消息显示为纯文本
            <div className="whitespace-pre-wrap break-words">
              {message.content}
            </div>
          ) : (
            // AI消息支持Markdown渲染
            <div className="prose prose-sm max-w-none prose-headings:my-2 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-pre:my-2 prose-code:text-sm">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  // 自定义代码块样式
                  code: ({ className, children, ...props }: any) => {
                    const isInline = !className?.includes('language-')
                    if (isInline) {
                      return (
                        <code
                          className="rounded bg-gray-200 px-1 py-0.5 text-xs font-mono text-gray-800"
                          {...props}
                        >
                          {children}
                        </code>
                      )
                    }
                    return (
                      <code
                        className={`${className} text-sm font-mono`}
                        {...props}
                      >
                        {children}
                      </code>
                    )
                  },
                  // 自定义pre标签样式 - 深色代码块
                  pre: ({ children }) => (
                    <pre 
                      className="overflow-x-auto rounded-lg bg-gray-900 p-4 text-gray-100 border"
                      style={{
                        background: '#1a1a1a',
                        color: '#f8f8f2'
                      }}
                    >
                      {children}
                    </pre>
                  ),
                  // 自定义链接样式
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 underline hover:text-blue-800"
                    >
                      {children}
                    </a>
                  ),
                  // 自定义表格样式
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-2">
                      <table className="min-w-full border-collapse border border-gray-300 text-xs">
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-gray-300 bg-gray-50 px-2 py-1 text-left font-semibold text-gray-800">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-gray-300 px-2 py-1 text-gray-700">
                      {children}
                    </td>
                  ),
                  // 自定义块引用样式
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-blue-400 pl-4 py-2 bg-blue-50 italic text-gray-700 my-2">
                      {children}
                    </blockquote>
                  ),
                  // 自定义列表样式
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside space-y-1 my-2">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside space-y-1 my-2">
                      {children}
                    </ol>
                  ),
                  // 自定义标题样式
                  h1: ({ children }) => (
                    <h1 className="text-lg font-bold text-gray-900 mt-4 mb-2 border-b border-gray-200 pb-1">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-base font-semibold text-gray-900 mt-3 mb-2">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-sm font-semibold text-gray-900 mt-2 mb-1">
                      {children}
                    </h3>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        
        {/* 时间戳 */}
        <div className="mt-1 text-xs text-gray-500">
          {message.timestamp.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>

        {/* 元数据 */}
        {showMetadata && message.metadata && (
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-400">
            <span className="rounded bg-gray-100 px-2 py-1">
              ⏱️ {message.metadata.processing_time.toFixed(2)}s
            </span>
            <span className="rounded bg-gray-100 px-2 py-1">
              🔤 {message.metadata.tokens_used}
            </span>
            <span className="rounded bg-gray-100 px-2 py-1">
              🎯 {message.metadata.relevance_score.toFixed(2)}
            </span>
            <span className="rounded bg-gray-100 px-2 py-1">
              📄 {message.metadata.retrieved_chunks_count}
            </span>
          </div>
        )}
      </div>

      {isUser && (
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-blue-600 text-white">
            <User className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  )
}
