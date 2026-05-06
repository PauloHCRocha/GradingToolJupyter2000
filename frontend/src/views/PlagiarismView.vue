<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { plagiarismAnalyze, plagiarismCompare } from '../api/client'
import type { PlagiarismAnalyzeResponse, PlagiarismCompareResponse } from '../api/client'

const session = useSessionStore()
const router = useRouter()

const threshold = ref(0.85)
const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<PlagiarismAnalyzeResponse | null>(null)

const compareLoading = ref(false)
const compareResult = ref<PlagiarismCompareResponse | null>(null)

const filteredPairs = computed(() => result.value?.suspicious_pairs ?? [])

async function analyze() {
  loading.value = true
  error.value = null
  try {
    result.value = await plagiarismAnalyze(threshold.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
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
  if (isDiagonal) return '#3a3a3a'
  if (v < 0.3) return `hsl(140, 50%, ${20 + v * 30}%)`
  if (v < 0.7) return `hsl(${140 - (v - 0.3) * 80}, 60%, ${30 + v * 10}%)`
  return `hsl(${30 - (v - 0.7) * 100}, 75%, ${30 + v * 15}%)`
}
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="left">
        <button class="ghost" @click="router.push('/grading')">← Grading</button>
        <h1>Plagiarism detection</h1>
      </div>
      <div class="right">
        <button class="ghost" @click="router.push('/setup')">Setup</button>
      </div>
    </header>

    <section v-if="session.students.length < 2" class="placeholder">
      Need at least 2 student submissions to detect plagiarism.
    </section>

    <template v-else>
      <section class="controls">
        <label>
          Threshold: <strong>{{ threshold.toFixed(2) }}</strong>
          <input type="range" min="0.5" max="1" step="0.01" v-model.number="threshold" />
        </label>
        <button class="primary" :disabled="loading" @click="analyze">
          {{ loading ? 'Analyzing…' : '▶ Run plagiarism detection' }}
        </button>
      </section>

      <p v-if="error" class="error">{{ error }}</p>

      <section v-if="result" class="stats">
        <div class="stat">
          <span class="label">Total comparisons</span>
          <strong>{{ result.stats.total_comparisons }}</strong>
        </div>
        <div class="stat warn">
          <span class="label">Suspicious pairs</span>
          <strong>{{ result.stats.suspicious_count }}</strong>
        </div>
        <div class="stat danger">
          <span class="label">High similarity (≥95%)</span>
          <strong>{{ result.stats.high_similarity_count }}</strong>
        </div>
        <div class="stat">
          <span class="label">Average similarity</span>
          <strong>{{ Math.round(result.stats.avg_similarity * 100) }}%</strong>
        </div>
      </section>

      <section v-if="result" class="pairs">
        <h2>Suspicious pairs</h2>
        <p v-if="!filteredPairs.length" class="placeholder">
          No pairs above threshold {{ threshold.toFixed(2) }}.
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
              <code>#{{ p.student1_id }}</code> ·
              <code>#{{ p.student2_id }}</code>
            </div>
            <div class="pair-score" :class="severity(p.similarity)">
              {{ Math.round(p.similarity * 100) }}%
            </div>
          </li>
        </ul>
      </section>

      <section v-if="result" class="matrix">
        <h2>Similarity matrix</h2>
        <div class="matrix-scroll">
          <table>
            <thead>
              <tr>
                <th></th>
                <th
                  v-for="(name, j) in result.student_names"
                  :key="j"
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

    <Transition name="modal">
      <div v-if="compareResult || compareLoading" class="modal-bg" @click.self="compareResult = null">
        <div class="modal">
          <header>
            <h3 v-if="compareResult">
              {{ compareResult.student1_name }} ↔ {{ compareResult.student2_name }}
              <span class="overall">
                · overall {{ Math.round(compareResult.overall_similarity * 100) }}%
              </span>
            </h3>
            <h3 v-else>Loading comparison…</h3>
            <button class="ghost" @click="compareResult = null">✕</button>
          </header>
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
.page {
  min-height: 100vh;
  display: flex; flex-direction: column;
  background: var(--bg-primary);
  color: var(--text);
}
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 1rem; height: 56px;
  background: var(--header-bg);
  border-bottom: 1px solid var(--border-strong);
}
.topbar .left, .topbar .right { display: flex; gap: 0.6rem; align-items: center; }
.topbar h1 { margin: 0; font-size: 1rem; color: var(--text-strong); }
button.ghost {
  background: transparent; color: var(--text);
  border: 1px solid var(--border-strong);
  padding: 0.35rem 0.7rem; border-radius: 4px;
  font-size: 0.85rem;
}
button.ghost:hover { background: rgba(255,255,255,0.06); }
button.primary {
  background: var(--accent); color: white; border: none;
  padding: 0.45rem 0.9rem; border-radius: 4px; font-size: 0.9rem;
}
button.primary:hover:not(:disabled) { background: var(--accent-hover); }
button:disabled { opacity: 0.5; cursor: not-allowed; }

.controls {
  display: flex; align-items: center; gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}
.controls label {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.9rem;
}
.controls input[type="range"] { width: 200px; }

.placeholder {
  color: var(--text-muted);
  padding: 2rem;
  text-align: center;
  font-style: italic;
}
.error {
  color: var(--danger);
  background: rgba(231, 76, 60, 0.12);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin: 1rem 1.5rem;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  padding: 1rem 1.5rem;
}
.stat {
  background: var(--bg-elevated);
  padding: 0.75rem 1rem;
  border-radius: 6px;
  border-left: 3px solid var(--accent);
}
.stat.warn { border-left-color: var(--warning); }
.stat.danger { border-left-color: var(--danger); }
.stat .label {
  display: block; font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.stat strong {
  display: block;
  font-size: 1.6rem;
  color: var(--text-strong);
  margin-top: 0.25rem;
}

.pairs, .matrix {
  padding: 0.5rem 1.5rem 1.5rem;
}
.pairs h2, .matrix h2 {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  margin: 0.5rem 0 0.5rem;
}

.pairs ul { list-style: none; margin: 0; padding: 0; }
.pairs li {
  display: grid;
  grid-template-columns: 1fr 200px 80px;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.85rem;
  margin-bottom: 0.3rem;
  background: var(--bg-elevated);
  border-radius: 4px;
  border-left: 3px solid var(--text-muted);
  cursor: pointer;
  transition: background 0.1s;
}
.pairs li.low { border-left-color: var(--success); }
.pairs li.med { border-left-color: var(--warning); }
.pairs li.high { border-left-color: var(--danger); }
.pairs li:hover { background: var(--bg-panel); }

.pair-names { display: flex; gap: 0.35rem; align-items: center; font-size: 0.9rem; }
.pair-names strong { color: var(--text-strong); }
.pair-names .sep { color: var(--text-muted); }
.pair-meta { color: var(--text-muted); font-size: 0.8rem; }
.pair-meta code { background: var(--bg-input); padding: 1px 5px; border-radius: 3px; }

.pair-score {
  text-align: right;
  font-weight: 700;
  font-size: 1rem;
}
.pair-score.low { color: var(--success); }
.pair-score.med { color: var(--warning); }
.pair-score.high { color: var(--danger); }

.matrix-scroll { overflow: auto; max-height: 600px; border: 1px solid var(--border); border-radius: 4px; }
.matrix table { border-collapse: collapse; }
.matrix th {
  position: sticky;
  background: var(--bg-elevated);
  z-index: 1;
  padding: 4px 6px;
  font-size: 0.7rem;
  font-family: ui-monospace, monospace;
  color: var(--text-muted);
  border: 1px solid var(--border);
}
.matrix thead th { top: 0; }
.matrix tbody th { left: 0; text-align: right; }
.matrix td {
  width: 18px; height: 18px;
  border: 1px solid #1a1a1a;
  cursor: pointer;
}
.matrix td:hover { outline: 2px solid var(--accent); outline-offset: -2px; z-index: 2; position: relative; }

/* Modal */
.modal-bg {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 50;
}
.modal {
  background: var(--bg-elevated);
  width: min(1100px, 95vw);
  max-height: 90vh;
  border-radius: 8px;
  border: 1px solid var(--border-strong);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.modal > header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.6rem 0.9rem;
  background: var(--header-bg);
  border-bottom: 1px solid var(--border);
}
.modal > header h3 { margin: 0; font-size: 0.95rem; color: var(--text-strong); }
.modal-body { padding: 0.9rem 1.1rem; overflow-y: auto; }
.modal-body h4 { margin: 0.5rem 0 0.4rem; color: var(--text-strong); font-size: 0.9rem; }
.modal-body .overall { color: var(--accent); }

.qsim { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.qsim th, .qsim td { padding: 0.35rem 0.6rem; border-bottom: 1px solid var(--border); text-align: left; }
.qsim th { background: var(--bg-panel); color: var(--text-muted); font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.4px; }
.qsim td.low { color: var(--success); font-weight: 600; }
.qsim td.med { color: var(--warning); font-weight: 600; }
.qsim td.high { color: var(--danger); font-weight: 700; }

.codes { display: grid; grid-template-columns: 1fr 1fr; gap: 0.7rem; margin-top: 1rem; }
.codes pre {
  margin: 0; padding: 0.6rem 0.8rem;
  background: var(--code-bg); color: var(--text);
  border-radius: 4px;
  font-family: ui-monospace, monospace; font-size: 0.8rem;
  max-height: 400px; overflow: auto;
  white-space: pre-wrap;
}

.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.18s; }
</style>
