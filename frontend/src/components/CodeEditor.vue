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

const INDENT = 4

/** Replace [start, end) with `text`, then optionally select [selStart, selEnd).
 *  Goes through execCommand so the browser's undo history (Cmd/Ctrl+Z)
 *  survives — assigning `.value` would wipe it. */
function edit(t: HTMLTextAreaElement, start: number, end: number, text: string, selStart?: number, selEnd?: number) {
  t.setSelectionRange(start, end)
  const ok = text === '' ? document.execCommand('delete') : document.execCommand('insertText', false, text)
  if (!ok) {
    t.setRangeText(text, start, end, 'end')
    emit('update:modelValue', t.value)
  }
  if (selStart !== undefined) t.setSelectionRange(selStart, selEnd ?? selStart)
}

const lineStartOf = (v: string, pos: number) => v.lastIndexOf('\n', pos - 1) + 1

/** Indent (or with `out`, dedent) every line the selection touches. */
function shiftLines(t: HTMLTextAreaElement, out: boolean) {
  const { selectionStart: s, selectionEnd: e, value: v } = t
  const from = lineStartOf(v, s)
  // A selection ending at the very start of a line doesn't include that line.
  const last = e > s && v[e - 1] === '\n' ? e - 1 : e
  const to = v.indexOf('\n', last) === -1 ? v.length : v.indexOf('\n', last)
  const block = v.slice(from, to)
  const lines = block.split('\n')
  const changed = lines
    .map((l) => (out ? l.replace(new RegExp(`^ {1,${INDENT}}|^\\t`), '') : ' '.repeat(INDENT) + l))
    .join('\n')
  if (changed === block) return
  if (s === e) {
    // Caret only: keep it where it was relative to the text.
    const caret = Math.max(from, s + (changed.length - block.length))
    edit(t, from, to, changed, caret)
  } else {
    edit(t, from, to, changed, from, from + changed.length)
  }
}

// After Escape, the next Tab leaves the editor instead of indenting —
// otherwise keyboard users would be trapped inside it.
let tabLeaves = false

function onKeyDown(e: KeyboardEvent) {
  if (e.isComposing) return
  const t = e.target as HTMLTextAreaElement
  const { selectionStart: s, selectionEnd: end, value: v } = t

  if (e.key === 'Escape') {
    tabLeaves = true
    return
  }
  if (e.key === 'Tab') {
    if (tabLeaves) {
      tabLeaves = false
      return
    }
    e.preventDefault()
    if (e.shiftKey || s !== end) shiftLines(t, e.shiftKey)
    else edit(t, s, end, ' '.repeat(INDENT - ((s - lineStartOf(v, s)) % INDENT)))
    return
  }
  tabLeaves = false

  // Enter keeps the line's indentation, one level deeper after a ":".
  if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) {
    e.preventDefault()
    const before = v.slice(lineStartOf(v, s), s)
    let indent = before.match(/^[ \t]*/)![0]
    if (/:\s*(#.*)?$/.test(before) && !before.trimStart().startsWith('#')) indent += ' '.repeat(INDENT)
    edit(t, s, end, '\n' + indent)
    return
  }

  // Backspace inside leading spaces removes one indentation level.
  if (e.key === 'Backspace' && s === end && !e.metaKey && !e.altKey && !e.ctrlKey) {
    const before = v.slice(lineStartOf(v, s), s)
    if (before.length && /^ +$/.test(before)) {
      e.preventDefault()
      edit(t, s - (((before.length - 1) % INDENT) + 1), s, '')
    }
  }
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
  /* The container's height drives both the <pre> and <textarea>; drag the
     bottom-right corner to make it taller. */
  height: calc(var(--rows, 12) * 1.5em + 1.1rem);
  min-height: calc(4 * 1.5em + 1.1rem);
  resize: vertical;
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
  font-variant-ligatures: none;
}

.code-editor .hl {
  pointer-events: none;
  color: var(--text);
}
.code-editor .hl :deep(code.hljs) {
  background: transparent;
  padding: 0;
  /* Browsers give <code> `font-family: monospace` — a different font from
     the textarea's, which put the caret off the visible text. */
  font: inherit;
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
