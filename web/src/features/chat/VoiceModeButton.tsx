import { useTranslation } from 'react-i18next'
import { Mic } from 'lucide-react'

interface VoiceModeButtonProps {
  onClick: () => void
}

export default function VoiceModeButton({ onClick }: VoiceModeButtonProps) {
  const { t } = useTranslation()

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-stone-100 text-stone-500 transition-all hover:bg-stone-950 hover:text-white hover:shadow-lg active:scale-95 dark:bg-stone-800 dark:text-stone-400 dark:hover:bg-white dark:hover:text-stone-950"
      aria-label={t('enterVoice')}
    >
      <Mic size={18} strokeWidth={2.2} />
    </button>
  )
}
