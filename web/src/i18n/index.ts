import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en'
import zh from './zh'

const STORAGE_KEY = 'echo-lang'

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    zh: { translation: zh },
  },
  lng: localStorage.getItem(STORAGE_KEY) || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export function setLanguage(lng: string) {
  i18n.changeLanguage(lng)
  localStorage.setItem(STORAGE_KEY, lng)
}

export function getLanguage(): string {
  return i18n.language
}

export default i18n
