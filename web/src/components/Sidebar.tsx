import { ScrollArea } from '@/components/ui/scroll-area';
import { useChatStore } from '@/store/chat';
import { RiAddCircleFill, RiMessage3Fill, RiDeleteBinLine } from 'react-icons/ri';
import { useCallback, useMemo } from 'react';
import toast from 'react-hot-toast';

export default function Sidebar() {
  const { sessions, currentSessionId, createSession, switchSession, clearAllSessions } = useChatStore();

  // 使用useMemo缓存计算结果
  const isEmpty = useMemo(() => sessions.length === 0, [sessions.length]);
  
  // 检查是否有空的新会话（没有消息的会话）
  const hasEmptySession = useMemo(() => {
    return sessions.some(session => session.messages.length === 0);
  }, [sessions]);

  const handleNewChat = useCallback(() => {
    // 如果已经有空会话，就不创建新的
    if (hasEmptySession) {
      const emptySession = sessions.find(session => session.messages.length === 0);
      if (emptySession) {
        switchSession(emptySession.id);
        toast.success('已切换到空会话');
        return;
      }
    }
    createSession();
    toast.success('已创建新会话');
  }, [createSession, switchSession, hasEmptySession, sessions]);

  const handleClearAllSessions = useCallback(() => {
    // 使用toast进行确认
    toast((t) => (
      <div className="flex flex-col gap-3">
        <div>
          <p className="font-medium text-gray-900">确定要清空所有聊天记录吗？</p>
          <p className="text-sm text-gray-500 mt-1">此操作不可撤销</p>
        </div>
        <div className="flex gap-2">
          <button
            className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600 transition-colors"
            onClick={() => {
              clearAllSessions();
              toast.dismiss(t.id);
              toast.success('已清空所有会话');
            }}
          >
            确定清空
          </button>
          <button
            className="px-3 py-1 bg-gray-200 text-gray-800 rounded text-sm hover:bg-gray-300 transition-colors"
            onClick={() => toast.dismiss(t.id)}
          >
            取消
          </button>
        </div>
      </div>
    ), {
      duration: 0, // 不自动消失
      style: {
        background: '#fff',
        color: '#000',
        maxWidth: '400px',
      },
    });
  }, [clearAllSessions]);

  const handleGitHubClick = useCallback(() => {
    window.open('https://github.com/sumingcheng/echo-intellect', '_blank');
  }, []);

  const formatTime = useCallback((date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } else if (diffDays === 1) {
      return '昨天';
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric',
      });
    }
  }, []);

  return (
    <div className="flex h-full w-80 flex-col border-r border-gray-200 bg-gray-50">
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-semibold text-gray-900">聊天记录</h2>
        <div className="flex items-center gap-2">
          {/* 清空按钮 */}
          {!isEmpty && (
            <div className="h-8 w-8 rounded-full cursor-pointer flex items-center justify-center hover:bg-gray-100 transition-colors" onClick={handleClearAllSessions}>
              <RiDeleteBinLine className="h-5 w-5 text-gray-600" />
            </div>
          )}
          
          {/* 新建按钮 */}
          <div className="h-10 w-10 rounded-full bg-blue-50 hover:bg-blue-100 transition-colors cursor-pointer flex items-center justify-center" onClick={handleNewChat}>
            <RiAddCircleFill className="h-8 w-8 text-blue-600" />
          </div>
        </div>
      </div>

      {/* 会话列表 */}
      <ScrollArea className="flex-1">
        <div className="space-y-1 p-2">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <RiMessage3Fill className="h-10 w-10 mb-3 text-gray-400" />
              <p className="text-sm text-center">暂无聊天记录</p>
              <p className="text-xs text-gray-400 mt-1">开始新对话吧</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`group relative rounded-lg cursor-pointer transition-all duration-200 ${
                  session.id === currentSessionId
                    ? 'bg-white shadow-sm border border-blue-200 ring-1 ring-blue-100'
                    : 'bg-gray-100/80 border border-gray-200 hover:bg-white hover:shadow-sm'
                }`}
                onClick={() => switchSession(session.id)}
              >
                <div className="flex items-center justify-between px-3 py-2 min-h-[44px]">
                  <h3 className={`text-sm font-medium truncate flex-1 mr-2 ${session.id === currentSessionId ? 'text-blue-900' : 'text-gray-800'}`}>{session.title}</h3>

                  <span className={`text-xs shrink-0 ${session.id === currentSessionId ? 'text-blue-600' : 'text-gray-500'}`}>{formatTime(session.lastUpdated)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* 底部GitHub徽章 */}
      <div className="border-t border-gray-200 bg-white">
        <button onClick={handleGitHubClick} className="w-full p-3 text-left hover:bg-gray-50 transition-colors group flex items-center justify-center">
          <img
            src="https://img.shields.io/github/stars/sumingcheng/echo-intellect?logo=github&style=social"
            alt="GitHub Stars"
            className="h-5 group-hover:scale-105 transition-transform"
          />
        </button>
      </div>
    </div>
  );
}
