import { RiMessage3Fill, RiLightbulbFill, RiBookOpenFill, RiQuestionFill } from 'react-icons/ri';

interface EmptyStateProps {
  onSuggestionClick: (suggestion: string) => void;
}

export default function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  const suggestions = [
    {
      icon: RiLightbulbFill,
      title: "创意思考",
      description: "帮我想一些创新的想法",
      prompt: "我正在开发一个新产品，能帮我想一些创新的功能想法吗？"
    },
    {
      icon: RiBookOpenFill,
      title: "学习助手",
      description: "解释复杂的概念",
      prompt: "能否详细解释一下机器学习的基本概念？"
    },
    {
      icon: RiQuestionFill,
      title: "问题解答",
      description: "回答你的疑问",
      prompt: "我想了解区块链技术的原理和应用场景"
    }
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center mb-6">
        <RiMessage3Fill className="h-8 w-8 text-blue-600" />
      </div>
      
      <h2 className="text-2xl font-semibold text-gray-900 mb-2">
        开始新的对话
      </h2>
      <p className="text-gray-600 mb-8 max-w-md">
        你可以询问任何问题，我会基于知识库为你提供准确的答案
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-4xl">
        {suggestions.map((suggestion, index) => {
          const IconComponent = suggestion.icon;
          return (
            <button
              key={index}
              onClick={() => onSuggestionClick(suggestion.prompt)}
              className="p-4 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:border-blue-300 transition-all duration-200 text-left group"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                  <IconComponent className="h-4 w-4 text-blue-600" />
                </div>
                <h3 className="font-medium text-gray-900">{suggestion.title}</h3>
              </div>
              <p className="text-sm text-gray-600">{suggestion.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
