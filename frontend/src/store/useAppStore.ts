// Deprecated: Migrate to useAuthStore for auth state.
// This store now only provides UI state (theme).
import { create } from 'zustand'

interface UiState {
  theme: 'light' | 'dark'
  toggleTheme: () => void
  setTheme: (theme: 'light' | 'dark') => void
}

export const useAppStore = create<UiState>((set) => ({
  theme: 'light',
  toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
  setTheme: (theme) => set({ theme }),
}))
