<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/github.css'
import type { MatchingBlock, PlagiarismCompareResponse, QuestionComparison } from '../../api/client'
import { severityClass } from './colors'

hljs.registerLanguage('python', python)

const props = defineProps<{
  result: PlagiarismCompareResponse | null
  loading: boolean
}>()
const emit = defineEmits<{
  close: []
  exportPdf: []
}>()

// Lock body scroll while modal is open. Restore on unmount as a safety net
// in case the parent gets torn down (e.g. route change) with the modal up.
watch(
  () => props.result || props.loading,
  (open) => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = open ? 'hidden' : ''
    }
  },
)
onBeforeUnmount(() => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})

function highlightLine(line: string): string {
  if (!line) return '&nbsp;'
  return hljs.highlight(line, { language: 'python', ignoreIllegals: true }).value
}

interface Group {
  block: MatchingBlock | null
  lines: { text: string; html: string }[]
}

function groupLines(code: string, blocks: MatchingBlock[], side: 'left' | 'right'): Group[] {
  const lines = code.split('\n')
  const lineToBlock = new Map<number, MatchingBlock>()
  for (const b of blocks) {
    const start = side === 'left' ? b.start1 : b.start2
    const end = side === 'left' ? b.end1 : b.end2
    if (start < 0) continue
    for (let i = start; i < end; i++) lineToBlock.set(i, b)
  }
  const groups: Group[] = []
  let cur: Group | null = null
  for (let i = 0; i < lines.length; i++) {
    const block = lineToBlock.get(i) ?? null
    if (!cur || cur.block !== block) {
      cur = { block, lines: [] }
      groups.push(cur)
    }
    cur.lines.push({ text: lines[i], html: highlightLine(lines[i]) })
  }
  return groups
}

function blockLabel(type: 'exact' | 'similar' | 'invisible'): string {
  if (type === 'exact') return '⚠️ Identical'
  if (type === 'similar') return '⚡ Similar'
  return '👻 Hidden chars'
}

function blockBg(color: string): string {
  return color + '14' // 8% opacity
}

function questionGroups(q: QuestionComparison) {
  return {
    left: groupLines(q.code1, q.matching_blocks, 'left'),
    right: groupLines(q.code2, q.matching_blocks, 'right'),
  }
}

const orderedQuestions = computed(() => {
  if (!props.result) return []
  return [...props.result.questions].sort((a, b) => b.similarity - a.similarity)
})

function onBgClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('modal-bg')) {
    emit('close')
  }
}
</script>

<template>
  <Transition name="modal">
    <div v-if="result || loading" class="modal-bg" @click="onBgClick">
      <div class="modal" role="dialog" aria-modal="true">
        <header>
          <div class="title">
            <h3 v-if="result">
              {{ result.student1_name }} ↔ {{ result.student2_name }}
            </h3>
            <h3 v-else>Comparing…</h3>
            <div v-if="result" class="overall">
              Overall similarity:
              <strong :class="severityClass(result.overall_similarity)">
                {{ Math.round(result.overall_similarity * 100) }}%
              </strong>
            </div>
          </div>
          <div class="actions">
            <button v-if="result" class="btn btn-pdf" @click="emit('exportPdf')">
              Export PDF
            </button>
            <button class="btn ghost" @click="emit('close')">✕</button>
          </div>
        </header>

        <div v-if="loading" class="modal-body loading">
          <div class="spin big" />
          <p>Computing similarity & matching blocks…</p>
        </div>

        <div v-else-if="result" class="modal-body">
          <section class="legend">
            <span class="lg-item exact">⚠️ Identical block</span>
            <span class="lg-item similar">⚡ Similar (variable rename)</span>
            <span class="lg-item invisible">👻 Hidden unicode chars</span>
          </section>

          <article v-for="q in orderedQuestions" :key="q.question_id" class="qsection">
            <header class="qhead" :class="severityClass(q.similarity)">
              <h4>
                {{ q.question_id }}
                <span class="qsim">{{ Math.round(q.similarity * 100) }}%</span>
              </h4>
              <span class="qsub">
                hybrid {{ Math.round(q.similarity * 100) }}% ·
                tf-idf {{ Math.round(q.tfidf * 100) }}% ·
                ast {{ Math.round(q.ast * 100) }}%
              </span>
            </header>
            <div class="codes">
              <div class="code-pane">
                <header>{{ result.student1_name }}</header>
                <div class="code-body">
                  <template v-for="(g, gi) in questionGroups(q).left" :key="`l${gi}`">
                    <div
                      v-if="g.block"
                      class="bubble"
                      :style="{ borderColor: g.block.color, background: blockBg(g.block.color) }"
                    >
                      <span class="bubble-tag" :style="{ color: g.block.color }">
                        {{ blockLabel(g.block.type) }}
                      </span>
                      <pre><code class="hljs"><template v-for="(l, li) in g.lines" :key="li"><span v-html="l.html" />{{ '\n' }}</template></code></pre>
                    </div>
                    <pre v-else class="loose"><code class="hljs"><template v-for="(l, li) in g.lines" :key="li"><span v-html="l.html" />{{ '\n' }}</template></code></pre>
                  </template>
                  <p v-if="!q.code1.trim()" class="empty">(no code for this question)</p>
                </div>
              </div>
              <div class="code-pane">
                <header>{{ result.student2_name }}</header>
                <div class="code-body">
                  <template v-for="(g, gi) in questionGroups(q).right" :key="`r${gi}`">
                    <div
                      v-if="g.block"
                      class="bubble"
                      :style="{ borderColor: g.block.color, background: blockBg(g.block.color) }"
                    >
                      <span class="bubble-tag" :style="{ color: g.block.color }">
                        {{ blockLabel(g.block.type) }}
                      </span>
                      <pre><code class="hljs"><template v-for="(l, li) in g.lines" :key="li"><span v-html="l.html" />{{ '\n' }}</template></code></pre>
                    </div>
                    <pre v-else class="loose"><code class="hljs"><template v-for="(l, li) in g.lines" :key="li"><span v-html="l.html" />{{ '\n' }}</template></code></pre>
                  </template>
                  <p v-if="!q.code2.trim()" class="empty">(no code for this question)</p>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-bg {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex; align-items: center; justify-content: center;
  z-index: 50;
  padding: 1rem;
}
.modal {
  background: var(--bg-card);
  width: min(1300px, 96vw);
  max-height: 92vh;
  border-radius: 10px;
  border: 1px solid var(--border-strong);
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0,0,0,0.2);
}
.modal > header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.7rem 1rem;
  background: var(--header-bg);
  color: white;
  border-bottom: 1px solid var(--border);
  gap: 0.6rem;
}
.modal h3 { margin: 0; font-size: 0.95rem; }
.title { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
.overall { font-size: 0.82rem; color: rgba(255,255,255,0.85); }
.overall strong { color: white; }
.overall strong.high { color: #fca5a5; }
.overall strong.med { color: #fcd34d; }
.overall strong.low { color: #86efac; }
/* (header sits on a navy bg in both themes — fixed colours are fine here) */
.actions { display: flex; gap: 0.4rem; }
.btn-pdf { background: var(--danger); border: none; color: white; padding: 0.35rem 0.7rem; border-radius: 6px; font-size: 0.82rem; }
.btn-pdf:hover { background: #b91c1c; }
.btn.ghost { background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.25); padding: 0.3rem 0.6rem; border-radius: 6px; font-size: 0.82rem; }
.btn.ghost:hover { background: rgba(255,255,255,0.18); }

.modal-body {
  padding: 1rem 1.25rem;
  overflow-y: auto;
  background: var(--bg-page);
}
.modal-body.loading { padding: 4rem 1rem; text-align: center; color: var(--text-muted); }
.modal-body.loading .spin {
  display: inline-block;
  width: 40px; height: 40px;
  border: 4px solid var(--accent);
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.legend {
  display: flex; gap: 0.6rem; flex-wrap: wrap;
  padding: 0.55rem 0.85rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 0.85rem;
  font-size: 0.78rem;
  color: var(--text-muted);
}
.lg-item.exact { color: #ef4444; }
.lg-item.similar { color: #f59e0b; }
.lg-item.invisible { color: #3b82f6; }

.qsection {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 0.85rem;
  overflow: hidden;
}
.qhead {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.55rem 0.85rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
}
.qhead.high { background: var(--danger-soft); }
.qhead.med { background: var(--warning-soft); }
.qhead.low { background: var(--success-soft); }
.qhead h4 { margin: 0; font-size: 0.92rem; color: var(--text-strong); display: flex; align-items: center; gap: 0.5rem; }
.qhead .qsim { font-weight: 700; }
.qhead.high .qsim { color: var(--danger); }
.qhead.med .qsim { color: var(--warning); }
.qhead.low .qsim { color: var(--success); }
.qhead .qsub { color: var(--text-muted); font-size: 0.78rem; font-family: ui-monospace, monospace; }

.codes { display: grid; grid-template-columns: 1fr 1fr; gap: 0.55rem; padding: 0.55rem; }
.code-pane {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.code-pane > header {
  padding: 0.35rem 0.6rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
  font-size: 0.78rem;
  color: var(--text-muted);
  font-weight: 600;
}
.code-body {
  padding: 0.4rem;
  overflow: auto;
  max-height: 460px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
  background: var(--code-bg);
}
.bubble {
  position: relative;
  border: 2px solid;
  border-radius: 8px;
  padding: 0.5rem 0.6rem 0.4rem;
  margin: 0.45rem 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.bubble-tag {
  position: absolute;
  top: 4px;
  right: 8px;
  font-size: 0.68rem;
  font-weight: 700;
  background: rgba(255,255,255,0.85);
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.3px;
}
.bubble pre, pre.loose {
  margin: 0;
  background: transparent;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}
pre.loose { padding: 0 0.2rem; }
code.hljs { background: transparent; padding: 0; }

.empty { color: var(--text-muted); font-style: italic; padding: 0.5rem; margin: 0; }

.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.15s; }

@media (max-width: 900px) {
  .codes { grid-template-columns: 1fr; }
}
</style>
