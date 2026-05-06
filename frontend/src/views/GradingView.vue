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

const showRunner = ref(false)
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
  const v = Math.round(((q.max_points || 0) * pct) * 100) / 100
  draft[qid].points = v
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
    if (res.points !== null) {
      draft[session.selectedQuestionId].points = res.points
      draft[session.selectedQuestionId].comment = res.comment
    }
  } catch (e) {
    showToast('err', e instanceof Error ? e.message : String(e))
  } finally {
    suggesting.value = false
  }
}

function openRunner() {
  runnerCode.value = studentCodeJoined.value
  runnerResult.value = null
  showRunner.value = true
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

function statusClass(s: { total_grade: number; has_error: boolean; invisible_count: number }) {
  if (s.has_error) return 'err'
  if (s.invisible_count > 0) return 'flagged'
  if (s.total_grade > 0) return 'graded'
  return 'pending'
}
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <div class="left">
        <button class="ghost" @click="router.push('/setup')">← Setup</button>
        <h1>Assignment Grading Tool</h1>
        <span class="meta">
          {{ session.students.length }} students · {{ gradedCount }} graded ·
          {{ session.questions.length }} questions / {{ totalMax }} pts
        </span>
      </div>
      <div class="right">
        <button class="ghost" @click="router.push('/plagiarism')">⚠ Plagiarism</button>
        <a class="primary" :href="exportGradesUrl()" download>Export CSV</a>
      </div>
    </header>

    <aside class="sidebar">
      <div class="sidebar-controls">
        <span class="label">Sort by</span>
        <button
          class="toggle" :class="{ active: session.sortOrder === 'name' }"
          @click="session.setSortOrder('name')"
        >Name</button>
        <button
          class="toggle" :class="{ active: session.sortOrder === 'number' }"
          @click="session.setSortOrder('number')"
        >Number</button>
      </div>
      <div class="nav-row">
        <button @click="session.navigate(-1).then(syncDraft)">‹ Prev</button>
        <span class="pos">
          {{ session.currentIndex + 1 || '—' }} / {{ session.students.length }}
        </span>
        <button @click="session.navigate(+1).then(syncDraft)">Next ›</button>
      </div>
      <ul>
        <li
          v-for="s in session.students"
          :key="s.id"
          :class="{ active: s.id === session.selectedStudentId, [statusClass(s)]: true }"
          @click="selectStudent(s.id)"
        >
          <div class="row1">
            <span class="dot" />
            <strong>{{ s.name }}</strong>
          </div>
          <div class="row2">
            <span class="num">#{{ s.id }}</span>
            <span class="grade">{{ s.total_grade.toFixed(1) }} / {{ totalMax }}</span>
          </div>
          <div v-if="s.invisible_count > 0" class="badge ai">⚠ {{ s.invisible_count }} unicode</div>
          <div v-if="s.has_error" class="err-msg">{{ s.error }}</div>
        </li>
      </ul>
    </aside>

    <main class="main">
      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="!session.studentDetail" class="placeholder">
        Select a student from the sidebar to start grading. Use ← / → to navigate.
      </div>

      <template v-else>
        <header class="student-head">
          <div>
            <h2>
              {{ session.studentDetail.info.name }}
              <span class="num">#{{ session.studentDetail.info.id }}</span>
            </h2>
            <span class="meta"><code>{{ session.studentDetail.info.filename }}</code></span>
          </div>
          <div class="total">
            <span class="label">Current grade</span>
            <strong>{{ totalCurrent.toFixed(1) }} / {{ totalMax }}</strong>
          </div>
        </header>

        <div v-if="session.studentDetail.invisible_findings.length" class="warn">
          ⚠ Detected <strong>{{ session.studentDetail.invisible_findings.length }}</strong>
          suspicious unicode characters in code (possible AI paste). E.g.
          <code>{{ session.studentDetail.invisible_findings[0].name }}</code>
          at line {{ session.studentDetail.invisible_findings[0].line }}.
        </div>

        <nav class="qbar">
          <button
            v-for="q in session.questions" :key="q.id"
            :class="{ active: q.id === session.selectedQuestionId }"
            @click="session.selectQuestion(q.id)"
          >
            {{ q.id }} <span class="qpts">({{ q.max_points }}pt)</span>
          </button>
        </nav>

        <div v-if="selectedQuestion" class="qstatement">
          {{ selectedQuestion.statement.slice(0, 280) }}{{ selectedQuestion.statement.length > 280 ? '…' : '' }}
        </div>

        <section class="compare">
          <div class="pane">
            <header><span>Solution</span></header>
            <div class="pane-body">
              <NotebookViewer
                :cells="solutionCellsForQuestion"
                placeholder="No solution cells for this question."
              />
            </div>
          </div>
          <div class="pane">
            <header><span>Student submission</span><button class="run-btn" @click="openRunner">▶ Run code</button></header>
            <div class="pane-body">
              <NotebookViewer
                :cells="studentCellsForQuestion"
                placeholder="No student cells for this question."
              />
            </div>
          </div>
        </section>
      </template>
    </main>

    <section class="grading">
      <h2>Grading</h2>
      <div v-if="!session.selectedStudentId" class="placeholder">No student selected.</div>
      <template v-else>
        <ul class="questions">
          <li
            v-for="q in session.questions" :key="q.id"
            :class="{ active: q.id === session.selectedQuestionId }"
            @click="session.selectQuestion(q.id)"
          >
            <div class="qhead">
              <strong>{{ q.label }}</strong>
              <span class="qmax">/ {{ q.max_points }}</span>
            </div>
            <div class="qrow">
              <input
                type="number" step="0.25" min="0" :max="q.max_points"
                v-model.number="draft[q.id].points" @blur="clamp(q.id)"
              />
              <button class="primary save" :disabled="saving[q.id]" @click.stop="save(q.id)">
                {{ saving[q.id] ? '…' : 'Save' }}
              </button>
            </div>
            <div class="quick">
              <button v-for="p in [0, 0.25, 0.5, 0.75, 1]" :key="p"
                @click.stop="quickGrade(q.id, p)">{{ p * 100 }}%</button>
            </div>
            <textarea
              v-model="draft[q.id].comment"
              placeholder="Comment (optional)"
              rows="2"
              @click.stop
            />
          </li>
        </ul>

        <div class="suggest-block">
          <button class="suggest" :disabled="suggesting || !session.selectedQuestionId" @click="onSuggest">
            {{ suggesting ? 'Thinking…' : '✨ Suggest grade for ' + (session.selectedQuestionId ?? '—') }}
          </button>
          <div v-if="lastSuggest" class="suggest-result" :class="lastSuggest.confidence">
            <strong>{{ lastSuggest.points }}</strong> / {{ lastSuggest.max_points }}
            · score <strong>{{ Math.round(lastSuggest.score * 100) }}%</strong>
            · confidence <strong>{{ lastSuggest.confidence }}</strong>
          </div>
        </div>
      </template>
    </section>

    <Transition name="toast">
      <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>
    </Transition>

    <Transition name="modal">
      <div v-if="showRunner" class="modal-bg" @click.self="showRunner = false">
        <div class="modal">
          <header>
            <h3>Run student code</h3>
            <button class="ghost" @click="showRunner = false">✕</button>
          </header>
          <div class="modal-body">
            <label class="label">Code</label>
            <textarea v-model="runnerCode" rows="14" class="code-in" />
            <label class="label">Stdin (optional)</label>
            <textarea v-model="runnerStdin" rows="3" />
            <div class="run-actions">
              <button class="primary" :disabled="runnerLoading" @click="onRun">
                {{ runnerLoading ? 'Running…' : '▶ Run' }}
              </button>
              <span v-if="runnerResult" class="meta">
                {{ runnerResult.duration_ms }}ms ·
                <span :class="runnerResult.success ? 'ok' : 'err'">
                  {{ runnerResult.success ? 'success' : 'error' }}
                </span>
              </span>
            </div>
            <div v-if="runnerResult" class="run-out">
              <div v-if="runnerResult.output">
                <span class="label">Output</span>
                <pre>{{ runnerResult.output }}</pre>
              </div>
              <div v-if="runnerResult.error">
                <span class="label err">Error</span>
                <pre class="err">{{ runnerResult.error }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 280px 1fr 340px;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    'topbar topbar topbar'
    'sidebar main grading';
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text);
}

/* Topbar */
.topbar {
  grid-area: topbar;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  background: var(--header-bg);
  border-bottom: 1px solid var(--border-strong);
}
.topbar .left, .topbar .right { display: flex; gap: 0.6rem; align-items: center; }
.topbar h1 { margin: 0; font-size: 1rem; color: var(--text-strong); }
.topbar .meta { font-size: 0.8rem; color: #cbd5e1; }

button.ghost {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border-strong);
  padding: 0.35rem 0.7rem;
  border-radius: 4px;
  font-size: 0.85rem;
}
button.ghost:hover { background: rgba(255,255,255,0.06); }

a.primary, button.primary {
  padding: 0.4rem 0.85rem;
  border-radius: 4px;
  background: var(--accent);
  color: white;
  border: none;
  font-size: 0.85rem;
  text-decoration: none;
}
a.primary:hover, button.primary:hover { background: var(--accent-hover); }
button:disabled { opacity: 0.5; cursor: not-allowed; }

/* Sidebar */
.sidebar {
  grid-area: sidebar;
  border-right: 1px solid var(--border);
  background: var(--bg-elevated);
  overflow-y: auto;
}
.sidebar-controls {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.6rem 0.75rem 0.4rem;
  font-size: 0.78rem;
}
.sidebar-controls .label { color: var(--text-muted); margin-right: 0.2rem; }
.toggle {
  background: var(--bg-panel);
  color: var(--text);
  border: 1px solid var(--border-strong);
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  font-size: 0.78rem;
}
.toggle.active { background: var(--accent); border-color: var(--accent); color: white; }

.nav-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.4rem 0.75rem 0.6rem;
  border-bottom: 1px solid var(--border);
}
.nav-row button {
  background: var(--bg-panel);
  color: var(--text);
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  padding: 0.25rem 0.55rem;
  font-size: 0.8rem;
}
.nav-row .pos { font-size: 0.8rem; color: var(--text-muted); font-family: ui-monospace, monospace; }

.sidebar ul { list-style: none; margin: 0; padding: 0; }
.sidebar li {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}
.sidebar li:hover { background: rgba(255,255,255,0.04); }
.sidebar li.active {
  background: rgba(52, 152, 219, 0.18);
  border-left: 3px solid var(--accent);
  padding-left: calc(0.75rem - 3px);
}
.row1 { display: flex; align-items: center; gap: 0.4rem; }
.row1 strong { font-size: 0.88rem; color: var(--text-strong); }
.row2 { display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-muted); margin-top: 2px; }
.num { font-family: ui-monospace, monospace; }
.grade { font-weight: 600; color: var(--text); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #555; }
.graded .dot { background: var(--success); }
.flagged .dot { background: var(--warning); }
.err .dot { background: var(--danger); }
.badge { font-size: 0.7rem; margin-top: 3px; padding: 2px 5px; border-radius: 3px; display: inline-block; }
.badge.ai { background: rgba(243, 156, 18, 0.2); color: #fbbf24; }
.err-msg { color: var(--danger); font-size: 0.72rem; margin-top: 3px; }

/* Main */
.main {
  grid-area: main;
  overflow-y: auto;
  padding: 1rem 1.25rem 2rem;
}
.error {
  color: var(--danger);
  background: rgba(231, 76, 60, 0.12);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
}
.placeholder { color: var(--text-muted); padding: 2rem; text-align: center; font-style: italic; }

.student-head {
  display: flex; justify-content: space-between; align-items: flex-end;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.8rem;
}
.student-head h2 { margin: 0; font-size: 1.15rem; color: var(--text-strong); }
.student-head h2 .num { font-size: 0.9rem; color: var(--text-muted); margin-left: 0.4rem; }
.student-head .meta { font-size: 0.82rem; color: var(--text-muted); }
.total { text-align: right; }
.total .label { display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.total strong { font-size: 1.4rem; color: var(--accent); }

.warn {
  background: rgba(243, 156, 18, 0.12);
  border-left: 3px solid var(--warning);
  padding: 0.55rem 0.75rem;
  border-radius: 4px;
  margin-bottom: 0.8rem;
  font-size: 0.85rem;
  color: #fbbf24;
}

.qbar {
  display: flex; flex-wrap: wrap; gap: 0.4rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.5rem;
}
.qbar button {
  background: var(--bg-panel);
  color: var(--text);
  border: 1px solid var(--border-strong);
  padding: 0.3rem 0.65rem;
  border-radius: 4px;
  font-size: 0.82rem;
  font-family: ui-monospace, monospace;
}
.qbar button.active { background: var(--accent); border-color: var(--accent); color: white; }
.qbar .qpts { font-size: 0.7rem; opacity: 0.8; }

.qstatement {
  font-size: 0.82rem;
  color: var(--text-muted);
  padding: 0.4rem 0.6rem;
  background: var(--bg-elevated);
  border-radius: 4px;
  margin-bottom: 0.6rem;
}

.compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
}
.pane {
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-elevated);
}
.pane > header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.4rem 0.7rem;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
}
.pane-body {
  max-height: 540px;
  overflow-y: auto;
  padding: 0.5rem;
}
.run-btn {
  background: var(--accent);
  color: white;
  border: none;
  padding: 0.2rem 0.55rem;
  font-size: 0.75rem;
  border-radius: 3px;
}

/* Grading panel */
.grading {
  grid-area: grading;
  border-left: 1px solid var(--border);
  background: var(--bg-elevated);
  overflow-y: auto;
  padding: 0;
}
.grading > h2 {
  margin: 0; padding: 0.7rem 0.85rem; font-size: 0.78rem;
  text-transform: uppercase; letter-spacing: 0.6px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  background: var(--bg-panel);
}
.questions { list-style: none; margin: 0; padding: 0; }
.questions li {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}
.questions li.active { background: rgba(52, 152, 219, 0.12); border-left: 3px solid var(--accent); padding-left: calc(0.75rem - 3px); }
.qhead { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-strong); }
.qmax { color: var(--text-muted); font-size: 0.78rem; }
.qrow { display: flex; gap: 0.4rem; align-items: center; margin: 0.35rem 0; }
.qrow input { flex: 1; padding: 0.28rem 0.5rem; font-family: ui-monospace, monospace; }
.save { padding: 0.3rem 0.7rem !important; font-size: 0.8rem !important; }
.quick { display: flex; gap: 0.2rem; margin-bottom: 0.3rem; }
.quick button {
  flex: 1; background: var(--bg-panel); color: var(--text);
  border: 1px solid var(--border-strong);
  border-radius: 3px;
  padding: 0.18rem 0; font-size: 0.72rem;
}
.quick button:hover { background: var(--accent); border-color: var(--accent); color: white; }
.questions textarea {
  width: 100%; padding: 0.3rem 0.5rem;
  font-size: 0.8rem; resize: vertical; min-height: 36px;
  font-family: inherit;
}

.suggest-block { padding: 0.7rem 0.75rem; border-top: 1px solid var(--border); background: var(--bg-panel); }
.suggest {
  width: 100%;
  background: var(--suggest); color: white;
  border: none; padding: 0.45rem;
  border-radius: 4px; font-size: 0.85rem; font-weight: 600;
}
.suggest:disabled { opacity: 0.6; }
.suggest-result {
  margin-top: 0.5rem; padding: 0.4rem 0.55rem;
  border-radius: 4px;
  font-size: 0.8rem;
  background: rgba(255,255,255,0.04);
  border-left: 3px solid var(--text-muted);
}
.suggest-result.high { border-left-color: var(--success); }
.suggest-result.medium { border-left-color: var(--warning); }
.suggest-result.low { border-left-color: var(--danger); }
.suggest-result.none { color: var(--text-muted); }

/* Toast */
.toast {
  position: fixed;
  bottom: 16px;
  right: 16px;
  padding: 0.6rem 0.9rem;
  border-radius: 4px;
  background: var(--success); color: white;
  z-index: 100; font-size: 0.85rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.toast.err { background: var(--danger); }
.toast-enter-from, .toast-leave-to { transform: translateX(120%); opacity: 0; }
.toast-enter-active, .toast-leave-active { transition: all 0.25s ease; }

/* Modal (Run code) */
.modal-bg {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 50;
}
.modal {
  background: var(--bg-elevated);
  width: min(800px, 92vw);
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
.modal-body { padding: 0.8rem; overflow-y: auto; }
.modal-body .label { display: block; font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem; margin-top: 0.4rem; }
.code-in {
  width: 100%; font-family: ui-monospace, monospace; font-size: 0.85rem;
  background: var(--code-bg); color: var(--text);
}
.modal-body textarea { width: 100%; padding: 0.4rem 0.55rem; }
.run-actions { display: flex; align-items: center; gap: 0.7rem; margin-top: 0.6rem; }
.run-actions .meta { color: var(--text-muted); font-size: 0.82rem; }
.run-actions .ok { color: var(--success); }
.run-actions .err { color: var(--danger); }
.run-out { margin-top: 0.7rem; }
.run-out pre {
  margin: 0; padding: 0.5rem 0.7rem;
  background: var(--code-bg); border-radius: 4px;
  font-family: ui-monospace, monospace; font-size: 0.82rem;
  white-space: pre-wrap; word-break: break-word;
  color: var(--text);
}
.run-out pre.err { color: #fca5a5; border-left: 3px solid var(--danger); }
.run-out .label.err { color: #fca5a5; }

.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.18s; }

@media (max-width: 1200px) {
  .layout { grid-template-columns: 240px 1fr 300px; }
  .compare { grid-template-columns: 1fr; }
}
</style>
