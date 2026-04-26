export default {
  // Header
  appName: 'Echo Intellect',
  appSubtitle: '本地知识库助手',
  switchTheme: '切换主题',
  knowledgeStatus: '知识库状态',

  // Sidebar
  newChat: '新对话',
  history: 'History',
  clear: '清空',
  newSession: '新对话',

  // Composer
  composerPlaceholder: '问点什么...',
  composerHint: 'Enter 发送 · 📎 上传知识库文件 · 点击麦克风进入语音',
  send: '发送',
  uploadFile: '上传文件到知识库',
  uploadFileFormats: '上传文件到知识库 (.txt .md .pdf)',
  enterVoice: '进入语音聊天',

  // Conversation
  emptyTitle: '今天想聊点什么？',
  emptyDescription: '输入一句话，或者点击麦克风进入持续语音聊天。知识库在后台工作，界面只保留对话。',
  emptySuggestion1: '总结一下我的知识库里有哪些重点',
  emptySuggestion2: '我最近应该优先关注什么？',
  thinking: '正在思考',

  // Voice session
  voiceConnecting: '正在连接…',
  voiceListening: '我在听',
  voiceRecording: '继续说…',
  voiceTranscribing: '正在理解…',
  voiceThinking: '思考中…',
  voiceSpeaking: '正在回答',
  voiceError: '出了点问题',
  voiceHint: '直接说话，停顿后自动回答',
  voiceInterrupt: '打断',
  voiceExit: '退出语音',
  voiceExitLabel: '退出语音',
  voicePlaybackFailed: '语音播放失败',
  voiceSessionFailed: '语音会话失败',
  voiceMicFailed: '无法启动麦克风',

  // Model selector
  loadingModels: '加载模型…',
  noModels: '无可用模型',
  selectModel: 'Select model',
  fetchModelsFailed: '获取模型列表失败',

  // Knowledge status
  knowledgeFiles: '知识库文件',
  noFilesYet: '还没有上传文件',
  jobPending: '排队中',
  jobProcessing: '处理中',
  jobCompleted: '已完成',
  jobFailed: '失败',

  // Upload
  uploadSuccess: '{{name}} 已上传，正在处理',
  uploadFailed: '文件上传失败',

  // References
  references: '{{count}} 条引用',
  refScore: '相关度 {{score}}',

  // Chat
  chatFailed: '对话失败',
  chatError: '这次没处理成功，请稍后再试。',
} as const
