import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Bot } from 'lucide-react';

export default function TypingIndicator() {
  return (
    <div className="flex w-full items-start gap-4">
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className="bg-emerald-500 text-white">
          <Bot className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>

      <div className="flex flex-col items-start">
        <div className="rounded-2xl bg-gray-100 px-4 py-3">
          <div className="flex items-center space-x-1">
            <div className="flex space-x-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
            </div>
            <span className="ml-2 text-sm text-gray-600">AI正在思考...</span>
          </div>
        </div>
      </div>
    </div>
  );
}
