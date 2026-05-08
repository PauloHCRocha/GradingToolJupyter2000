/**
 * Light/dark theme controller.
 *
 * - Initial value: localStorage > `prefers-color-scheme` > 'light'.
 * - The chosen mode is mirrored as `data-theme="<mode>"` on <html> so
 *   CSS can branch with `:root[data-theme="dark"] { ... }`.
 * - Persisted to localStorage so it survives page reloads.
 */

import { ref, watch } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'gtj-theme'

function detectInitial(): Theme {
  if (typeof window === 'undefined' || typeof document === 'undefined') return 'light'
  const saved = window.localStorage.getItem(STORAGE_KEY) as Theme | null
  if (saved === 'light' || saved === 'dark') return saved
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

function apply(t: Theme): void {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', t)
}

export const theme = ref<Theme>(detectInitial())
apply(theme.value)

watch(theme, (t) => {
  apply(t)
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(STORAGE_KEY, t)
    } catch {
      /* private mode / quota — ignore */
    }
  }
})

export function toggleTheme(): void {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}
