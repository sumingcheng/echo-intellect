import { useChatStore } from '@/store/chat';
import { RiMoreFill, RiPencilFill } from 'react-icons/ri';

export default function ChatHeader() {
  const { getCurrentSession } = useChatStore();
  const currentSession = getCurrentSession();

  if (!currentSession) {
    return null;
  }

  const messageCount = currentSession.messages.length;
  const createdAt = currentSession.createdAt.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="border-gray-200 bg-white px-6 py-4">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex-1">
          <h1 className="text-lg font-semibold text-gray-900 truncate">{currentSession.title}</h1>
          <p className="text-sm text-gray-500">
            {messageCount} 条消息 • 创建于 {createdAt}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <RiPencilFill className="h-4 w-4 text-gray-600" />
          </button>
          <button className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <RiMoreFill className="h-4 w-4 text-gray-600" />
          </button>
        </div>
      </div>
    </div>
  );
}
