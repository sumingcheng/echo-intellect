import { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Square } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export default function ChatInput({ onSend, disabled = false, loading = false }: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整高度 - 使用useCallback避免重复创建
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [input, adjustHeight]);

  const handleSend = useCallback(() => {
    if (!input.trim() || disabled || loading) return;
    onSend(input.trim());
    setInput('');
  }, [input, disabled, loading, onSend]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className=" bg-white px-4 py-3">
      <div className="mx-auto max-w-4xl">
        <div className="relative flex items-end gap-3">
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="发送消息..."
              disabled={disabled}
              className="w-full resize-none rounded-xl border border-gray-300 bg-white px-4 py-3 pr-12 text-sm placeholder-gray-500 focus:border-gray-400 focus:outline-none focus:ring-0 disabled:bg-gray-50"
              style={{ minHeight: '52px', maxHeight: '200px' }}
              rows={1}
            />

            {/* 发送/停止按钮 */}
            <div className="absolute bottom-2 right-2">
              {loading ? (
                <Button size="sm" variant="ghost" className="h-8 w-8 rounded-lg p-0 text-gray-500 hover:bg-gray-100" disabled>
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={handleSend} disabled={!input.trim() || disabled} size="sm" className="h-8 w-8 rounded-lg p-0 disabled:opacity-30">
                  <Send className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* 底部提示 */}
        <div className="mt-2 text-center text-xs text-gray-400">AI可能会犯错误，请核实重要信息。</div>
      </div>
    </div>
  );
}
