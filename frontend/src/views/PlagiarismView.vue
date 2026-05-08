<script setup lang="ts">
/**
 * Plagiarism workspace orchestrator.
 *
 * Owns the threshold controls, runs the analysis, holds the result, and
 * dispatches it to the four tab components. The compare modal lives here
 * (one shared instance) — tabs raise `compare` events and the modal calls
 * the Pyodide compare function lazily.
 *
 * Cleanup contract:
 * - All in-flight fetches are aborted on route leave.
 * - The vis-network instance lives inside <NetworkTab> and is destroyed in
 *   its own onBeforeUnmount.
 * - The Heatmap canvas frees its backing store on unmount.
 * - PDF export is awaited before the modal can close (the user gets a
 *   spinner from the modal's loading state).
 */
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import {
  plagiarismAnalyze,
  plagiarismCompare,
  plagiarismCluster,
} from '../api/client'
import type {
  PlagiarismAnalyzeResponse,
  PlagiarismCompareResponse,
  SuspiciousPair,
} from '../api/client'
import HeatmapTab from '../components/plagiarism/HeatmapTab.vue'
import ClustersTab from '../components/plagiarism/ClustersTab.vue'
import PairsTab from '../components/plagiarism/PairsTab.vue'
import CompareModal from '../components/plagiarism/CompareModal.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

// Heavy chunks loaded only when actually used.
//   - vis-network is ~600KB; only the Network tab needs it.
//   - jsPDF + autotable is ~150KB; only PDF export needs it.
const NetworkTab = defineAsyncComponent(() => import('../components/plagiarism/NetworkTab.vue'))

async function lazyExportPair(pair: SuspiciousPair, analyze: PlagiarismAnalyzeResponse) {
  const m = await import('../runtime/pdfExport')
  return m.exportPairPdf(pair, analyze)
}
async function lazyExportFull(pairs: SuspiciousPair[], analyze: PlagiarismAnalyzeResponse) {
  const m = await import('../runtime/pdfExport')
  return m.exportFullPdf(pairs, analyze)
}

const session = useSessionStore()
const router = useRouter()

type Tab = 'heatmap' | 'network' | 'clusters' | 'pairs'

const activeTab = ref<Tab>('heatmap')
const threshold = ref(0.85)
const clusterThreshold = ref(0.7)

const analyzing = ref(false)
const startedAt = ref<number | null>(null)
const elapsed = ref(0)
const error = ref<string | null>(null)
const result = ref<PlagiarismAnalyzeResponse | null>(null)

const compareLoading = ref(false)
const compareError = ref<string | null>(null)
const compareResult = ref<PlagiarismCompareResponse | null>(null)
const compareQueue = ref<{ ids: string[]; cursor: number } | null>(null)
const exportingPdf = ref(false)

let elapsedTimer: number | null = null
let analyzeAbort: AbortController | null = null
let compareAbort: AbortController | null = null

const studentCount = computed(() => session.students.length)
const estComparisons = computed(() => {
  const n = studentCount.value
  return n < 2 ? 0 : (n * (n - 1)) / 2
})

function clearElapsedTimer() {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

function abortAll() {
  if (analyzeAbort) {
    analyzeAbort.abort()
    analyzeAbort = null
  }
  if (compareAbort) {
    compareAbort.abort()
    compareAbort = null
  }
  clearElapsedTimer()
  analyzing.value = false
  compareLoading.value = false
  exportingPdf.value = false
}

onMounted(async () => {
  if (!session.students.length) {
    try {
      await session.refreshStudents()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    }
  }
})
onBeforeRouteLeave(() => abortAll())
onBeforeUnmount(() => abortAll())

async function runAnalyze() {
  if (analyzing.value) return
  abortAll()
  analyzing.value = true
  error.value = null
  result.value = null
  startedAt.value = Date.now()
  elapsed.value = 0
  elapsedTimer = window.setInterval(() => {
    if (startedAt.value) elapsed.value = (Date.now() - startedAt.value) / 1000
  }, 100)
  analyzeAbort = new AbortController()
  try {
    result.value = await plagiarismAnalyze(threshold.value, clusterThreshold.value, analyzeAbort.signal)
  } catch (e) {
    if ((e as Error).name === 'AbortError') return
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    clearElapsedTimer()
    analyzing.value = false
    analyzeAbort = null
  }
}

async function recomputeClusters() {
  if (!result.value) return
  // Re-cluster without recomputing the matrix.
  try {
    const payload = await plagiarismCluster(clusterThreshold.value)
    result.value = {
      ...result.value,
      cluster_threshold: clusterThreshold.value,
      cluster_assignments: payload.cluster_assignments,
      clusters: payload.clusters,
      outliers: payload.outliers,
      num_clusters: payload.num_clusters,
      stats: {
        ...result.value.stats,
        num_clusters: payload.num_clusters,
        largest_cluster: Math.max(0, ...payload.clusters.map((c) => c.size)),
        outliers_count: payload.outliers.length,
      },
      // Re-tag suspicious pairs with the new cluster assignments.
      suspicious_pairs: result.value.suspicious_pairs.map((p) => {
        const ca = payload.cluster_assignments[p.student1_index]
        const cb = payload.cluster_assignments[p.student2_index]
        return { ...p, cluster_id: ca >= 0 && ca === cb ? ca : -1 }
      }),
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function openCompare(s1: string, s2: string) {
  if (compareAbort) compareAbort.abort()
  compareAbort = new AbortController()
  compareLoading.value = true
  compareError.value = null
  compareResult.value = null
  try {
    compareResult.value = await plagiarismCompare(s1, s2, compareAbort.signal)
  } catch (e) {
    if ((e as Error).name === 'AbortError') return
    compareError.value = e instanceof Error ? e.message : String(e)
    compareResult.value = null
  } finally {
    compareLoading.value = false
    compareAbort = null
  }
}

function closeCompare() {
  if (compareAbort) {
    compareAbort.abort()
    compareAbort = null
  }
  compareResult.value = null
  compareLoading.value = false
  compareError.value = null
  compareQueue.value = null
}

async function compareCluster(memberIds: string[]) {
  if (memberIds.length < 2) return
  // Walk through pairs (member i ↔ member i+1) one at a time. The user
  // closes the modal to advance, but we also support next/prev later.
  compareQueue.value = { ids: memberIds, cursor: 0 }
  await openCompare(memberIds[0], memberIds[1])
}

async function exportPairPdfHandler(pair: SuspiciousPair) {
  if (!result.value) return
  exportingPdf.value = true
  try {
    await lazyExportPair(pair, result.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    exportingPdf.value = false
  }
}

async function exportModalPdf() {
  if (!result.value || !compareResult.value) return
  const pair = result.value.suspicious_pairs.find(
    (p) =>
      p.student1_id === compareResult.value!.student1_id &&
      p.student2_id === compareResult.value!.student2_id,
  ) ?? {
    student1_id: compareResult.value.student1_id,
    student1_name: compareResult.value.student1_name,
    student1_index: -1,
    student2_id: compareResult.value.student2_id,
    student2_name: compareResult.value.student2_name,
    student2_index: -1,
    similarity: compareResult.value.overall_similarity,
    cluster_id: -1,
  }
  await exportPairPdfHandler(pair)
}

async function exportFullReport() {
  if (!result.value || !result.value.suspicious_pairs.length) return
  exportingPdf.value = true
  try {
    await lazyExportFull(result.value.suspicious_pairs, result.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    exportingPdf.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="appbar">
      <RouterLink to="/" class="title" title="Back to landing">
        <h1>Granymede</h1>
        <span class="meta">Plagiarism · {{ studentCount }} students loaded</span>
      </RouterLink>
      <div class="actions">
        <button class="btn" @click="router.push('/grading')">← Back to grading</button>
        <button class="btn" @click="router.push('/setup')">Setup</button>
        <ThemeToggle />
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
              <span class="lbl">Detection threshold</span>
              <input type="range" min="0.5" max="1" step="0.01"
                     v-model.number="threshold" :disabled="analyzing" />
              <strong>{{ threshold.toFixed(2) }}</strong>
            </label>
            <label class="threshold">
              <span class="lbl">Cluster threshold</span>
              <input type="range" min="0.3" max="1" step="0.01"
                     v-model.number="clusterThreshold" :disabled="analyzing"
                     @change="result && recomputeClusters()" />
              <strong>{{ clusterThreshold.toFixed(2) }}</strong>
            </label>
            <button class="btn btn-primary big" :disabled="analyzing" @click="runAnalyze">
              <span v-if="analyzing" class="spin" />
              {{ analyzing ? 'Analysing…' : 'Run analysis' }}
            </button>
          </div>
          <p class="hint">
            Hybrid similarity: 40% TF-IDF · 30% AST · 30% token Jaccard. Pairs above
            <strong>detection threshold</strong> are flagged. Clustering uses a separate, lower
            <strong>cluster threshold</strong> so loosely-related groups still surface.
          </p>
        </section>

        <p v-if="error" class="error">{{ error }}</p>

        <section v-if="analyzing" class="card progress">
          <div class="progress-row">
            <span class="big-spin" />
            <div>
              <strong>Computing similarity matrix…</strong>
              <p>
                Comparing {{ estComparisons }} pairs across {{ studentCount }} students.
                Elapsed {{ elapsed.toFixed(1) }}s.
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
          <div class="stat info">
            <span class="lbl">Clusters</span>
            <strong>{{ result.stats.num_clusters }}</strong>
            <span class="sub">largest: {{ result.stats.largest_cluster }}</span>
          </div>
        </section>

        <section v-if="result" class="card tabs-card">
          <nav class="tabbar">
            <button :class="{ active: activeTab === 'heatmap' }" @click="activeTab = 'heatmap'">
              Heatmap
            </button>
            <button :class="{ active: activeTab === 'network' }" @click="activeTab = 'network'">
              Network
            </button>
            <button :class="{ active: activeTab === 'clusters' }" @click="activeTab = 'clusters'">
              Clusters
              <span class="badge">{{ result.stats.num_clusters }}</span>
            </button>
            <button :class="{ active: activeTab === 'pairs' }" @click="activeTab = 'pairs'">
              Pairs
              <span class="badge">{{ result.stats.suspicious_count }}</span>
            </button>
            <div class="tab-spacer" />
            <button class="btn btn-pdf" :disabled="exportingPdf || !result.suspicious_pairs.length"
                    @click="exportFullReport">
              <span v-if="exportingPdf" class="spin" />
              Export PDF report
            </button>
          </nav>

          <KeepAlive>
            <HeatmapTab
              v-if="activeTab === 'heatmap'"
              key="heatmap"
              :matrix="result.matrix"
              :student-ids="result.student_ids"
              :student-names="result.student_names"
              @compare="openCompare"
            />
          </KeepAlive>

          <NetworkTab
            v-if="activeTab === 'network'"
            :student-ids="result.student_ids"
            :student-names="result.student_names"
            :pairs="result.suspicious_pairs"
            :cluster-assignments="result.cluster_assignments"
            :clusters="result.clusters"
            @compare="openCompare"
          />

          <ClustersTab
            v-if="activeTab === 'clusters'"
            :clusters="result.clusters"
            :outliers-count="result.outliers.length"
            :total-students="result.student_ids.length"
            @compare="openCompare"
            @compare-all="compareCluster"
          />

          <PairsTab
            v-if="activeTab === 'pairs'"
            :pairs="result.suspicious_pairs"
            :clusters="result.clusters"
            :threshold="threshold"
            @compare="openCompare"
            @export-pdf="exportPairPdfHandler"
          />
        </section>
      </template>
    </main>

    <CompareModal
      :result="compareResult"
      :loading="compareLoading"
      @close="closeCompare"
      @export-pdf="exportModalPdf"
    />
    <p v-if="compareError" class="error floating">{{ compareError }}</p>
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
.appbar h1 { margin: 0; font-size: 1.05rem; color: var(--text-strong); color: white; }
.appbar .meta { font-size: 0.78rem; color: rgba(255,255,255,0.75); }
.appbar .title {
  display: flex;
  flex-direction: column;
  color: inherit;
  text-decoration: none;
  padding: 0.25rem 0.55rem;
  margin: -0.25rem -0.55rem;
  border-radius: 6px;
  transition: background 0.15s;
}
.appbar .title:hover { background: rgba(255, 255, 255, 0.08); text-decoration: none; }
.appbar .title:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }
.appbar .actions { display: flex; gap: 0.5rem; }
.appbar .btn {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.25);
  color: white;
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  font-size: 0.85rem;
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
  display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap;
}
.threshold { display: flex; align-items: center; gap: 0.5rem; }
.threshold .lbl { font-size: 0.85rem; color: var(--text-muted); }
.threshold input[type="range"] { width: 180px; }
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
.error.floating {
  position: fixed; bottom: 1rem; right: 1rem;
  z-index: 60;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  max-width: 480px;
}

.progress {
  background: var(--accent-soft);
  border-color: var(--accent-bd);
}
.progress-row {
  display: flex; align-items: center; gap: 0.85rem;
  padding: 1rem 1.25rem;
}
.progress-row strong { color: var(--text-strong); font-size: 0.95rem; }
.progress-row p { margin: 0.2rem 0 0; color: var(--text); font-size: 0.85rem; }

.stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
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
.stat.info { border-left-color: #6366f1; }
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
.stat .sub { font-size: 0.72rem; color: var(--text-muted); }

.tabs-card { padding: 0; }
.tabbar {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.4rem 0.5rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.tabbar > button {
  background: transparent;
  color: var(--text);
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0.4rem 0.7rem;
  font-size: 0.85rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  transition: background 0.1s, border-color 0.1s;
}
.tabbar > button:hover { background: var(--bg-card); }
.tabbar > button.active {
  background: var(--bg-card);
  border-color: var(--border-strong);
  color: var(--text-strong);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.tabbar .badge {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.72rem;
  font-weight: 600;
}
.tabbar > button.active .badge { background: var(--accent); color: white; }
.tab-spacer { flex: 1 1 auto; }
.btn-pdf {
  background: var(--danger);
  color: white;
  border: 1px solid var(--danger);
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-size: 0.82rem;
}
.btn-pdf:hover:not(:disabled) { background: #b91c1c; border-color: #b91c1c; }
.btn-pdf:disabled { opacity: 0.55; cursor: not-allowed; }

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

@media (max-width: 1100px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
