import { RiRobotFill, RiUser3Fill } from 'react-icons/ri';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { type Message } from '@/store/chat';

interface MessageBubbleProps {
  message: Message;
  showMetadata?: boolean;
}

export default function MessageBubble({ message, showMetadata = true }: MessageBubbleProps) {
  const isUser = message.type === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
          <RiRobotFill className="h-5 w-5 text-blue-600" />
        </div>
      )}

      <div className={`max-w-[80%] ${isUser ? 'order-first' : ''}`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${isUser ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
          {isUser ? (
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          ) : (
            <div className="prose prose-sm max-w-none prose-headings:my-2 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-pre:my-2 prose-code:text-sm">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code: (props: any) => {
                    const { className, children, ...rest } = props;
                    const isInline = !className;
                    return isInline ? (
                      <code className="bg-gray-200 text-gray-800 px-1 py-0.5 rounded text-xs font-mono" {...rest}>
                        {children}
                      </code>
                    ) : (
                      <code className={`${className} text-sm font-mono`} {...rest}>
                        {children}
                      </code>
                    );
                  },
                  pre: (props: any) => (
                    <pre
                      className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-2"
                      style={{
                        backgroundColor: '#1a202c',
                        color: '#e2e8f0',
                      }}
                    >
                      {props.children}
                    </pre>
                  ),
                  a: (props: any) => (
                    <a href={props.href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline">
                      {props.children}
                    </a>
                  ),
                  table: (props: any) => (
                    <div className="overflow-x-auto my-2">
                      <table className="min-w-full border-collapse border border-gray-300">{props.children}</table>
                    </div>
                  ),
                  th: (props: any) => <th className="border border-gray-300 px-3 py-2 bg-gray-100 font-semibold text-left">{props.children}</th>,
                  td: (props: any) => <td className="border border-gray-300 px-3 py-2">{props.children}</td>,
                  blockquote: (props: any) => <blockquote className="border-l-4 border-gray-400 pl-4 my-2 text-gray-700 italic">{props.children}</blockquote>,
                  ul: (props: any) => <ul className="list-disc pl-5 my-1 space-y-1">{props.children}</ul>,
                  ol: (props: any) => <ol className="list-decimal pl-5 my-1 space-y-1">{props.children}</ol>,
                  h1: (props: any) => <h1 className="text-xl font-bold text-gray-900 my-2">{props.children}</h1>,
                  h2: (props: any) => <h2 className="text-lg font-semibold text-gray-900 my-2">{props.children}</h2>,
                  h3: (props: any) => <h3 className="text-base font-medium text-gray-900 my-2">{props.children}</h3>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {showMetadata && !isUser && message.metadata && (
          <div className="text-xs text-gray-500 mt-2 space-y-1">
            {message.metadata.processing_time && <div>处理时间: {message.metadata.processing_time.toFixed(2)}s</div>}
            {message.metadata.tokens_used && <div>Token使用: {message.metadata.tokens_used}</div>}
            {message.metadata.relevance_score && <div>相关性: {(message.metadata.relevance_score * 100).toFixed(1)}%</div>}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
          <RiUser3Fill className="h-5 w-5 text-white" />
        </div>
      )}
    </div>
  );
}
