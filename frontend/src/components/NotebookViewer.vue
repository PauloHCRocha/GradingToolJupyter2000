<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/github.css'
import type { CellOut } from '../api/client'

hljs.registerLanguage('python', python)

const props = defineProps<{ cells: CellOut[]; placeholder?: string }>()

const renderedCells = computed(() =>
  props.cells.map((cell) => {
    if (cell.cell_type === 'markdown') {
      return { ...cell, html: marked.parse(cell.source) as string, highlighted: '' }
    }
    const highlighted = cell.source
      ? hljs.highlight(cell.source, { language: 'python', ignoreIllegals: true }).value
      : ''
    return { ...cell, html: '', highlighted }
  }),
)
</script>

<template>
  <div class="notebook">
    <p v-if="!cells.length" class="placeholder">
      {{ placeholder ?? 'No cells to display.' }}
    </p>
    <article
      v-for="(cell, i) in renderedCells"
      :key="cell.cell_id || i"
      class="cell"
      :class="cell.cell_type"
    >
      <header class="cell-head">
        <span>{{ cell.cell_type }}</span>
        <span v-if="cell.output" class="has-output">has output</span>
      </header>
      <div v-if="cell.cell_type === 'markdown'" class="md" v-html="cell.html" />
      <template v-else>
        <!-- Explicit closing tags so the browser never gets confused by a
             self-closing <code/> inside <pre>. v-html safely escapes/wraps. -->
        <pre class="code"><code class="hljs language-python" v-html="cell.highlighted"></code></pre>
        <div v-if="cell.output" class="output-wrap">
          <span class="output-label">Output</span>
          <pre class="output">{{ cell.output }}</pre>
        </div>
      </template>
    </article>
  </div>
</template>

<style scoped>
.notebook { display: flex; flex-direction: column; gap: 0.55rem; }
.placeholder { color: var(--text-muted); font-style: italic; padding: 1rem; text-align: center; }

.cell {
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-card);
  /* Stack the children explicitly so nothing overlaps. */
  display: flex;
  flex-direction: column;
}
.cell.markdown { border-left: 3px solid #8b5cf6; }
.cell.code { border-left: 3px solid var(--success); }

.cell-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  padding: 0.28rem 0.6rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
}
.cell-head .has-output {
  font-size: 0.65rem;
  letter-spacing: 0.4px;
  color: var(--warning);
  padding: 1px 6px;
  background: var(--warning-soft);
  border-radius: 999px;
  text-transform: none;
}

.md { padding: 0.7rem 0.9rem; }
.md :deep(p) { margin: 0.4rem 0; }
.md :deep(h1), .md :deep(h2), .md :deep(h3) {
  color: var(--text-strong);
  margin: 0.6rem 0 0.3rem;
}
.md :deep(code) {
  background: var(--code-bg);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.9em;
  border: 1px solid var(--code-border);
}

/* Code panel — own background, owns its own scroll context, never bleeds. */
pre.code {
  display: block;
  margin: 0;
  padding: 0.55rem 0.85rem;
  background: var(--code-bg);
  font-size: 0.85rem;
  line-height: 1.5;
  overflow-x: auto;
  /* Prevent the implicit baseline gap that <code> can leave at the bottom
     of <pre> and which would show through as a strip of code-bg below the
     last line, "passing below" the output panel that follows. */
  vertical-align: top;
  white-space: pre;
}
pre.code :deep(code.hljs) {
  display: block;
  background: transparent;
  padding: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  /* Same vertical-align rule on the inline child. */
  vertical-align: top;
}

/* Output sits on its own card-like row, clearly separated from the code
   above. No competing border-left here — the parent .cell already shows
   its colour stripe; another stripe on the output created the visual
   "code region extending under the output" effect. */
.output-wrap {
  border-top: 1px solid var(--border);
  background: #fffaf0;
}
.output-label {
  display: block;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #b45309;
  padding: 0.3rem 0.85rem 0.1rem;
  font-weight: 600;
}
pre.output {
  margin: 0;
  padding: 0 0.85rem 0.5rem;
  background: transparent;
  color: #6b4519;
  font-size: 0.82rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
</style>
