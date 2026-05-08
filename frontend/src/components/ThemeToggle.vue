<script setup lang="ts">
import { theme, toggleTheme } from '../runtime/theme'
</script>

<template>
  <button
    type="button"
    class="theme-toggle"
    :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
    :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="toggleTheme"
  >
    <svg
      v-if="theme === 'dark'"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <!-- Sun -->
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M3 12h2M19 12h2M5.5 18.5l1.4-1.4M17.1 6.9l1.4-1.4" />
    </svg>
    <svg
      v-else
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <!-- Moon -->
      <path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5Z" />
    </svg>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 6px;
  border: 1px solid var(--border-strong);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  padding: 0;
  transition: background 0.15s, border-color 0.15s, transform 0.1s;
}
.theme-toggle:hover { background: var(--bg-soft); border-color: var(--accent); color: var(--accent); }
.theme-toggle:active { transform: scale(0.95); }
.theme-toggle svg { width: 18px; height: 18px; }

/* When the toggle sits inside a navy appbar, override the surface so it
   keeps the same translucent-on-navy treatment as the other appbar
   buttons in light mode. Same in dark mode — navy is unchanged. */
:where(.appbar, .topnav) .theme-toggle {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
  color: white;
}
:where(.appbar, .topnav) .theme-toggle:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
  color: white;
}
</style>
