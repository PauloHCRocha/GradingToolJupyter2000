<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/atom-one-dark.css'
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
      <header class="cell-head">{{ cell.cell_type }}</header>
      <div v-if="cell.cell_type === 'markdown'" class="md" v-html="cell.html" />
      <template v-else>
        <pre class="code"><code class="hljs language-python" v-html="cell.highlighted" /></pre>
        <pre v-if="cell.output" class="output">{{ cell.output }}</pre>
      </template>
    </article>
  </div>
</template>

<style scoped>
.notebook {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.placeholder {
  color: var(--text-muted);
  font-style: italic;
  padding: 1rem;
  text-align: center;
}

.cell {
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-panel);
}
.cell.markdown { border-left: 3px solid #9b59b6; }
.cell.code { border-left: 3px solid var(--success); }

.cell-head {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  padding: 0.3rem 0.6rem;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.md {
  padding: 0.7rem 0.9rem;
  color: var(--text);
}
.md :deep(p) { margin: 0.4rem 0; }
.md :deep(h1), .md :deep(h2), .md :deep(h3) { color: var(--text-strong); margin: 0.6rem 0 0.3rem; }
.md :deep(code) {
  background: var(--code-bg);
  color: #f8f8f2;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

pre.code {
  margin: 0;
  padding: 0.6rem 0.85rem;
  background: var(--code-bg);
  font-size: 0.85rem;
  line-height: 1.45;
  overflow-x: auto;
}

pre.output {
  margin: 0;
  padding: 0.5rem 0.85rem;
  background: #1f1f1f;
  border-top: 1px solid var(--border);
  border-left: 3px solid var(--warning);
  color: #ddd;
  font-size: 0.82rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

code.hljs {
  background: transparent;
  padding: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
</style>
