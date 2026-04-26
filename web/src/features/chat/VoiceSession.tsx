import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import AudioOrb from './AudioOrb'
import type { VoiceSessionError, VoiceSessionStatus } from './voiceTypes'

interface VoiceSessionProps {
  status: VoiceSessionStatus
  transcript: string
  error: VoiceSessionError | null
  analyserRef: React.RefObject<AnalyserNode | null>
  onInterrupt: () => void
  onExit: () => void
}

const LABEL_KEY: Record<VoiceSessionStatus, string> = {
  inactive: '',
  entering: 'voiceConnecting',
  listening: 'voiceListening',
  recording: 'voiceRecording',
  transcribing: 'voiceTranscribing',
  thinking: 'voiceThinking',
  speaking: 'voiceSpeaking',
  error: 'voiceError',
}

export default function VoiceSession({
  status,
  transcript,
  error,
  analyserRef,
  onInterrupt,
  onExit,
}: VoiceSessionProps) {
  const { t } = useTranslation()
  const active = status !== 'inactive'
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (active) {
      setMounted(true)
    } else if (mounted) {
      const timer = setTimeout(() => setMounted(false), 500)
      return () => clearTimeout(timer)
    }
  }, [active, mounted])

  if (!mounted) {
    return null
  }

  return (
    <div
      className={[
        'fixed inset-0 z-50 flex flex-col items-center bg-[#0a0a0a] transition-opacity duration-500',
        active ? 'opacity-100' : 'opacity-0 pointer-events-none',
      ].join(' ')}
    >
      <button
        type="button"
        onClick={onExit}
        className="absolute right-5 top-5 z-10 flex h-10 w-10 items-center justify-center rounded-full text-white/30 transition hover:bg-white/10 hover:text-white/60"
        aria-label={t('voiceExitLabel')}
      >
        <X size={20} />
      </button>

      <div className="flex flex-1 items-center justify-center pb-20">
        <div className="flex flex-col items-center">
          <AudioOrb status={status} analyserRef={analyserRef} size={380} />

          <p className="mt-6 text-lg font-medium tracking-wide text-white/80">
            {LABEL_KEY[status] ? t(LABEL_KEY[status]) : ''}
          </p>

          <div className="mt-3 min-h-10 max-w-sm text-center text-sm leading-relaxed text-white/35">
            {error ? (
              <p className="text-red-400/80">{error.message}</p>
            ) : transcript ? (
              <p>&ldquo;{transcript}&rdquo;</p>
            ) : status === 'listening' ? (
              <p>{t('voiceHint')}</p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 pb-12">
        {status === 'speaking' && (
          <button
            type="button"
            onClick={onInterrupt}
            className="rounded-full border border-white/15 bg-white/10 px-6 py-3 text-sm font-medium text-white/80 backdrop-blur transition hover:bg-white/20 hover:text-white"
          >
            {t('voiceInterrupt')}
          </button>
        )}

        <button
          type="button"
          onClick={onExit}
          className="rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm text-white/40 transition hover:bg-white/10 hover:text-white/60"
        >
          {t('voiceExit')}
        </button>
      </div>
    </div>
  )
}
