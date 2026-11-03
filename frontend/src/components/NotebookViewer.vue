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
    <template v-for="(cell, i) in renderedCells" :key="cell.cell_id || i">
      <!-- Cell #1: the code (or markdown) itself. -->
      <article class="cell" :class="cell.cell_type">
        <!-- Code needs no label; markdown and output do, to tell them apart. -->
        <header v-if="cell.cell_type !== 'code'" class="cell-head">{{ cell.cell_type }}</header>
        <div v-if="cell.cell_type === 'markdown'" class="md" v-html="cell.html" />
        <pre v-else class="code"><code class="hljs language-python" v-html="cell.highlighted"></code></pre>
      </article>

      <!-- Cell #2: the output, only when present. Sibling card so it's
           visually distinct from the code, like real notebook UIs do. -->
      <article v-if="cell.cell_type === 'code' && cell.output" class="cell output">
        <header class="cell-head">Output</header>
        <pre class="output-body">{{ cell.output }}</pre>
      </article>
    </template>
  </div>
</template>

<style scoped>
.notebook { display: flex; flex-direction: column; gap: 0.5rem; }
.placeholder { color: var(--text-muted); font-style: italic; padding: 1rem; text-align: center; }

.cell {
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
}
.cell.markdown { border-left: 3px solid #8b5cf6; }
.cell.code { border-left: 3px solid var(--success); }
.cell.output {
  border-left: 3px solid var(--warning);
  background: var(--output-bg);
  /* Tighter coupling to the code card above it. */
  margin-top: -0.35rem;
}

.cell-head {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  padding: 0.28rem 0.6rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
}
.cell.output .cell-head {
  color: var(--output-label);
  background: rgba(245, 158, 11, 0.08);
  border-bottom-color: rgba(245, 158, 11, 0.25);
  font-weight: 600;
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

pre.code {
  display: block;
  margin: 0;
  padding: 0.55rem 0.85rem;
  background: var(--code-bg);
  font-size: 0.85rem;
  line-height: 1.5;
  overflow-x: auto;
  vertical-align: top;
  white-space: pre;
}
pre.code :deep(code.hljs) {
  display: block;
  background: transparent;
  padding: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  vertical-align: top;
}

pre.output-body {
  margin: 0;
  padding: 0.55rem 0.85rem;
  background: transparent;
  color: var(--output-text);
  font-size: 0.82rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
</style>
