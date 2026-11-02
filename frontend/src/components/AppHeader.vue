<script setup lang="ts">
/**
 * Header shared by the workspace pages: the brand, the workflow steps as
 * tabs (a step opens once what it needs is loaded), page actions and the
 * theme toggle.
 */
import { computed } from 'vue'
import { useSessionStore } from '../stores/session'
import { useAutogradeStore } from '../stores/autograde'
import BrandMark from './BrandMark.vue'
import ThemeToggle from './ThemeToggle.vue'

defineProps<{ subtitle?: string }>()

const session = useSessionStore()
const autograde = useAutogradeStore()

const ready = computed(() => session.enabledQuestions.length > 0 && session.students.length > 0)
const steps = computed(() => [
  { to: '/setup', label: 'Setup', enabled: true, hint: '' },
  { to: '/grading', label: 'Grading', enabled: ready.value, hint: 'Load a solution and submissions first' },
  {
    to: '/autograde',
    label: 'Auto-grade',
    enabled: ready.value,
    hint: 'Load a solution and submissions first',
    badge: autograde.pendingCount,
  },
  {
    to: '/plagiarism',
    label: 'Plagiarism',
    enabled: session.students.length >= 2,
    hint: 'Needs at least 2 submissions',
  },
])
</script>

<template>
  <header class="appbar app-header">
    <RouterLink to="/" class="brand" title="Back to the start page">
      <BrandMark />
      <span class="brand-text">
        <span class="name">Granymede</span>
        <span v-if="subtitle" class="subtitle">{{ subtitle }}</span>
      </span>
    </RouterLink>

    <nav class="steps" aria-label="Workflow">
      <template v-for="s in steps" :key="s.to">
        <RouterLink v-if="s.enabled" :to="s.to" class="step" active-class="active">
          {{ s.label }}
          <span v-if="s.badge" class="badge" :title="`${s.badge} grade(s) to review`">{{ s.badge }}</span>
        </RouterLink>
        <span v-else class="step disabled" aria-disabled="true" :title="s.hint">{{ s.label }}</span>
      </template>
    </nav>

    <div class="actions">
      <slot name="actions" />
      <ThemeToggle />
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 1rem;
  padding: 0.6rem 1.25rem;
  background: linear-gradient(180deg, var(--header-bg), var(--header-bg-2));
  color: var(--header-text);
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.12);
}

.brand {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  justify-self: start;
  color: inherit;
  text-decoration: none;
  padding: 0.2rem 0.45rem;
  margin: -0.2rem -0.45rem;
  border-radius: 8px;
  font-size: 1.25rem;
  transition: background 0.15s;
}
.brand:hover { background: rgba(255, 255, 255, 0.08); text-decoration: none; }
.brand-text { display: flex; flex-direction: column; min-width: 0; line-height: 1.2; }
.name { font-weight: 700; letter-spacing: -0.015em; }
.subtitle {
  font-size: 0.74rem;
  color: rgba(255, 255, 255, 0.72);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.steps {
  display: flex;
  gap: 0.2rem;
  padding: 0.25rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.38rem 0.95rem;
  border-radius: 7px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.88rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.step:hover { background: rgba(255, 255, 255, 0.1); color: #fff; text-decoration: none; }
.step.active { background: #fff; color: var(--header-bg); font-weight: 600; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18); }
:root[data-theme='dark'] .step.active { background: rgba(255, 255, 255, 0.16); color: #fff; }
.step.disabled { opacity: 0.4; cursor: not-allowed; }
.badge {
  min-width: 1.25rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: var(--ai);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1.25rem;
  text-align: center;
}

.actions { justify-self: end; display: flex; align-items: center; gap: 0.5rem; }
.actions :deep(.btn) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
  color: #fff;
}
.actions :deep(.btn:hover:not(:disabled)) { background: rgba(255, 255, 255, 0.2); }
.actions :deep(.btn-primary) { background: var(--primary); border-color: var(--primary); }
.actions :deep(.btn-primary:hover:not(:disabled)) { background: var(--primary-hover); border-color: var(--primary-hover); }

@media (max-width: 980px) {
  .app-header { grid-template-columns: 1fr auto; }
  .steps { grid-column: 1 / -1; grid-row: 2; justify-self: center; }
}
@media (max-width: 560px) {
  .step { padding: 0.35rem 0.6rem; font-size: 0.82rem; }
  .subtitle { display: none; }
}
</style>
