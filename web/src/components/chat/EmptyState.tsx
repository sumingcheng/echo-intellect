import { MessageCircle, Lightbulb, BookOpen, HelpCircle } from 'lucide-react';

const suggestions = [
  {
    icon: Lightbulb,
    title: '创意灵感',
    description: '帮我想一些创新的想法',
  },
  {
    icon: BookOpen,
    title: '知识问答',
    description: '基于文档回答专业问题',
  },
  {
    icon: HelpCircle,
    title: '问题解答',
    description: '解释复杂的概念和流程',
  },
];

interface EmptyStateProps {
  onSuggestionClick: (suggestion: string) => void;
}

export default function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
      <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 text-white">
        <MessageCircle className="h-8 w-8" />
      </div>

      <h2 className="mb-2 text-2xl font-semibold text-gray-900">你好！我是智能问答助手</h2>

      <p className="mb-8 text-center text-gray-600">我可以基于您的文档知识库回答问题，提供准确的信息和建议。</p>

      <div className="grid w-full max-w-2xl grid-cols-1 gap-3 md:grid-cols-3">
        {suggestions.map((suggestion, index) => {
          const Icon = suggestion.icon;
          return (
            <button
              key={index}
              onClick={() => onSuggestionClick(suggestion.description)}
              className="rounded-lg border border-gray-200 bg-white p-4 text-left transition-colors hover:bg-gray-50 hover:border-gray-300"
            >
              <div className="mb-2 flex items-center gap-2">
                <Icon className="h-5 w-5 text-gray-600" />
                <span className="font-medium text-gray-900">{suggestion.title}</span>
              </div>
              <p className="text-sm text-gray-600">{suggestion.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
