export type VoiceSessionStatus =
  | 'inactive'
  | 'entering'
  | 'listening'
  | 'recording'
  | 'transcribing'
  | 'thinking'
  | 'speaking'
  | 'error'

export interface VoiceSessionError {
  message: string
}
