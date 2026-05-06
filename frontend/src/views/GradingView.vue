<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { exportGradesUrl, runCode, suggestGrade } from '../api/client'
import type { CellOut, RunCodeResponse, SuggestResponse } from '../api/client'
import NotebookViewer from '../components/NotebookViewer.vue'

const session = useSessionStore()
const router = useRouter()

const draft = reactive<Record<string, { points: number; comment: string }>>({})
const saving = ref<Record<string, boolean>>({})
const suggesting = ref(false)
const error = ref<string | null>(null)
const toast = ref<{ kind: 'ok' | 'err'; text: string } | null>(null)

const runnerCode = ref('')
const runnerStdin = ref('')
const runnerResult = ref<RunCodeResponse | null>(null)
const runnerLoading = ref(false)

const lastSuggest = ref<SuggestResponse | null>(null)

const totalMax = computed(() =>
  session.questions.reduce((acc, q) => acc + (Number(q.max_points) || 0), 0),
)
const totalCurrent = computed(() =>
  Object.values(session.studentGrades).reduce((acc, g) => acc + (g?.points ?? 0), 0),
)
const gradedCount = computed(() => session.students.filter((s) => s.total_grade > 0).length)

const selectedQuestion = computed(() =>
  session.questions.find((q) => q.id === session.selectedQuestionId) ?? null,
)

const selectedQuestionMax = computed(() =>
  selectedQuestion.value ? Number(selectedQuestion.value.max_points) || 0 : 0,
)

const solutionCellsForQuestion = computed<CellOut[]>(() => {
  const sd = session.solutionDetail
  const qid = session.selectedQuestionId
  if (!sd) return []
  if (!qid) return sd.cells
  const indices = sd.question_windows[qid] ?? []
  return indices.map((i) => sd.cells[i]).filter(Boolean)
})

const studentCellsForQuestion = computed<CellOut[]>(() => {
  const sd = session.studentDetail
  const qid = session.selectedQuestionId
  if (!sd) return []
  if (!qid) return sd.cells
  const indices = sd.question_windows[qid] ?? []
  return indices.map((i) => sd.cells[i]).filter(Boolean)
})

const studentCodeJoined = computed(() =>
  studentCellsForQuestion.value
    .filter((c) => c.cell_type === 'code')
    .map((c) => c.source)
    .join('\n\n'),
)

watch(
  () => session.selectedQuestionId,
  () => {
    runnerCode.value = studentCodeJoined.value
    runnerResult.value = null
  },
)

watch(
  () => session.studentDetail?.info.id,
  () => {
    runnerCode.value = studentCodeJoined.value
    runnerResult.value = null
  },
)

onMounted(async () => {
  if (!session.questions.length || !session.students.length) {
    router.replace('/setup')
    return
  }
  await session.ensureSolutionDetail()
  if (!session.selectedStudentId) {
    const first = session.students.find((s) => !s.has_error)
    if (first) await selectStudent(first.id)
  } else {
    syncDraft()
  }
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
})

function onKeyDown(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    void session.navigate(-1).then(syncDraft)
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    void session.navigate(+1).then(syncDraft)
  }
}

async function selectStudent(id: string) {
  error.value = null
  lastSuggest.value = null
  try {
    await session.selectStudent(id)
    syncDraft()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function onStudentChange(e: Event) {
  await selectStudent((e.target as HTMLSelectElement).value)
}

function syncDraft() {
  for (const q of session.questions) {
    const g = session.studentGrades[q.id]
    if (!draft[q.id]) {
      draft[q.id] = { points: g ? Number(g.points) : 0, comment: g ? g.comment : '' }
    } else {
      draft[q.id].points = g ? Number(g.points) : 0
      draft[q.id].comment = g ? g.comment : ''
    }
  }
}

watch(() => session.selectedStudentId, syncDraft)

function showToast(kind: 'ok' | 'err', text: string) {
  toast.value = { kind, text }
  setTimeout(() => {
    toast.value = null
  }, 2400)
}

async function save(qid: string) {
  if (!draft[qid]) return
  saving.value[qid] = true
  error.value = null
  try {
    await session.saveGrade(qid, Number(draft[qid].points) || 0, draft[qid].comment)
    showToast('ok', `Saved ${qid}`)
  } catch (e) {
    showToast('err', e instanceof Error ? e.message : String(e))
  } finally {
    saving.value[qid] = false
  }
}

async function quickGrade(qid: string, pct: number) {
  const q = session.questions.find((x) => x.id === qid)
  if (!q) return
  draft[qid].points = Math.round((q.max_points || 0) * pct * 100) / 100
  await save(qid)
}

function clamp(qid: string) {
  const q = session.questions.find((x) => x.id === qid)
  if (!q) return
  const max = Number(q.max_points) || 0
  if (draft[qid].points < 0) draft[qid].points = 0
  if (draft[qid].points > max) draft[qid].points = max
}

async function onSuggest() {
  if (!session.selectedStudentId || !session.selectedQuestionId) return
  suggesting.value = true
  lastSuggest.value = null
  try {
    const res = await suggestGrade(session.selectedStudentId, session.selectedQuestionId)
    lastSuggest.value = res
    if (res.points !== null && draft[session.selectedQuestionId]) {
      draft[session.selectedQuestionId].points = res.points
      draft[session.selectedQuestionId].comment = res.comment
    }
  } catch (e) {
    showToast('err', e instanceof Error ? e.message : String(e))
  } finally {
    suggesting.value = false
  }
}

async function onRun() {
  runnerLoading.value = true
  runnerResult.value = null
  try {
    runnerResult.value = await runCode(runnerCode.value, runnerStdin.value)
  } catch (e) {
    runnerResult.value = {
      success: false,
      output: '',
      error: e instanceof Error ? e.message : String(e),
      duration_ms: 0,
    }
  } finally {
    runnerLoading.value = false
  }
}

function loadStudentCodeIntoRunner() {
  runnerCode.value = studentCodeJoined.value
  runnerResult.value = null
}

function gradeFor(qid: string): number | null {
  const g = session.studentGrades[qid]
  return g ? Number(g.points) : null
}
</script>

<template>
  <div class="page">
    <header class="appbar">
      <div class="title">
        <h1>📋 Assignment Grading Tool</h1>
        <span class="meta">
          {{ session.students.length }} students · {{ gradedCount }} graded ·
          {{ session.questions.length }} questions ({{ totalMax }} pts total)
        </span>
      </div>
      <div class="actions">
        <button class="btn" @click="router.push('/setup')">← Setup</button>
        <a class="btn btn-primary" :href="exportGradesUrl()" download>📥 Export CSV</a>
        <button class="btn btn-warn" @click="router.push('/plagiarism')">⚠ Plagiarism</button>
      </div>
    </header>

    <nav class="topnav">
      <button class="btn nav-btn" @click="session.navigate(-1).then(syncDraft)">← Previous</button>
      <div class="cur-student">
        <span v-if="session.studentDetail" class="cs-name">
          {{ session.studentDetail.info.name }}
        </span>
        <span v-if="session.studentDetail" class="cs-meta">
          #{{ session.studentDetail.info.id }} ·
          <code>{{ session.studentDetail.info.filename }}</code>
        </span>
        <span v-else class="cs-meta muted">No student selected</span>
      </div>
      <button class="btn nav-btn" @click="session.navigate(+1).then(syncDraft)">Next →</button>
    </nav>

    <main class="body">
      <section class="row split">
        <article class="card selector">
          <header class="card-head">
            <h3>Select student</h3>
            <div class="sort-toggle">
              <span class="lbl">Sort by</span>
              <button :class="{ active: session.sortOrder === 'name' }"
                      @click="session.setSortOrder('name')">Name</button>
              <button :class="{ active: session.sortOrder === 'number' }"
                      @click="session.setSortOrder('number')">Number</button>
            </div>
          </header>
          <select class="student-select" :value="session.selectedStudentId" @change="onStudentChange">
            <option value="" disabled>— pick a student —</option>
            <option v-for="s in session.students" :key="s.id" :value="s.id" :disabled="s.has_error">
              {{ s.name }} (#{{ s.id }})
              <template v-if="s.total_grade > 0">— {{ s.total_grade.toFixed(1) }}/{{ totalMax }}</template>
              <template v-if="s.invisible_count">⚠ {{ s.invisible_count }}</template>
              <template v-if="s.has_error">⚠ error</template>
            </option>
          </select>
          <p class="hint">Tip: use ← / → keys to navigate.</p>
          <div v-if="session.studentDetail?.invisible_findings.length" class="alert warn">
            ⚠ <strong>{{ session.studentDetail.invisible_findings.length }}</strong>
            suspicious unicode character(s) detected in code (possible AI paste).
          </div>
        </article>

        <article class="card summary">
          <header class="card-head"><h3>Grade summary</h3></header>
          <ul class="summary-list">
            <li v-for="q in session.questions" :key="q.id"
                :class="{ done: gradeFor(q.id) !== null && (gradeFor(q.id) ?? 0) > 0 }">
              <span class="qid">{{ q.id }}</span>
              <span class="qval">
                <template v-if="gradeFor(q.id) !== null">
                  {{ gradeFor(q.id)?.toFixed(2) }}
                </template>
                <template v-else>—</template>
                <span class="qmax"> / {{ q.max_points }}</span>
              </span>
            </li>
            <li class="total">
              <span class="qid">Total</span>
              <span class="qval"><strong>{{ totalCurrent.toFixed(1) }}</strong> / {{ totalMax }}</span>
            </li>
          </ul>
        </article>
      </section>

      <section class="card questions">
        <header class="card-head"><h3>Questions</h3></header>
        <div class="qbar">
          <button v-for="q in session.questions" :key="q.id"
                  class="qchip"
                  :class="{ active: q.id === session.selectedQuestionId, graded: (gradeFor(q.id) ?? 0) > 0 }"
                  @click="session.selectQuestion(q.id)">
            <span class="qchip-id">{{ q.id }}</span>
            <span class="qchip-pts">{{ q.max_points }}pt</span>
          </button>
        </div>
        <p v-if="selectedQuestion" class="qstatement">
          {{ selectedQuestion.statement.slice(0, 360) }}{{ selectedQuestion.statement.length > 360 ? '…' : '' }}
        </p>
      </section>

      <section v-if="selectedQuestion && session.selectedStudentId" class="card grading">
        <header class="card-head">
          <h3>Grade · {{ selectedQuestion.label }}</h3>
          <span class="card-meta">Max: <strong>{{ selectedQuestionMax }}</strong></span>
        </header>
        <div class="grade-row">
          <div class="grade-input">
            <input
              type="number" step="0.25" min="0" :max="selectedQuestionMax"
              v-model.number="draft[selectedQuestion.id].points"
              @blur="clamp(selectedQuestion.id)"
            />
            <span class="of">/ {{ selectedQuestionMax }}</span>
          </div>
          <button class="btn btn-suggest" :disabled="suggesting" @click="onSuggest">
            <span v-if="suggesting" class="spin" />
            {{ suggesting ? 'Analyzing…' : '✨ Suggest grade' }}
          </button>
          <button class="btn btn-primary" :disabled="saving[selectedQuestion.id]"
                  @click="save(selectedQuestion.id)">
            {{ saving[selectedQuestion.id] ? 'Saving…' : '💾 Save grade' }}
          </button>
        </div>

        <div class="quick-row">
          <span class="quick-lbl">Quick grade</span>
          <button v-for="p in [0, 0.25, 0.5, 0.75, 1]" :key="p" class="btn quick"
                  @click="quickGrade(selectedQuestion.id, p)">
            {{ p * 100 }}%
          </button>
        </div>

        <textarea
          class="comment"
          v-model="draft[selectedQuestion.id].comment"
          placeholder="Comment (optional) — auto-filled when you click Suggest grade"
          rows="3"
        />

        <div v-if="lastSuggest" class="suggest-result" :class="lastSuggest.confidence">
          <header>
            <span class="conf-pill" :class="lastSuggest.confidence">{{ lastSuggest.confidence }}</span>
            <strong>{{ lastSuggest.points }} / {{ lastSuggest.max_points }}</strong>
            · score {{ Math.round(lastSuggest.score * 100) }}%
          </header>
          <pre class="suggest-comment">{{ lastSuggest.comment }}</pre>
        </div>
      </section>

      <section v-if="session.selectedStudentId" class="row split code-row">
        <article class="card pane">
          <header class="card-head solution"><h3>📘 Solution</h3></header>
          <div class="pane-body">
            <NotebookViewer :cells="solutionCellsForQuestion"
                            placeholder="No solution cells for this question." />
          </div>
        </article>
        <article class="card pane">
          <header class="card-head student">
            <h3>📝 Student submission</h3>
            <button class="btn btn-small" @click="loadStudentCodeIntoRunner">↓ Load to runner</button>
          </header>
          <div class="pane-body">
            <NotebookViewer :cells="studentCellsForQuestion"
                            placeholder="No student cells for this question." />
          </div>
        </article>
      </section>

      <section v-if="session.selectedStudentId" class="card runner">
        <header class="card-head">
          <h3>▶ Run code</h3>
          <span class="card-meta muted">Runs as a Python subprocess (10s timeout)</span>
        </header>
        <textarea class="code-in" v-model="runnerCode" rows="12"
                  placeholder="Paste or load the student's code here..." />
        <div class="run-row">
          <input class="stdin" v-model="runnerStdin" placeholder="Optional stdin" />
          <button class="btn btn-primary" :disabled="runnerLoading" @click="onRun">
            <span v-if="runnerLoading" class="spin" />
            {{ runnerLoading ? 'Running…' : '▶ Run' }}
          </button>
          <span v-if="runnerResult" class="run-meta" :class="runnerResult.success ? 'ok' : 'err'">
            {{ runnerResult.success ? '✓' : '✗' }} {{ runnerResult.duration_ms }}ms
          </span>
        </div>
        <div v-if="runnerResult" class="run-out">
          <div v-if="runnerResult.output">
            <span class="lbl">Output</span>
            <pre>{{ runnerResult.output }}</pre>
          </div>
          <div v-if="runnerResult.error">
            <span class="lbl err">Error</span>
            <pre class="err">{{ runnerResult.error }}</pre>
          </div>
        </div>
      </section>
    </main>

    <Transition name="toast">
      <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>
    </Transition>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg-page);
}

/* ---- App bar ---- */
.appbar {
  background: var(--header-bg);
  color: var(--header-text);
  padding: 0.7rem 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.appbar h1 { margin: 0; font-size: 1.05rem; font-weight: 600; }
.appbar .meta { font-size: 0.78rem; color: rgba(255,255,255,0.75); }
.appbar .actions { display: flex; gap: 0.5rem; }
.appbar .btn {
  background: rgba(255,255,255,0.1);
  border-color: rgba(255,255,255,0.25);
  color: white;
}
.appbar .btn:hover:not(:disabled) { background: rgba(255,255,255,0.2); }
.appbar .btn-primary { background: var(--accent); border-color: var(--accent); }
.appbar .btn-warn { background: var(--warning); border-color: var(--warning); color: white; }
.appbar .btn-warn:hover:not(:disabled) { background: #b45309; border-color: #b45309; }

/* ---- Top nav ---- */
.topnav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 1.25rem;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.nav-btn { min-width: 100px; }
.cur-student { flex: 1; display: flex; flex-direction: column; align-items: center; }
.cs-name { font-weight: 600; color: var(--text-strong); font-size: 0.95rem; }
.cs-meta { font-size: 0.78rem; color: var(--text-muted); }
.cs-meta code { background: var(--code-bg); padding: 1px 4px; border-radius: 3px; }
.cs-meta.muted { font-style: italic; }

/* ---- Body ---- */
.body {
  max-width: 1500px;
  margin: 0 auto;
  padding: 1rem 1.25rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.row.split { display: grid; grid-template-columns: 2fr 1fr; gap: 0.85rem; }
.code-row { grid-template-columns: 1fr 1fr; }

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
.card-head.solution h3::before { content: ''; }
.card-head .card-meta { font-size: 0.78rem; color: var(--text-muted); }
.card-head .card-meta strong { color: var(--text-strong); }
.muted { color: var(--text-muted); }

/* selector card */
.selector { padding: 0; }
.selector .card-head { gap: 0.5rem; }
.sort-toggle { display: flex; gap: 0.25rem; align-items: center; }
.sort-toggle .lbl { font-size: 0.72rem; color: var(--text-muted); margin-right: 0.2rem; }
.sort-toggle button {
  background: var(--bg-card); border: 1px solid var(--border-strong);
  color: var(--text); padding: 0.2rem 0.55rem; border-radius: 4px; font-size: 0.78rem;
}
.sort-toggle button.active { background: var(--accent); border-color: var(--accent); color: white; }
.student-select {
  width: calc(100% - 1.6rem);
  margin: 0.7rem 0.8rem 0.4rem;
  padding: 0.5rem 0.6rem;
  font-size: 0.92rem;
  font-family: inherit;
}
.hint { color: var(--text-muted); font-size: 0.75rem; padding: 0 0.85rem 0.7rem; margin: 0; }
.alert {
  margin: 0 0.85rem 0.85rem;
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
  font-size: 0.82rem;
}
.alert.warn { background: var(--warning-soft); color: #92400e; border-left: 3px solid var(--warning); }

/* summary card */
.summary-list { list-style: none; margin: 0; padding: 0.5rem 0; }
.summary-list li {
  display: flex; justify-content: space-between;
  padding: 0.35rem 0.9rem;
  font-size: 0.85rem;
  border-bottom: 1px dashed var(--border);
}
.summary-list li:last-child { border-bottom: none; }
.summary-list .qid { color: var(--text-muted); font-family: ui-monospace, monospace; }
.summary-list .qmax { color: var(--text-muted); }
.summary-list li.done .qval { color: var(--success); font-weight: 600; }
.summary-list li.total {
  border-top: 1px solid var(--border-strong);
  border-bottom: none;
  background: var(--bg-soft);
  margin-top: 0.3rem;
  padding: 0.5rem 0.9rem;
  font-weight: 600;
}
.summary-list li.total .qid { color: var(--text-strong); }
.summary-list li.total .qval strong { color: var(--accent); font-size: 1.05rem; }

/* questions */
.qbar {
  display: flex; flex-wrap: wrap; gap: 0.35rem;
  padding: 0.7rem 0.9rem 0.4rem;
}
.qchip {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.35rem 0.7rem;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  font-size: 0.85rem;
  color: var(--text);
}
.qchip:hover { background: var(--bg-soft); }
.qchip-id { font-family: ui-monospace, monospace; font-weight: 600; }
.qchip-pts { font-size: 0.72rem; color: var(--text-muted); }
.qchip.graded { border-color: var(--success); }
.qchip.graded .qchip-pts { color: var(--success); }
.qchip.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}
.qchip.active .qchip-pts { color: rgba(255,255,255,0.85); }
.qstatement {
  margin: 0.3rem 0.9rem 0.85rem;
  padding: 0.55rem 0.7rem;
  background: var(--accent-soft);
  border-left: 3px solid var(--accent);
  border-radius: 4px;
  font-size: 0.85rem;
  color: #1e3a5f;
}

/* grading */
.grading { padding: 0; }
.grading > * { margin: 0; }
.grade-row {
  display: flex; gap: 0.6rem; align-items: center;
  padding: 0.85rem 0.9rem 0.55rem;
}
.grade-input {
  display: flex; align-items: center; gap: 0.35rem;
  background: var(--bg-soft);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 0 0.5rem 0 0;
}
.grade-input input {
  width: 90px; padding: 0.45rem 0.55rem;
  font-size: 1.1rem; font-weight: 600;
  font-family: ui-monospace, monospace;
  border: none; background: transparent;
}
.grade-input input:focus { box-shadow: none; }
.grade-input .of { color: var(--text-muted); font-size: 0.9rem; }

.btn-warn { background: var(--warning); border-color: var(--warning); color: white; }

.quick-row {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0 0.9rem 0.6rem;
}
.quick-lbl { font-size: 0.75rem; color: var(--text-muted); margin-right: 0.4rem; }
.btn.quick {
  padding: 0.28rem 0.55rem; font-size: 0.78rem;
  background: var(--bg-soft);
}
.btn.quick:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

.comment {
  display: block;
  width: calc(100% - 1.8rem);
  margin: 0 0.9rem 0.85rem;
  padding: 0.5rem 0.6rem;
  font-size: 0.85rem;
  resize: vertical;
}

.suggest-result {
  margin: 0;
  padding: 0.7rem 0.9rem;
  border-top: 1px solid var(--border);
  background: var(--bg-soft);
}
.suggest-result header { display: flex; align-items: center; gap: 0.55rem; font-size: 0.92rem; }
.suggest-result .conf-pill {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-weight: 600;
}
.conf-pill.high { background: var(--success-soft); color: #065f46; }
.conf-pill.medium { background: var(--warning-soft); color: #92400e; }
.conf-pill.low { background: var(--danger-soft); color: #991b1b; }
.conf-pill.none { background: var(--border); color: var(--text-muted); }
.suggest-comment {
  margin: 0.5rem 0 0;
  padding: 0.6rem 0.7rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 0.83rem;
  color: var(--text);
  white-space: pre-wrap;
  font-family: inherit;
}

/* code panes */
.pane { padding: 0; }
.card-head.solution { background: #ebf5ff; border-bottom-color: #bfdbfe; }
.card-head.solution h3 { color: #1e3a8a; }
.card-head.student { background: #ecfdf5; border-bottom-color: #a7f3d0; }
.card-head.student h3 { color: #14532d; }
.btn-small { padding: 0.2rem 0.5rem; font-size: 0.75rem; }
.pane-body {
  max-height: 540px;
  overflow-y: auto;
  padding: 0.55rem;
  background: var(--bg-soft);
}

/* runner */
.runner { padding: 0; }
.code-in {
  display: block;
  width: calc(100% - 1.6rem);
  margin: 0.7rem 0.8rem 0.4rem;
  padding: 0.55rem 0.7rem;
  background: var(--code-bg);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
  resize: vertical;
}
.run-row {
  display: flex; gap: 0.5rem; align-items: center;
  padding: 0 0.8rem 0.7rem;
}
.run-row .stdin {
  flex: 1; padding: 0.4rem 0.55rem;
  font-size: 0.85rem;
}
.run-meta { font-size: 0.85rem; }
.run-meta.ok { color: var(--success); }
.run-meta.err { color: var(--danger); }
.run-out { padding: 0 0.8rem 0.85rem; }
.run-out .lbl {
  display: inline-block;
  font-size: 0.7rem; text-transform: uppercase;
  color: var(--text-muted); letter-spacing: 0.5px; margin-bottom: 0.2rem;
}
.run-out .lbl.err { color: var(--danger); }
.run-out pre {
  margin: 0; padding: 0.55rem 0.7rem;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-family: ui-monospace, monospace; font-size: 0.82rem;
  white-space: pre-wrap; word-break: break-word;
  max-height: 240px; overflow: auto;
}
.run-out pre.err { border-color: var(--danger); background: var(--danger-soft); color: #991b1b; }

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
@keyframes spin { to { transform: rotate(360deg); } }

/* toast */
.toast {
  position: fixed; bottom: 18px; right: 18px;
  padding: 0.6rem 0.95rem;
  border-radius: 6px;
  background: var(--success); color: white;
  z-index: 100; font-size: 0.85rem;
  box-shadow: 0 4px 14px rgba(0,0,0,0.15);
}
.toast.err { background: var(--danger); }
.toast-enter-from, .toast-leave-to { transform: translateX(120%); opacity: 0; }
.toast-enter-active, .toast-leave-active { transition: all 0.25s ease; }

@media (max-width: 1100px) {
  .row.split { grid-template-columns: 1fr; }
  .code-row { grid-template-columns: 1fr; }
}
</style>
