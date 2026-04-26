import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ModelState {
  selectedModel: string
  setModel: (id: string) => void
}

export const useModelStore = create<ModelState>()(
  persist(
    (set) => ({
      selectedModel: '',
      setModel: (id: string) => set({ selectedModel: id }),
    }),
    { name: 'echo-model' },
  ),
)
