export default {
  // Header
  appName: 'Echo Intellect',
  appSubtitle: 'Local Knowledge Assistant',
  switchTheme: 'Toggle theme',
  knowledgeStatus: 'Knowledge base status',

  // Sidebar
  newChat: 'New Chat',
  history: 'History',
  clear: 'Clear',
  newSession: 'New Chat',

  // Composer
  composerPlaceholder: 'Ask something...',
  composerHint: 'Enter to send · 📎 Upload files · Click mic for voice',
  send: 'Send',
  uploadFile: 'Upload file to knowledge base',
  uploadFileFormats: 'Upload file (.txt .md .pdf)',
  enterVoice: 'Enter voice chat',

  // Conversation
  emptyTitle: 'What shall we talk about?',
  emptyDescription: 'Type a message, or click the mic to start a continuous voice chat. Knowledge base works in the background.',
  emptySuggestion1: 'Summarize the key points in my knowledge base',
  emptySuggestion2: 'What should I focus on recently?',
  thinking: 'Thinking',

  // Voice session
  voiceConnecting: 'Connecting…',
  voiceListening: "I'm listening",
  voiceRecording: 'Keep talking…',
  voiceTranscribing: 'Understanding…',
  voiceThinking: 'Thinking…',
  voiceSpeaking: 'Responding',
  voiceError: 'Something went wrong',
  voiceHint: 'Speak freely, auto-reply after pause',
  voiceInterrupt: 'Interrupt',
  voiceExit: 'Exit voice',
  voiceExitLabel: 'Exit voice',
  voicePlaybackFailed: 'Voice playback failed',
  voiceSessionFailed: 'Voice session failed',
  voiceMicFailed: 'Cannot start microphone',

  // Model selector
  loadingModels: 'Loading models…',
  noModels: 'No models available',
  selectModel: 'Select model',
  fetchModelsFailed: 'Failed to fetch models',

  // Knowledge status
  knowledgeFiles: 'Knowledge Files',
  noFilesYet: 'No files uploaded yet',
  jobPending: 'Queued',
  jobProcessing: 'Processing',
  jobCompleted: 'Completed',
  jobFailed: 'Failed',

  // Upload
  uploadSuccess: '{{name}} uploaded, processing',
  uploadFailed: 'File upload failed',

  // References
  references: '{{count}} references',
  refScore: 'Score {{score}}',

  // Chat
  chatFailed: 'Chat failed',
  chatError: "Couldn't process this time, try again later.",
} as const
