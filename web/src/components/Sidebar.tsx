import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useChatStore } from '@/store/chat';
import { Plus, MessageSquare, Trash2, Edit3, Check, X, Star, ExternalLink } from 'lucide-react';
import { useState, useEffect, useCallback, useMemo } from 'react';

export default function Sidebar() {
  const {
    sessions,
    currentSessionId,
    createSession,
    switchSession,
    deleteSession,
    updateSessionTitle
  } = useChatStore();

  const [hoveredSession, setHoveredSession] = useState<string | null>(null);
  const [editingSession, setEditingSession] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [starCount, setStarCount] = useState<number>(4); // 默认值

  // 使用useMemo缓存计算结果
  const isEmpty = useMemo(() => sessions.length === 0, [sessions.length]);

  // 获取GitHub star数量
  useEffect(() => {
    const fetchStarCount = async () => {
      try {
        const response = await fetch('https://api.github.com/repos/sumingcheng/echo-intellect');
        const data = await response.json();
        setStarCount(data.stargazers_count || 4);
      } catch {
        console.log('获取star数量失败，使用默认值');
        setStarCount(4);
      }
    };

    fetchStarCount();
  }, []);

  const handleNewChat = useCallback(() => {
    createSession();
  }, [createSession]);

  const handleDeleteSession = useCallback((sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (sessions.length > 1) {
      deleteSession(sessionId);
    }
  }, [sessions.length, deleteSession]);

  const handleEditStart = useCallback((sessionId: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSession(sessionId);
    setEditTitle(currentTitle);
  }, []);

  const handleEditConfirm = useCallback((sessionId: string) => {
    if (editTitle.trim()) {
      updateSessionTitle(sessionId, editTitle.trim());
    }
    setEditingSession(null);
    setEditTitle('');
  }, [editTitle, updateSessionTitle]);

  const handleEditCancel = useCallback(() => {
    setEditingSession(null);
    setEditTitle('');
  }, []);

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
        <Button
          onClick={handleNewChat}
          size="sm"
          className="h-9 w-9 rounded-lg p-0"
          variant="outline"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* 会话列表 */}
      <ScrollArea className="flex-1">
        <div className="space-y-2 p-3">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <MessageSquare className="h-8 w-8 mb-3 text-gray-400" />
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
                onClick={() => !editingSession && switchSession(session.id)}
                onMouseEnter={() => !editingSession && setHoveredSession(session.id)}
                onMouseLeave={() => setHoveredSession(null)}
              >
                <div className="p-3">
                  {editingSession === session.id ? (
                    // 编辑状态
                    <div className="flex items-center gap-2" style={{ minHeight: '40px' }}>
                      <div className="flex-1 flex flex-col gap-2">
                        <input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              handleEditConfirm(session.id);
                            } else if (e.key === 'Escape') {
                              handleEditCancel();
                            }
                          }}
                          autoFocus
                        />
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-xs text-green-600 hover:bg-green-100"
                            onClick={() => handleEditConfirm(session.id)}
                          >
                            <Check className="h-3 w-3 mr-1" />
                            确认
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-xs text-red-600 hover:bg-red-100"
                            onClick={handleEditCancel}
                          >
                            <X className="h-3 w-3 mr-1" />
                            取消
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    // 正常显示状态
                    <div className="flex items-center justify-between" style={{ minHeight: '40px' }}>
                      <div className="flex-1 min-w-0">
                        <h3 className={`text-sm font-medium truncate ${
                          session.id === currentSessionId
                            ? 'text-blue-900'
                            : 'text-gray-800'
                        }`}>
                          {session.title}
                        </h3>
                        
                        <p className={`text-xs mt-1 ${
                          session.id === currentSessionId
                            ? 'text-blue-600'
                            : 'text-gray-500'
                        }`}>
                          {formatTime(session.lastUpdated)}
                        </p>
                      </div>

                      {/* 操作按钮 */}
                      {(hoveredSession === session.id || session.id === currentSessionId) && !editingSession && (
                        <div className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 text-gray-500 hover:text-gray-700 hover:bg-gray-200"
                            onClick={(e) => handleEditStart(session.id, session.title, e)}
                          >
                            <Edit3 className="h-3 w-3" />
                          </Button>
                          {sessions.length > 1 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-gray-500 hover:text-red-500 hover:bg-red-100"
                              onClick={(e) => handleDeleteSession(session.id, e)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* 底部GitHub信息 */}
      <div className="border-t border-gray-200 bg-white">
        <button
          onClick={handleGitHubClick}
          className="w-full p-3 text-left hover:bg-gray-50 transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Star className="h-4 w-4 text-yellow-500" />
              <span className="text-sm font-medium text-gray-700">
                {starCount} stars
              </span>
            </div>
            <ExternalLink className="h-3 w-3 text-gray-400 group-hover:text-gray-600" />
          </div>
          <p className="text-xs text-gray-500 mt-1">
            点击访问 GitHub 仓库
          </p>
        </button>
      </div>
    </div>
  );
}
