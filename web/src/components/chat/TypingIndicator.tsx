import { RiRobotFill } from 'react-icons/ri';

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 text-gray-500 p-4">
      <RiRobotFill className="h-6 w-6 text-blue-500" />
      <div className="flex items-center gap-1">
        <span className="text-sm">AI正在思考</span>
        <div className="flex gap-1">
          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
    </div>
  );
}
