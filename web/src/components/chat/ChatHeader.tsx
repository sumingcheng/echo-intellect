import { Button } from '@/components/ui/button';
import { MoreHorizontal, Edit3 } from 'lucide-react';
import { type Session } from '@/store/chat';

interface ChatHeaderProps {
  session: Session | null;
  onEditTitle?: () => void;
}

export default function ChatHeader({ session, onEditTitle }: ChatHeaderProps) {
  if (!session) {
    return (
      <div className=" bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-medium text-gray-900">智能问答助手</h1>
            <p className="text-sm text-gray-500">基于您的文档知识库回答问题</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className=" bg-white px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg font-medium text-gray-900">{session.title}</h1>
            <p className="text-sm text-gray-500">
              {session.messages.length} 条消息 · 创建于 {session.createdAt.toLocaleDateString()}
            </p>
          </div>
          {onEditTitle && (
            <Button onClick={onEditTitle} variant="ghost" size="sm" className="h-8 w-8 p-0 text-gray-400 hover:text-gray-600">
              <Edit3 className="h-4 w-4" />
            </Button>
          )}
        </div>

        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-gray-400 hover:text-gray-600">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
