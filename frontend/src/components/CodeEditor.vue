<script setup lang="ts">
/**
 * Lightweight syntax-highlighted code editor.
 *
 * Implementation: a transparent <textarea> overlays a <pre><code> rendered
 * with highlight.js. Both share the same font/line-height so the caret in
 * the textarea lines up with tokens in the highlight underneath. The
 * textarea's scroll position is mirrored into the <pre> so long files stay
 * in sync.
 *
 * This avoids the ~150KB+ cost of CodeMirror/Monaco for what's essentially
 * a "show what the student wrote and let me edit before running" textbox.
 */
import { computed, nextTick, ref, watch } from 'vue'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/github.css'

hljs.registerLanguage('python', python)

const props = defineProps<{
  modelValue: string
  rows?: number
  placeholder?: string
  language?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const textareaEl = ref<HTMLTextAreaElement | null>(null)
const preEl = ref<HTMLPreElement | null>(null)

const language = computed(() => props.language ?? 'python')

// Trailing newline keeps the highlighted block the same height as the
// textarea content (textareas always render an extra empty trailing line).
const highlighted = computed(() => {
  const code = props.modelValue ?? ''
  if (!code) return ''
  try {
    return hljs.highlight(code, { language: language.value, ignoreIllegals: true }).value + '\n'
  } catch {
    return escapeHtml(code) + '\n'
  }
})

function escapeHtml(s: string): string {
  return s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]!))
}

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
}

function onScroll() {
  if (!textareaEl.value || !preEl.value) return
  preEl.value.scrollTop = textareaEl.value.scrollTop
  preEl.value.scrollLeft = textareaEl.value.scrollLeft
}

// Tab inserts spaces instead of moving focus.
function onKeyDown(e: KeyboardEvent) {
  if (e.key !== 'Tab') return
  e.preventDefault()
  const t = e.target as HTMLTextAreaElement
  const start = t.selectionStart
  const end = t.selectionEnd
  const value = t.value
  const next = value.slice(0, start) + '    ' + value.slice(end)
  emit('update:modelValue', next)
  void nextTick(() => {
    t.selectionStart = t.selectionEnd = start + 4
  })
}

// Re-sync scroll after content changes (e.g. external programmatic edits).
watch(() => props.modelValue, () => {
  void nextTick(onScroll)
})
</script>

<template>
  <div class="code-editor" :style="{ '--rows': rows ?? 12 }">
    <pre ref="preEl" class="hl" aria-hidden="true"><code :class="`hljs language-${language}`" v-html="highlighted" /></pre>
    <textarea
      ref="textareaEl"
      class="input"
      :value="modelValue"
      :placeholder="placeholder"
      spellcheck="false"
      autocomplete="off"
      autocorrect="off"
      autocapitalize="off"
      @input="onInput"
      @scroll="onScroll"
      @keydown="onKeyDown"
    />
  </div>
</template>

<style scoped>
.code-editor {
  position: relative;
  background: var(--code-bg);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  overflow: hidden;
  /* The container's height drives both the <pre> and <textarea>. */
  height: calc(var(--rows, 12) * 1.5em + 1.1rem);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  line-height: 1.5;
}

/* Both layers share identical box metrics so columns line up. */
.code-editor .hl,
.code-editor .input {
  position: absolute;
  inset: 0;
  margin: 0;
  padding: 0.55rem 0.75rem;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  white-space: pre;
  word-spacing: normal;
  overflow: auto;
  border: 0;
  background: transparent;
  tab-size: 4;
}

.code-editor .hl {
  pointer-events: none;
  color: var(--text);
}
.code-editor .hl :deep(code.hljs) {
  background: transparent;
  padding: 0;
}

.code-editor .input {
  resize: none;
  color: transparent;
  /* Caret stays visible even when text is invisible. */
  caret-color: var(--text-strong);
  /* On Safari "color: transparent" hides the selection too — give it a
     visible highlight that doesn't fight with the underlying tokens. */
  -webkit-text-fill-color: transparent;
}
.code-editor .input::selection {
  background: rgba(37, 99, 235, 0.25);
  -webkit-text-fill-color: transparent;
}
.code-editor .input::placeholder {
  color: var(--text-muted);
  -webkit-text-fill-color: var(--text-muted);
}
.code-editor .input:focus {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
</style>
