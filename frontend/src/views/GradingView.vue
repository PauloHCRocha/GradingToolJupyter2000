<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { useAutogradeStore } from '../stores/autograde'
import type { ReviewStatus } from '../stores/autograde'
import { downloadGradesCsv, suggestGrade } from '../api/client'
import type { CellOut, SuggestResponse } from '../api/client'
import { useRunConsole } from '../runtime/runConsole'
import NotebookViewer from '../components/NotebookViewer.vue'
import CodeEditor from '../components/CodeEditor.vue'
import RunConsole from '../components/RunConsole.vue'
import AppHeader from '../components/AppHeader.vue'

const session = useSessionStore()
const autograde = useAutogradeStore()
const router = useRouter()
const route = useRoute()

const draft = reactive<Record<string, { points: number; comment: string }>>({})
const saving = ref<Record<string, boolean>>({})
const suggesting = ref(false)
const error = ref<string | null>(null)
const toast = ref<{ kind: 'ok' | 'err'; text: string } | null>(null)

const runnerTimeout = ref(10)
const studentConsole = useRunConsole()
const solutionConsole = useRunConsole()

// The runner edits the teacher's working copy of the whole submission. It
// starts as the original and is kept per student, so switching students or
// questions never loses edits — and never changes the submission itself.
const originalSource = computed(() => session.studentDetail?.source ?? '')
const workingCopyEdited = computed(
  () => !!session.selectedStudentId && session.selectedStudentId in session.workingCopies,
)
const workingCopy = computed({
  get: () =>
    workingCopyEdited.value ? session.workingCopies[session.selectedStudentId!] : originalSource.value,
  set: (code: string) => {
    const id = session.selectedStudentId
    if (!id) return
    if (code === originalSource.value) session.resetWorkingCopy(id)
    else session.setWorkingCopy(id, code)
  },
})
const solutionSource = computed(() => session.solutionDetail?.source ?? '')

// Both consoles finished with the same answers typed in → compare what
// they printed (input() prompts ignored: their wording often differs).
const comparison = computed<'same' | 'different' | 'other-inputs' | null>(() => {
  const a = studentConsole.state
  const b = solutionConsole.state
  if (a.status !== 'done' || b.status !== 'done') return null
  if (a.inputs.join('\n') !== b.inputs.join('\n')) return 'other-inputs'
  return studentConsole.printed.value === solutionConsole.printed.value ? 'same' : 'different'
})

// "This question" shows each side's window; "Whole file" shows everything.
const viewScope = ref<'question' | 'file'>('question')

const lastSuggest = ref<SuggestResponse | null>(null)

// Splitter between Solution and Student panes (percentage of the left pane).
const splitRatio = ref(50)
const splitDragging = ref(false)

function startSplitDrag(e: MouseEvent) {
  e.preventDefault()
  const handle = e.currentTarget as HTMLElement
  const row = handle.parentElement
  if (!row) return
  const rect = row.getBoundingClientRect()
  splitDragging.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  function onMove(ev: MouseEvent) {
    const x = ev.clientX - rect.left
    const pct = Math.max(20, Math.min(80, (x / rect.width) * 100))
    splitRatio.value = pct
  }
  function onUp() {
    splitDragging.value = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

// Totals and chips reflect what the teacher actually wants to grade — all
// of these use enabledQuestions, so deselected ones disappear from the UI
// while their saved grades stay intact in case the teacher re-enables them.
const totalMax = computed(() =>
  session.enabledQuestions.reduce((acc, q) => acc + (Number(q.max_points) || 0), 0),
)
const totalCurrent = computed(() => {
  const enabledIds = new Set(session.enabledQuestions.map((q) => q.id))
  return Object.values(session.studentGrades).reduce(
    (acc, g) => (g && enabledIds.has(g.question_id) ? acc + (g.points ?? 0) : acc),
    0,
  )
})
const gradedCount = computed(() => session.students.filter((s) => s.total_grade > 0).length)
const studentPosition = computed(() =>
  session.currentIndex >= 0 ? `${session.currentIndex + 1} of ${session.students.length}` : '',
)

const selectedQuestion = computed(() =>
  session.enabledQuestions.find((q) => q.id === session.selectedQuestionId) ?? null,
)

const selectedQuestionMax = computed(() =>
  selectedQuestion.value ? Number(selectedQuestion.value.max_points) || 0 : 0,
)

const solutionCellsForQuestion = computed<CellOut[]>(() => {
  const sd = session.solutionDetail
  const qid = session.selectedQuestionId
  if (!sd) return []
  if (!qid || viewScope.value === 'file') return sd.cells
  const indices = sd.question_windows[qid] ?? []
  return indices.map((i) => sd.cells[i]).filter(Boolean)
})

// The student's file has no header for this question (renamed, deleted,
// different template): show the whole file rather than an empty pane.
const studentWindowMissing = computed(() => {
  const sd = session.studentDetail
  const qid = session.selectedQuestionId
  return !!sd && !!qid && !(sd.question_windows[qid]?.length)
})

const studentCellsForQuestion = computed<CellOut[]>(() => {
  const sd = session.studentDetail
  const qid = session.selectedQuestionId
  if (!sd) return []
  if (!qid || viewScope.value === 'file' || studentWindowMissing.value) return sd.cells
  const indices = sd.question_windows[qid] ?? []
  return indices.map((i) => sd.cells[i]).filter(Boolean)
})

watch(
  () => session.studentDetail?.info.id,
  () => {
    studentConsole.clear()
  },
)

// --- Claude auto-grade review -------------------------------------------
const aiStudent = computed(() =>
  session.selectedStudentId ? (autograde.results[session.selectedStudentId] ?? null) : null,
)
const aiResult = computed(() => autograde.resultFor(session.selectedStudentId, session.selectedQuestionId))
const aiStale = computed(() => !!aiStudent.value && aiStudent.value.rubricKey !== autograde.rubricKey)
const reviewLabel: Record<ReviewStatus, string> = {
  pending: 'not reviewed',
  accepted: 'accepted',
  overridden: 'changed by you',
  rejected: 'rejected',
}

function applyAi() {
  const qid = session.selectedQuestionId
  if (!aiResult.value || !qid || !draft[qid]) return
  draft[qid].points = aiResult.value.points
  draft[qid].comment = aiResult.value.feedback
}

async function acceptAi() {
  const sid = session.selectedStudentId
  const qid = session.selectedQuestionId
  if (!sid || !qid) return
  try {
    await autograde.accept(sid, qid)
    syncDraft()
    showToast('ok', `Accepted Claude's grade for ${qid}`)
  } catch (e) {
    showToast('err', e instanceof Error ? e.message : String(e))
  }
}

function rejectAi() {
  if (session.selectedStudentId && session.selectedQuestionId) {
    autograde.reject(session.selectedStudentId, session.selectedQuestionId)
  }
}

onMounted(async () => {
  if (!session.enabledQuestions.length || !session.students.length) {
    router.replace('/setup')
    return
  }
  // Cover the "user disabled the previously selected question and came back
  // to grading" case — store helper picks first enabled.
  session.ensureValidSelectedQuestion()
  await session.ensureSolutionDetail()
  // Deep link from the auto-grade review table: /grading?student=…&q=…
  const wantQ = typeof route.query.q === 'string' ? route.query.q : null
  const wantStudent = typeof route.query.student === 'string' ? route.query.student : null
  if (wantQ && session.enabledQuestions.some((q) => q.id === wantQ)) session.selectQuestion(wantQ)
  if (wantStudent && session.students.some((s) => s.id === wantStudent && !s.has_error)) {
    await selectStudent(wantStudent)
  } else if (!session.selectedStudentId) {
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

// Setup may still be finishing (a new solution or zip) when this view
// opens: reload whatever went missing instead of leaving the panes empty.
watch(
  () => session.solution && !session.solutionDetail,
  (missing) => {
    if (missing) void session.ensureSolutionDetail()
  },
)
watch(
  () => !session.selectedStudentId && session.students.some((s) => !s.has_error),
  (none) => {
    if (none) void selectStudent(session.students.find((s) => !s.has_error)!.id)
  },
)

async function retryLoad() {
  error.value = null
  await session.ensureSolutionDetail()
  if (session.selectedStudentId) await selectStudent(session.selectedStudentId)
}

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

// Run once synchronously so the template never reads draft[id] before it's
// initialized (e.g. when returning from another route with a student already
// selected from a prior visit).
syncDraft()

watch(() => session.selectedStudentId, syncDraft)
watch(() => session.questions.map((q) => q.id).join(','), syncDraft)

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
    const points = Number(draft[qid].points) || 0
    await session.saveGrade(qid, points, draft[qid].comment)
    if (session.selectedStudentId) autograde.noteManualGrade(session.selectedStudentId, qid, points)
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

function runStudent(inputs: string[] = [], seed?: number) {
  void studentConsole.start(workingCopy.value, runnerTimeout.value * 1000, inputs, seed)
}

function runSolution(inputs: string[] = [], seed?: number) {
  void solutionConsole.start(solutionSource.value, runnerTimeout.value * 1000, inputs, seed)
}

function resetWorkingCopy() {
  if (session.selectedStudentId) session.resetWorkingCopy(session.selectedStudentId)
}

function gradeFor(qid: string): number | null {
  const g = session.studentGrades[qid]
  return g ? Number(g.points) : null
}
</script>

<template>
  <div class="page">
    <AppHeader :subtitle="`${session.students.length} students · ${gradedCount} graded · ${session.enabledQuestions.length} questions · ${totalMax} pts`">
      <template #actions>
        <button class="btn btn-primary" @click="downloadGradesCsv">Export CSV</button>
      </template>
    </AppHeader>

    <nav class="student-bar" aria-label="Student">
      <button class="btn nav-btn" title="Previous student (←)" @click="session.navigate(-1).then(syncDraft)">
        <kbd>←</kbd> Previous
      </button>
      <div class="student-main">
        <template v-if="session.studentDetail">
          <span class="cs-name">{{ session.studentDetail.info.name }}</span>
          <span class="cs-meta">
            #{{ session.studentDetail.info.id }} · <code>{{ session.studentDetail.info.filename }}</code>
            <template v-if="studentPosition"> · {{ studentPosition }}</template>
          </span>
        </template>
        <span v-else class="cs-meta muted">No student selected</span>
      </div>
      <div class="student-tools">
        <div class="sort-toggle" role="group" aria-label="Sort students by">
          <button :class="{ active: session.sortOrder === 'name' }" @click="session.setSortOrder('name')">Name</button>
          <button :class="{ active: session.sortOrder === 'number' }" @click="session.setSortOrder('number')">Number</button>
        </div>
        <select class="student-select" aria-label="Jump to student" :value="session.selectedStudentId" @change="onStudentChange">
          <option value="" disabled>— pick a student —</option>
          <option v-for="s in session.students" :key="s.id" :value="s.id" :disabled="s.has_error">
            {{ s.name }} (#{{ s.id }})
            <template v-if="s.total_grade > 0">— {{ s.total_grade.toFixed(1) }}/{{ totalMax }}</template>
            <template v-if="s.invisible_count">⚠ {{ s.invisible_count }}</template>
            <template v-if="s.has_error">⚠ error</template>
          </option>
        </select>
        <span class="total-badge tnum" title="This student's total">
          <span class="lbl">Total</span>
          <strong>{{ totalCurrent.toFixed(1) }}</strong> / {{ totalMax }}
        </span>
      </div>
      <button class="btn nav-btn" title="Next student (→)" @click="session.navigate(+1).then(syncDraft)">
        Next <kbd>→</kbd>
      </button>
    </nav>

    <main class="body">
      <div v-if="session.studentDetail?.invisible_findings.length" class="alert warn">
        ⚠ <strong>{{ session.studentDetail.invisible_findings.length }}</strong>
        suspicious unicode character(s) in this submission's code (possible AI paste).
      </div>

      <section class="card questions">
        <div class="qbar">
          <button v-for="q in session.enabledQuestions" :key="q.id"
                  class="qchip tnum"
                  :class="{ active: q.id === session.selectedQuestionId, graded: gradeFor(q.id) !== null }"
                  @click="session.selectQuestion(q.id)">
            <span class="qchip-id">{{ q.id }}</span>
            <span class="qchip-pts">
              <template v-if="gradeFor(q.id) !== null">{{ gradeFor(q.id) }}</template><template v-else>–</template>/{{ q.max_points }}
            </span>
          </button>
          <p v-if="!session.enabledQuestions.length" class="hint">
            No questions selected for grading. Re-enable some in Setup.
          </p>
        </div>
        <p v-if="selectedQuestion" class="qstatement">
          {{ selectedQuestion.statement.slice(0, 360) }}{{ selectedQuestion.statement.length > 360 ? '…' : '' }}
        </p>
      </section>

      <section v-if="selectedQuestion && session.selectedStudentId && draft[selectedQuestion.id]" class="card grading">
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
            {{ suggesting ? 'Analysing…' : 'Suggest grade' }}
          </button>
          <button class="btn btn-primary" :disabled="saving[selectedQuestion.id]"
                  @click="save(selectedQuestion.id)">
            {{ saving[selectedQuestion.id] ? 'Saving…' : 'Save grade' }}
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
          <span class="suggest-note">Points and comment filled in above — review them and save.</span>
        </div>

        <div v-if="aiResult" class="ai-result">
          <header>
            <span class="ai-tag">Claude</span>
            <strong>{{ aiResult.points }} / {{ aiResult.maxPoints }}</strong>
            <span class="conf-pill" :class="aiResult.confidence">{{ aiResult.confidence }}</span>
            <span class="review-pill" :class="aiResult.review">{{ reviewLabel[aiResult.review] }}</span>
            <span v-if="aiStale" class="stale" title="The rubric was edited after this submission was graded">
              rubric changed since
            </span>
            <span class="grow" />
            <button class="btn btn-small" title="Copy points and feedback into the form above to edit them"
                    @click="applyAi">Edit before saving</button>
            <button class="btn btn-small" @click="rejectAi">Reject</button>
            <button class="btn btn-small btn-primary" @click="acceptAi">Accept</button>
          </header>
          <ul class="ai-criteria">
            <li v-for="c in aiResult.criteria" :key="c.id">
              <span class="ai-pts" :class="{ full: c.points === c.max, zero: c.points === 0 }">
                {{ c.points }}/{{ c.max }}
              </span>
              <div>
                <div class="ai-desc">{{ c.description }}</div>
                <div class="ai-why">{{ c.justification }}</div>
              </div>
            </li>
          </ul>
          <p v-if="aiResult.feedback" class="ai-feedback"><strong>Feedback:</strong> {{ aiResult.feedback }}</p>
          <p v-if="aiStudent?.flags.length" class="ai-flags">⚠ {{ aiStudent.flags.join(' · ') }}</p>
        </div>
        <div v-else-if="aiStudent?.status === 'error'" class="ai-result ai-error">
          Claude could not grade this submission: {{ aiStudent.error }}
        </div>
      </section>

      <div v-if="error || session.solutionError" class="alert err load-error" role="alert">
        <span>
          Couldn't load the code:
          <code>{{ error || session.solutionError }}</code>
        </span>
        <button class="btn btn-small" @click="retryLoad">Try again</button>
      </div>

      <div v-if="session.selectedStudentId" class="scope-row">
        <span class="scope-lbl">Show</span>
        <div class="sort-toggle" role="group" aria-label="Show">
          <button :class="{ active: viewScope === 'question' }" @click="viewScope = 'question'">This question</button>
          <button :class="{ active: viewScope === 'file' }" @click="viewScope = 'file'">Whole file</button>
        </div>
        <span v-if="studentWindowMissing && viewScope === 'question'" class="scope-note">
          No “{{ session.selectedQuestionId }}” header found in this submission — showing the student's whole file.
        </span>
      </div>

      <section
        v-if="session.selectedStudentId"
        class="code-row"
        :style="{ '--split-left': splitRatio + '%' }"
      >
        <article class="card pane left">
          <header class="card-head solution"><h3><span class="side-dot" />Solution</h3></header>
          <div class="pane-body">
            <NotebookViewer :cells="solutionCellsForQuestion"
                            placeholder="No solution cells for this question." />
          </div>
        </article>
        <div
          class="splitter"
          :class="{ dragging: splitDragging }"
          role="separator"
          aria-label="Resize panes"
          aria-orientation="vertical"
          title="Drag to resize"
          @mousedown="startSplitDrag"
          @dblclick="splitRatio = 50"
        />
        <article class="card pane right">
          <header class="card-head student">
            <h3><span class="side-dot" />Student submission</h3>
            <span class="card-meta">original</span>
          </header>
          <div class="pane-body">
            <NotebookViewer :cells="studentCellsForQuestion"
                            placeholder="No student cells for this question." />
          </div>
        </article>
      </section>

      <section v-if="session.selectedStudentId" class="card runner">
        <header class="card-head">
          <h3>
            Run code · your working copy
            <span v-if="workingCopyEdited" class="edited-pill">edited</span>
          </h3>
          <span class="card-meta muted">
            Edits stay here and never change the submission. Runs in a separate in-browser Python.
          </span>
        </header>
        <div class="runner-editor">
          <CodeEditor
            v-model="workingCopy"
            :rows="14"
            placeholder="The student's code appears here."
          />
        </div>
        <div class="run-row">
          <button class="btn" :disabled="!workingCopyEdited" @click="resetWorkingCopy">Reset to original</button>
          <span class="grow" />
          <label class="timeout">
            Stop a run after
            <select v-model.number="runnerTimeout">
              <option :value="5">5 s</option>
              <option :value="10">10 s</option>
              <option :value="30">30 s</option>
              <option :value="60">60 s</option>
            </select>
          </label>
        </div>
        <div class="consoles">
          <RunConsole :run="studentConsole" title="Student" variant="student">
            <template #actions>
              <button class="btn btn-small btn-primary" @click="runStudent()">▶ Run</button>
            </template>
            <template #inputs-actions>
              <button v-if="solutionSource" class="btn btn-small"
                      @click="runSolution(studentConsole.state.inputs, studentConsole.state.seed)">
                Run solution with these →
              </button>
            </template>
          </RunConsole>
          <RunConsole :run="solutionConsole" title="Solution" variant="solution">
            <template #actions>
              <button class="btn btn-small" :disabled="!solutionSource" @click="runSolution()">▶ Run</button>
            </template>
            <template #inputs-actions>
              <button class="btn btn-small"
                      @click="runStudent(solutionConsole.state.inputs, solutionConsole.state.seed)">
                ← Run student with these
              </button>
            </template>
          </RunConsole>
        </div>
        <p v-if="comparison" class="compare" :class="comparison">
          <template v-if="comparison === 'same'">✓ Same output as the solution for these inputs (prompts ignored)</template>
          <template v-else-if="comparison === 'different'">≠ The output differs from the solution for these inputs</template>
          <template v-else>The two runs used different inputs — use “Run … with these” to compare them.</template>
        </p>
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


/* ---- Student bar: who is being graded, always in view ---- */
.student-bar {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.55rem 1.25rem;
  background: color-mix(in srgb, var(--bg-card) 92%, transparent);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}
.nav-btn { display: inline-flex; align-items: center; gap: 0.4rem; }
.nav-btn kbd { font-size: 0.72rem; padding: 0 5px; }
.student-main { flex: 1; min-width: 180px; display: flex; flex-direction: column; line-height: 1.3; }
.cs-name { font-weight: 650; color: var(--text-strong); font-size: 1.05rem; letter-spacing: -0.01em; }
.cs-meta { font-size: 0.78rem; color: var(--text-muted); }
.cs-meta code { background: var(--code-bg); padding: 1px 5px; border-radius: 4px; border: 1px solid var(--code-border); }
.cs-meta.muted { font-style: italic; }
.student-tools { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.total-badge {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3rem;
  padding: 0.3rem 0.7rem;
  border-radius: 8px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-bd);
  color: var(--accent-tx);
  font-size: 0.85rem;
  white-space: nowrap;
}
.total-badge .lbl { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }
.total-badge strong { font-size: 1.05rem; }

/* ---- Body ---- */
.body {
  max-width: 1500px;
  margin: 0 auto;
  padding: 1rem 1.25rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

/* Code-row uses flex with a draggable splitter so the user can resize the
   solution / student panes by dragging the bar between them (double-click to
   reset to 50/50). */
.code-row {
  display: flex;
  align-items: stretch;
  gap: 0;
}
.code-row .pane.left {
  flex: 0 0 calc(var(--split-left, 50%) - 5px);
  min-width: 0;
}
.code-row .pane.right {
  flex: 1 1 auto;
  min-width: 0;
}
.splitter {
  flex: 0 0 10px;
  align-self: stretch;
  cursor: col-resize;
  position: relative;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}
.splitter::before {
  content: '';
  width: 3px;
  height: 44px;
  background: var(--border-strong);
  border-radius: 2px;
  transition: background 0.1s, height 0.1s;
}
.splitter:hover::before {
  background: var(--accent);
  height: 64px;
}
.splitter.dragging::before {
  background: var(--accent);
  height: 100%;
  width: 2px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
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

.sort-toggle {
  display: inline-flex;
  padding: 2px;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  background: var(--bg-soft);
}
.sort-toggle button {
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 0.22rem 0.6rem;
  border-radius: 5px;
  font-size: 0.78rem;
}
.sort-toggle button:hover { color: var(--text); }
.sort-toggle button.active { background: var(--bg-card); color: var(--text-strong); font-weight: 600; box-shadow: var(--shadow-sm); }
.student-select {
  max-width: 280px;
  padding: 0.4rem 0.55rem;
  font-size: 0.85rem;
}
.hint { color: var(--text-muted); font-size: 0.75rem; padding: 0 0.85rem 0.7rem; margin: 0; }
.alert {
  margin: 0 0.85rem 0.85rem;
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
  font-size: 0.82rem;
}
.alert.warn { background: var(--warning-soft); color: var(--warning-tx); border-left: 3px solid var(--warning); }
.alert.err { background: var(--danger-soft); color: var(--danger-tx); border-left: 3px solid var(--danger); }
.load-error { margin: 0; display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.load-error code { font-size: 0.8rem; }

/* questions */
.qbar {
  display: flex; flex-wrap: wrap; gap: 0.4rem;
  padding: 0.75rem 0.9rem 0.45rem;
}
.qchip {
  display: inline-flex; align-items: baseline; gap: 0.45rem;
  padding: 0.4rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  font-size: 0.86rem;
  color: var(--text);
  transition: background 0.12s, border-color 0.12s, box-shadow 0.12s;
}
.qchip:hover { background: var(--bg-soft); border-color: var(--accent); }
.qchip-id { font-family: ui-monospace, monospace; font-weight: 700; }
.qchip-pts { font-size: 0.76rem; color: var(--text-muted); }
.qchip.graded { border-color: var(--success-bd); background: var(--success-soft); }
.qchip.graded .qchip-pts { color: var(--success-tx); font-weight: 600; }
.qchip.active {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}
.qchip.active .qchip-pts { color: rgba(255,255,255,0.85); }
.qstatement {
  margin: 0.25rem 0.9rem 0.85rem;
  padding: 0.6rem 0.8rem;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  font-size: 0.87rem;
  line-height: 1.55;
  color: var(--text);
  white-space: pre-wrap;
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
.suggest-result .conf-pill,
.ai-result .conf-pill {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-weight: 600;
}
.conf-pill.high { background: var(--success-soft); color: var(--success-tx); }
.conf-pill.medium { background: var(--warning-soft); color: var(--warning-tx); }
.conf-pill.low { background: var(--danger-soft); color: var(--danger-tx); }
.conf-pill.none { background: var(--border); color: var(--text-muted); }
.suggest-note { font-size: 0.8rem; color: var(--text-muted); margin-left: auto; }

/* Claude result */
.ai-result {
  padding: 0.7rem 0.9rem;
  border-top: 1px solid var(--border);
  background: var(--ai-soft);
}
.ai-result header { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.92rem; }
.ai-result .grow { flex: 1; }
.ai-tag {
  padding: 1px 8px; border-radius: 999px;
  background: var(--ai); color: white;
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.3px;
}
.review-pill {
  padding: 1px 8px; border-radius: 999px; font-size: 0.7rem; font-weight: 600;
  background: var(--border); color: var(--text-muted);
}
.review-pill.accepted { background: var(--success-soft); color: var(--success-tx); }
.review-pill.overridden { background: var(--accent-soft); color: var(--accent-tx); }
.review-pill.rejected { background: var(--danger-soft); color: var(--danger-tx); }
.stale { font-size: 0.75rem; color: var(--warning-tx); }
.ai-criteria { list-style: none; margin: 0.55rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 0.35rem; }
.ai-criteria li {
  display: grid; grid-template-columns: 4.2rem 1fr; gap: 0.5rem;
  padding: 0.45rem 0.6rem;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px;
  font-size: 0.83rem;
}
.ai-pts { font-family: ui-monospace, monospace; font-weight: 700; color: var(--warning-tx); }
.ai-pts.full { color: var(--success); }
.ai-pts.zero { color: var(--danger); }
.ai-desc { color: var(--text-strong); font-weight: 500; }
.ai-why { color: var(--text-muted); margin-top: 0.15rem; }
.ai-feedback { margin: 0.55rem 0 0; font-size: 0.85rem; }
.ai-flags { margin: 0.4rem 0 0; font-size: 0.82rem; color: var(--danger-tx); }
.ai-error { color: var(--danger-tx); font-size: 0.85rem; }

.scope-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: -0.35rem; }
.scope-lbl { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.scope-note { font-size: 0.8rem; color: var(--warning-tx); }

/* code panes */
.pane { padding: 0; }
.card-head.solution { background: var(--solution-bg); border-bottom-color: var(--solution-bd); }
.card-head.solution h3 { color: var(--solution-tx); display: inline-flex; align-items: center; gap: 0.5rem; }
.card-head.student { background: var(--student-bg); border-bottom-color: var(--student-bd); }
.card-head.student h3 { color: var(--student-tx); display: inline-flex; align-items: center; gap: 0.5rem; }
.card-head .side-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.7;
}
.btn-small { padding: 0.2rem 0.5rem; font-size: 0.75rem; }
.pane-body {
  max-height: 540px;
  overflow-y: auto;
  padding: 0.55rem;
  background: var(--bg-soft);
}

/* runner */
.runner { padding: 0; }
.runner-editor {
  margin: 0.7rem 0.8rem 0.4rem;
}
.run-row {
  display: flex; gap: 0.5rem; align-items: center;
  padding: 0 0.8rem 0.7rem;
}
.run-row .grow { flex: 1; }
.run-row .timeout { font-size: 0.8rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.35rem; }
.run-row .timeout select { padding: 0.3rem 0.4rem; font-size: 0.82rem; }
.edited-pill {
  margin-left: 0.4rem;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
  background: var(--warning-soft);
  color: var(--warning-tx);
  border: 1px solid var(--warning-bd);
}
.consoles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 0.6rem;
  padding: 0 0.8rem 0.8rem;
}
.compare { margin: 0 0.8rem 0.85rem; font-size: 0.85rem; font-weight: 600; }
.compare.same { color: var(--success); }
.compare.different { color: var(--warning); }
.compare.other-inputs { color: var(--text-muted); font-weight: 400; }

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
  .code-row { flex-direction: column; }
  .code-row .pane.left { flex: 1 1 auto; }
  .splitter { display: none; }
}
</style>
