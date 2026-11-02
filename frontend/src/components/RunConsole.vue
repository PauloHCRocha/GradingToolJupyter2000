<script setup lang="ts">
/**
 * Terminal-style view of a RunConsole. input() prompts get an inline field
 * right after them; Enter answers, and pasting several lines answers
 * several input() calls at once.
 */
import { computed, nextTick, ref, watch } from 'vue'
import type { RunConsole } from '../runtime/runConsole'
import { runnerWarmingUp } from '../runtime/runner'

const props = defineProps<{ run: RunConsole; title: string; variant: 'student' | 'solution' }>()

const screen = ref<HTMLDivElement | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)
const draft = ref('')

const state = computed(() => props.run.state)
const busy = computed(() => state.value.status === 'running')

const statusLabel = computed(() => {
  switch (state.value.status) {
    case 'running':
      return runnerWarmingUp.value ? 'starting Python…' : 'running…'
    case 'waiting':
      return 'waiting for input'
    case 'done':
      return `✓ finished · ${state.value.durationMs} ms`
    case 'error':
      return '✗ error'
    case 'timeout':
      return `⏱ stopped after ${Math.round(state.value.timeoutMs / 1000)} s`
    case 'stopped':
      return 'stopped'
    default:
      return ''
  }
})

// Shown under the output once the program is no longer running.
const footer = computed(() => {
  switch (state.value.status) {
    case 'done':
      return '— program finished —'
    case 'timeout':
      return `The program didn't finish within ${Math.round(state.value.timeoutMs / 1000)} s (infinite loop?).`
    case 'stopped':
      return 'Stopped.'
    default:
      return ''
  }
})

function submit() {
  props.run.submit([draft.value])
  draft.value = ''
}

function onPaste(e: ClipboardEvent) {
  const text = e.clipboardData?.getData('text') ?? ''
  if (!text.includes('\n')) return
  e.preventDefault()
  const lines = (draft.value + text).replace(/\r/g, '').split('\n')
  if (lines[lines.length - 1] === '') lines.pop()
  draft.value = ''
  props.run.submit(lines)
}

function focusInput() {
  // Don't steal a text selection the teacher is making in the output.
  if (window.getSelection()?.toString()) return
  inputEl.value?.focus()
}

watch(
  () => [state.value.segments.length, state.value.segments.at(-1)?.text, state.value.status],
  async () => {
    await nextTick()
    if (screen.value) screen.value.scrollTop = screen.value.scrollHeight
    if (state.value.status === 'waiting') inputEl.value?.focus({ preventScroll: true })
  },
)
</script>

<template>
  <section class="console" :class="variant">
    <header>
      <span class="dot" />
      <span class="title">{{ title }}</span>
      <span v-if="statusLabel" class="status" :class="state.status">
        <span v-if="busy" class="spin" />{{ statusLabel }}
      </span>
      <span class="grow" />
      <slot name="actions" />
      <button v-if="busy || state.status === 'waiting'" class="btn btn-small" @click="run.stop()">Stop</button>
    </header>

    <div ref="screen" class="screen" :class="{ busy }" @click="focusInput">
      <p v-if="state.status === 'idle'" class="placeholder">
        Press <strong>Run</strong>. When the program calls <code>input()</code>, type the answer here and press Enter.
      </p>
      <template v-else>
        <span v-for="(s, i) in state.segments" :key="i" class="seg" :class="s.kind">{{ s.text }}</span><input
          v-if="state.status === 'waiting'"
          ref="inputEl"
          v-model="draft"
          class="stdin"
          spellcheck="false"
          autocomplete="off"
          aria-label="Input for the program"
          @keydown.enter.prevent="submit"
          @paste="onPaste"
        />
        <div v-if="footer" class="footer" :class="state.status">{{ footer }}</div>
      </template>
    </div>

    <footer v-if="state.inputs.length" class="inputs">
      <span class="lbl">Inputs</span>
      <code v-for="(v, i) in state.inputs" :key="i">{{ v === '' ? '⏎' : v }}</code>
      <span class="grow" />
      <slot name="inputs-actions" />
    </footer>
  </section>
</template>

<style scoped>
.console {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-card);
}
header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.82rem;
}
.student header { background: var(--student-bg); color: var(--student-tx); }
.solution header { background: var(--solution-bg); color: var(--solution-tx); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; opacity: 0.7; }
.title { font-weight: 600; }
.status { font-size: 0.75rem; color: var(--text-muted); display: inline-flex; align-items: center; }
.status.waiting { color: var(--accent); font-weight: 600; }
.status.done { color: var(--success); }
.status.error, .status.timeout { color: var(--danger); }
.grow { flex: 1; }

.screen {
  height: 260px;
  overflow: auto;
  padding: 0.55rem 0.75rem;
  background: var(--code-bg);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  cursor: text;
  resize: vertical;
}
.screen.busy { opacity: 0.75; }
.placeholder { margin: 0; color: var(--text-muted); white-space: normal; font-family: system-ui, sans-serif; }
.seg.out { color: var(--text); }
.seg.prompt { color: var(--text-strong); }
.seg.in { color: var(--accent); font-weight: 600; }
.seg.err { color: var(--danger); }
.stdin {
  display: inline-block;
  width: 22ch;
  max-width: 100%;
  padding: 0 0.15rem;
  border: none;
  border-bottom: 1.5px solid var(--accent);
  border-radius: 0;
  background: transparent;
  color: var(--accent);
  font: inherit;
  font-weight: 600;
  vertical-align: baseline;
}
.stdin:focus { outline: none; box-shadow: none; border-bottom-width: 2px; }
.footer { margin-top: 0.35rem; font-size: 0.78rem; color: var(--text-muted); white-space: normal; font-family: system-ui, sans-serif; }
.footer.timeout { color: var(--danger); }

.inputs {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-wrap: wrap;
  padding: 0.35rem 0.6rem;
  border-top: 1px solid var(--border);
  background: var(--bg-soft);
  font-size: 0.75rem;
}
.inputs .lbl { color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; font-size: 0.68rem; }
.inputs code {
  padding: 0 0.35rem;
  border-radius: 4px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  font-size: 0.75rem;
}
.btn-small { padding: 0.18rem 0.55rem; font-size: 0.76rem; }
.spin {
  display: inline-block;
  width: 10px; height: 10px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  margin-right: 0.35rem;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
