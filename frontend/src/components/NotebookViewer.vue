<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/github.css'
import type { CellOut } from '../api/client'

hljs.registerLanguage('python', python)

const props = defineProps<{ cells: CellOut[] }>()

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
    <article
      v-for="(cell, i) in renderedCells"
      :key="cell.cell_id || i"
      class="cell"
      :class="cell.cell_type"
    >
      <div v-if="cell.cell_type === 'markdown'" class="md" v-html="cell.html" />
      <template v-else>
        <pre class="code"><code class="hljs language-python" v-html="cell.highlighted" /></pre>
        <pre v-if="cell.output" class="output">{{ cell.output }}</pre>
      </template>
    </article>
  </div>
</template>

<style scoped>
.notebook { display: flex; flex-direction: column; gap: 1rem; }

.cell {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.5rem 0.85rem;
  background: white;
}

.cell.markdown {
  background: #fafbfc;
}

.md :deep(p) { margin: 0.4rem 0; }
.md :deep(h1), .md :deep(h2), .md :deep(h3) { margin: 0.6rem 0 0.3rem; }
.md :deep(code) { background: #f1f3f5; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }

pre.code {
  margin: 0.25rem 0;
  padding: 0.6rem 0.85rem;
  background: #f6f8fa;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.88rem;
  line-height: 1.45;
}

pre.output {
  margin: 0.4rem 0 0;
  padding: 0.5rem 0.75rem;
  background: #fffaf0;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-word;
}

code.hljs { background: transparent; padding: 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
</style>
