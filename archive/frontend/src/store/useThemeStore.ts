import { create } from 'zustand'

interface ThemeState {
  dark: boolean
  toggle: () => void
  setDark: (dark: boolean) => void
}

// Defaulting to light mode by default

export const useThemeStore = create<ThemeState>(() => ({
  dark: false,
  toggle: () => {
    // Disabled for strict light schema
    console.warn('Dark mode is disabled in EventSphere Pastel Theme.');
  },
  setDark: () => {
    // Disabled for strict light schema
  },
}))
