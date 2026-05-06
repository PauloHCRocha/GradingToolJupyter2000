<script setup lang="ts">
import { onMounted } from 'vue'
import { getPyodide, runtimeStage, runtimeError } from './runtime/pyodide'

onMounted(() => {
  // Eagerly start loading Pyodide on app boot so the user is ready by the
  // time they pick their first file. Errors are surfaced via runtimeStage.
  void getPyodide().catch(() => {
    /* runtimeError is already populated */
  })
})

const stageLabel: Record<string, string> = {
  idle: 'Starting…',
  'loading-runtime': 'Downloading Python runtime…',
  'loading-modules': 'Loading grading modules…',
  ready: 'Ready',
  error: 'Failed to load',
}
</script>

<template>
  <Transition name="boot">
    <div v-if="runtimeStage !== 'ready'" class="boot-overlay">
      <div class="boot-card">
        <div class="boot-icon">🐍</div>
        <h1>GradingToolJupyter2000</h1>
        <p class="lead">
          The whole tool runs <strong>inside your browser</strong>.
          Student files <strong>never leave your machine</strong>.
        </p>
        <div class="stage" :class="runtimeStage">
          <span v-if="runtimeStage !== 'error'" class="spin" />
          <span class="stage-text">{{ stageLabel[runtimeStage] ?? runtimeStage }}</span>
        </div>
        <p class="hint">First load can take 10-20s. Subsequent visits are instant (cached).</p>
        <p v-if="runtimeStage === 'error'" class="err">
          {{ runtimeError }}
        </p>
      </div>
    </div>
  </Transition>

  <RouterView v-if="runtimeStage === 'ready'" />
</template>

<style scoped>
.boot-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  z-index: 1000;
}
.boot-card {
  max-width: 480px;
  text-align: center;
  padding: 2rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
}
.boot-icon { font-size: 3rem; margin-bottom: 0.4rem; }
.boot-card h1 { margin: 0 0 0.6rem; font-size: 1.4rem; color: var(--text-strong); }
.boot-card .lead { color: var(--text); font-size: 0.95rem; line-height: 1.5; }
.boot-card .lead strong { color: var(--accent); }

.stage {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  margin: 1.4rem 0 0.8rem;
  padding: 0.55rem 1rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.9rem;
  font-weight: 500;
}
.stage.error {
  background: var(--danger-soft);
  color: var(--danger);
}
.stage .stage-text { letter-spacing: 0.2px; }

.hint { color: var(--text-muted); font-size: 0.8rem; margin: 0; }

.err {
  margin-top: 0.8rem;
  font-size: 0.85rem;
  color: var(--danger);
  background: var(--danger-soft);
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
}

.spin {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.boot-enter-from, .boot-leave-to { opacity: 0; }
.boot-enter-active, .boot-leave-active { transition: opacity 0.25s; }
</style>
