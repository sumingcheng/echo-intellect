import { useEffect } from 'react'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ThemeState {
  dark: boolean
  toggle: () => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      dark: false,
      toggle: () => set((s) => ({ dark: !s.dark })),
    }),
    { name: 'echo-theme' },
  ),
)

/** 放在 App 顶层，同步 .dark class 到 <html> */
export function useSyncTheme() {
  const dark = useThemeStore((s) => s.dark)
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])
}
