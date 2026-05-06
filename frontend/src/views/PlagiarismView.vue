<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { plagiarismAnalyze, plagiarismCompare } from '../api/client'
import type { PlagiarismAnalyzeResponse, PlagiarismCompareResponse } from '../api/client'

const session = useSessionStore()
const router = useRouter()

const threshold = ref(0.85)
const loading = ref(false)
const startedAt = ref<number | null>(null)
const elapsed = ref(0)
const error = ref<string | null>(null)
const result = ref<PlagiarismAnalyzeResponse | null>(null)

const compareLoading = ref(false)
const compareResult = ref<PlagiarismCompareResponse | null>(null)

let elapsedTimer: number | null = null

const studentCount = computed(() => session.students.length)
const estComparisons = computed(() => {
  const n = studentCount.value
  return n < 2 ? 0 : (n * (n - 1)) / 2
})
const filteredPairs = computed(() => result.value?.suspicious_pairs ?? [])

onMounted(async () => {
  if (!session.students.length) {
    try {
      await session.refreshStudents()
    } catch {
      /* ignore */
    }
  }
})

async function analyze() {
  if (loading.value) return
  loading.value = true
  error.value = null
  result.value = null
  startedAt.value = Date.now()
  elapsed.value = 0
  elapsedTimer = window.setInterval(() => {
    if (startedAt.value) elapsed.value = (Date.now() - startedAt.value) / 1000
  }, 100)
  try {
    result.value = await plagiarismAnalyze(threshold.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
    if (elapsedTimer) {
      clearInterval(elapsedTimer)
      elapsedTimer = null
    }
  }
}

async function openCompare(s1: string, s2: string) {
  compareLoading.value = true
  compareResult.value = null
  try {
    compareResult.value = await plagiarismCompare(s1, s2)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    compareLoading.value = false
  }
}

function severity(sim: number): 'low' | 'med' | 'high' {
  if (sim >= 0.95) return 'high'
  if (sim >= 0.85) return 'med'
  return 'low'
}

function cellColor(v: number, isDiagonal: boolean): string {
  if (isDiagonal) return '#f3f4f6'
  if (v < 0.3) return `hsl(140, 60%, ${88 - v * 35}%)`
  if (v < 0.7) return `hsl(${140 - (v - 0.3) * 80}, 70%, ${75 - v * 15}%)`
  return `hsl(${30 - (v - 0.7) * 100}, 78%, ${68 - v * 18}%)`
}
</script>

<template>
  <div class="page">
    <header class="appbar">
      <div class="title">
        <h1>⚠ Plagiarism detection</h1>
        <span class="meta">{{ studentCount }} students loaded</span>
      </div>
      <div class="actions">
        <button class="btn" @click="router.push('/grading')">← Back to grading</button>
        <button class="btn" @click="router.push('/setup')">Setup</button>
      </div>
    </header>

    <main class="body">
      <section v-if="studentCount < 2" class="empty">
        <p>You need at least 2 student submissions to detect plagiarism.</p>
        <button class="btn btn-primary" @click="router.push('/setup')">Go to setup</button>
      </section>

      <template v-else>
        <section class="card controls">
          <header class="card-head">
            <h3>Analysis settings</h3>
            <span class="card-meta">
              {{ studentCount }} students · ~<strong>{{ estComparisons }}</strong> comparisons
            </span>
          </header>
          <div class="control-row">
            <label class="threshold">
              <span class="lbl">Threshold</span>
              <input type="range" min="0.5" max="1" step="0.01" v-model.number="threshold" :disabled="loading" />
              <strong>{{ threshold.toFixed(2) }}</strong>
            </label>
            <button class="btn btn-primary big" :disabled="loading" @click="analyze">
              <span v-if="loading" class="spin" />
              {{ loading ? 'Analyzing…' : '▶ Run plagiarism detection' }}
            </button>
          </div>
          <p class="hint">
            Hybrid similarity: 40% TF-IDF text · 30% AST structure · 30% token Jaccard.
            Pairs above the threshold are flagged.
          </p>
        </section>

        <p v-if="error" class="error">{{ error }}</p>

        <!-- Inline progress -->
        <section v-if="loading" class="card progress">
          <div class="progress-row">
            <span class="big-spin" />
            <div>
              <strong>Computing similarity matrix…</strong>
              <p>
                Comparing {{ estComparisons }} pairs across {{ studentCount }} students.
                Elapsed {{ elapsed.toFixed(1) }}s. This can take 10-30s for ~80 students.
              </p>
            </div>
          </div>
        </section>

        <section v-if="result" class="stats">
          <div class="stat">
            <span class="lbl">Total comparisons</span>
            <strong>{{ result.stats.total_comparisons }}</strong>
          </div>
          <div class="stat warn">
            <span class="lbl">Suspicious pairs</span>
            <strong>{{ result.stats.suspicious_count }}</strong>
          </div>
          <div class="stat danger">
            <span class="lbl">High similarity (≥95%)</span>
            <strong>{{ result.stats.high_similarity_count }}</strong>
          </div>
          <div class="stat">
            <span class="lbl">Average similarity</span>
            <strong>{{ Math.round(result.stats.avg_similarity * 100) }}%</strong>
          </div>
        </section>

        <section v-if="result" class="card pairs">
          <header class="card-head">
            <h3>Suspicious pairs</h3>
            <span class="card-meta">{{ filteredPairs.length }} above {{ threshold.toFixed(2) }}</span>
          </header>
          <p v-if="!filteredPairs.length" class="placeholder">
            No pairs above threshold. Lower the threshold to see less-suspicious pairs.
          </p>
          <ul v-else>
            <li
              v-for="p in filteredPairs"
              :key="p.student1_id + '-' + p.student2_id"
              :class="severity(p.similarity)"
              @click="openCompare(p.student1_id, p.student2_id)"
            >
              <div class="pair-names">
                <strong>{{ p.student1_name }}</strong>
                <span class="sep">↔</span>
                <strong>{{ p.student2_name }}</strong>
              </div>
              <div class="pair-meta">
                <code>#{{ p.student1_id }}</code> · <code>#{{ p.student2_id }}</code>
              </div>
              <div class="pair-score" :class="severity(p.similarity)">
                {{ Math.round(p.similarity * 100) }}%
              </div>
            </li>
          </ul>
        </section>

        <section v-if="result" class="card matrix">
          <header class="card-head">
            <h3>Similarity matrix</h3>
            <span class="card-meta">click any cell to compare</span>
          </header>
          <div class="matrix-scroll">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th
                    v-for="(name, j) in result.student_names" :key="j"
                    :title="name"
                  >{{ result.student_ids[j] }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in result.matrix" :key="i">
                  <th :title="result.student_names[i]">{{ result.student_ids[i] }}</th>
                  <td
                    v-for="(v, j) in row" :key="j"
                    :style="{ background: cellColor(v, i === j) }"
                    :title="`${result.student_names[i]} vs ${result.student_names[j]}: ${(v*100).toFixed(1)}%`"
                    @click="i !== j && openCompare(result.student_ids[i], result.student_ids[j])"
                  />
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </main>

    <Transition name="modal">
      <div v-if="compareResult || compareLoading" class="modal-bg" @click.self="compareResult = null; compareLoading = false">
        <div class="modal">
          <header>
            <h3 v-if="compareResult">
              {{ compareResult.student1_name }} ↔ {{ compareResult.student2_name }}
              <span class="overall">
                · overall {{ Math.round(compareResult.overall_similarity * 100) }}%
              </span>
            </h3>
            <h3 v-else>Loading comparison…</h3>
            <button class="btn ghost" @click="compareResult = null">✕</button>
          </header>
          <div v-if="compareLoading" class="modal-body">
            <div class="progress-row">
              <span class="big-spin" />
              <strong>Comparing submissions…</strong>
            </div>
          </div>
          <div v-if="compareResult" class="modal-body">
            <h4>Per-question similarity</h4>
            <table class="qsim">
              <thead>
                <tr><th>Question</th><th>Hybrid</th><th>TF-IDF</th><th>AST</th></tr>
              </thead>
              <tbody>
                <tr v-for="q in compareResult.questions" :key="q.question_id">
                  <td><code>{{ q.question_id }}</code></td>
                  <td :class="severity(q.similarity)">{{ Math.round(q.similarity * 100) }}%</td>
                  <td>{{ Math.round(q.tfidf * 100) }}%</td>
                  <td>{{ Math.round(q.ast * 100) }}%</td>
                </tr>
              </tbody>
            </table>
            <div class="codes">
              <div>
                <h4>{{ compareResult.student1_name }}</h4>
                <pre>{{ compareResult.code1 }}</pre>
              </div>
              <div>
                <h4>{{ compareResult.student2_name }}</h4>
                <pre>{{ compareResult.code2 }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; background: var(--bg-page); }

.appbar {
  background: var(--header-bg);
  color: var(--header-text);
  padding: 0.7rem 1.25rem;
  display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.appbar h1 { margin: 0; font-size: 1.05rem; }
.appbar .meta { font-size: 0.78rem; color: rgba(255,255,255,0.75); }
.appbar .actions { display: flex; gap: 0.5rem; }
.appbar .btn {
  background: rgba(255,255,255,0.1);
  border-color: rgba(255,255,255,0.25);
  color: white;
}
.appbar .btn:hover:not(:disabled) { background: rgba(255,255,255,0.2); }

.body {
  max-width: 1500px;
  margin: 0 auto;
  padding: 1rem 1.25rem 2rem;
  display: flex; flex-direction: column; gap: 0.85rem;
}

.empty {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 2rem; text-align: center;
}
.empty p { margin: 0 0 1rem; color: var(--text-muted); }

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.card-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.55rem 0.9rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
}
.card-head h3 { margin: 0; font-size: 0.85rem; color: var(--text-strong); font-weight: 600; }
.card-head .card-meta { font-size: 0.78rem; color: var(--text-muted); }

.control-row {
  padding: 1rem 1rem 0.5rem;
  display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
}
.threshold { display: flex; align-items: center; gap: 0.5rem; }
.threshold .lbl { font-size: 0.85rem; color: var(--text-muted); }
.threshold input[type="range"] { width: 220px; }
.threshold strong { color: var(--accent); font-size: 1rem; min-width: 3em; }
.btn.big { padding: 0.6rem 1.2rem; font-size: 0.95rem; }
.hint {
  margin: 0.4rem 1rem 1rem;
  font-size: 0.8rem; color: var(--text-muted);
}

.error {
  color: var(--danger);
  background: var(--danger-soft);
  padding: 0.55rem 0.85rem;
  border-radius: 6px;
}

.progress {
  background: var(--accent-soft);
  border-color: #bfdbfe;
}
.progress-row {
  display: flex; align-items: center; gap: 0.85rem;
  padding: 1rem 1.25rem;
}
.progress-row strong { color: var(--text-strong); font-size: 0.95rem; }
.progress-row p { margin: 0.2rem 0 0; color: var(--text); font-size: 0.85rem; }

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.7rem;
}
.stat {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.7rem 0.95rem;
  border-left: 3px solid var(--accent);
}
.stat.warn { border-left-color: var(--warning); }
.stat.danger { border-left-color: var(--danger); }
.stat .lbl {
  display: block; font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.stat strong {
  display: block; font-size: 1.55rem;
  color: var(--text-strong);
  margin-top: 0.2rem;
}

.pairs ul { list-style: none; margin: 0; padding: 0.4rem 0; }
.pairs li {
  display: grid;
  grid-template-columns: 1fr 200px 80px;
  align-items: center; gap: 0.5rem;
  padding: 0.55rem 0.95rem;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background 0.1s;
}
.pairs li:last-child { border-bottom: none; }
.pairs li:hover { background: var(--bg-soft); }
.pairs li.low { border-left-color: var(--success); }
.pairs li.med { border-left-color: var(--warning); }
.pairs li.high { border-left-color: var(--danger); background: rgba(220, 38, 38, 0.04); }
.pair-names { display: flex; gap: 0.4rem; align-items: center; font-size: 0.92rem; }
.pair-names strong { color: var(--text-strong); }
.pair-names .sep { color: var(--text-muted); }
.pair-meta { color: var(--text-muted); font-size: 0.8rem; }
.pair-meta code { background: var(--code-bg); padding: 1px 5px; border-radius: 3px; }
.pair-score { text-align: right; font-weight: 700; font-size: 1.05rem; }
.pair-score.low { color: var(--success); }
.pair-score.med { color: var(--warning); }
.pair-score.high { color: var(--danger); }

.placeholder {
  margin: 0; padding: 1.5rem; text-align: center;
  color: var(--text-muted); font-style: italic;
}

.matrix-scroll { overflow: auto; max-height: 600px; padding: 0.5rem; }
.matrix table { border-collapse: collapse; }
.matrix th {
  position: sticky;
  background: var(--bg-card);
  padding: 4px 6px;
  font-size: 0.7rem;
  font-family: ui-monospace, monospace;
  color: var(--text-muted);
  border: 1px solid var(--border);
  z-index: 1;
}
.matrix thead th { top: 0; }
.matrix tbody th { left: 0; text-align: right; }
.matrix td {
  width: 18px; height: 18px;
  border: 1px solid white;
  cursor: pointer;
  transition: outline 0.05s;
}
.matrix td:hover {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
  z-index: 2;
  position: relative;
  transform: scale(1.4);
}

/* spinner */
.spin {
  display: inline-block;
  width: 12px; height: 12px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  margin-right: 0.4rem;
  animation: spin 0.7s linear infinite;
  vertical-align: middle;
}
.big-spin {
  display: inline-block;
  width: 36px; height: 36px;
  border: 4px solid var(--accent);
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Modal */
.modal-bg {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex; align-items: center; justify-content: center;
  z-index: 50;
}
.modal {
  background: var(--bg-card);
  width: min(1100px, 95vw);
  max-height: 90vh;
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
}
.modal > header h3 { margin: 0; font-size: 0.95rem; }
.modal > header .overall { color: #93c5fd; }
.modal > header .ghost {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.25);
  color: white;
  padding: 0.25rem 0.55rem;
  font-size: 0.85rem;
}
.modal-body { padding: 0.95rem 1.1rem; overflow-y: auto; }
.modal-body h4 { margin: 0.5rem 0 0.5rem; color: var(--text-strong); font-size: 0.9rem; }

.qsim { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 1rem; }
.qsim th, .qsim td { padding: 0.4rem 0.7rem; border-bottom: 1px solid var(--border); text-align: left; }
.qsim th { background: var(--bg-soft); color: var(--text-muted); font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.4px; }
.qsim td.low { color: var(--success); font-weight: 600; }
.qsim td.med { color: var(--warning); font-weight: 600; }
.qsim td.high { color: var(--danger); font-weight: 700; }

.codes { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.codes pre {
  margin: 0; padding: 0.65rem 0.85rem;
  background: var(--code-bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: ui-monospace, monospace; font-size: 0.8rem;
  max-height: 400px; overflow: auto;
  white-space: pre-wrap;
}

.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.18s; }

@media (max-width: 900px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
  .codes { grid-template-columns: 1fr; }
  .pairs li { grid-template-columns: 1fr 70px; }
  .pair-meta { grid-column: 1 / 3; }
}
</style>
