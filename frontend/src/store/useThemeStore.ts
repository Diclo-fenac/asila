import { create } from 'zustand'

interface ThemeState {
  dark: boolean
  toggle: () => void
  setDark: (dark: boolean) => void
}

// Detect system preference
function getSystemPreference(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

// Check localStorage for user override
function getStoredPreference(): boolean | null {
  try {
    const stored = localStorage.getItem('aasila_theme')
    if (stored === 'dark') return true
    if (stored === 'light') return false
  } catch {
    // ignore
  }
  return null
}

const initialDark = getStoredPreference() ?? getSystemPreference()

// Apply class on init
if (typeof document !== 'undefined') {
  if (initialDark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

export const useThemeStore = create<ThemeState>((set) => ({
  dark: initialDark,
  toggle: () =>
    set((state) => {
      const next = !state.dark
      if (typeof document !== 'undefined') {
        document.documentElement.classList.toggle('dark', next)
      }
      try {
        localStorage.setItem('aasila_theme', next ? 'dark' : 'light')
      } catch {
        // ignore
      }
      return { dark: next }
    }),
  setDark: (dark) => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', dark)
    }
    try {
      localStorage.setItem('aasila_theme', dark ? 'dark' : 'light')
    } catch {
      // ignore
    }
    set({ dark })
  },
}))
