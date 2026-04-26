import { useTranslation } from 'react-i18next'
import { setLanguage } from '@/i18n'

export default function LanguageSwitch() {
  const { i18n } = useTranslation()
  const isEn = i18n.language === 'en'

  return (
    <button
      type="button"
      onClick={() => setLanguage(isEn ? 'zh' : 'en')}
      className="flex h-9 items-center justify-center rounded-full px-2.5 text-xs font-medium text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 dark:text-stone-500 dark:hover:bg-white/10 dark:hover:text-stone-300"
      aria-label="Switch language"
    >
      {isEn ? '中' : 'EN'}
    </button>
  )
}
