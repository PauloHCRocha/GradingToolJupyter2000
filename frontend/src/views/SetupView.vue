<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { analyzeSolution, uploadSubmissionFiles, uploadSubmissions } from '../api/client'
import type { SubmissionsUploadResult } from '../api/client'
import { useSessionStore } from '../stores/session'
import PointsInput from '../components/PointsInput.vue'
import FileDrop from '../components/FileDrop.vue'
import AppHeader from '../components/AppHeader.vue'

const session = useSessionStore()
const router = useRouter()

const loadingSolution = ref<string | null>(null)
const loadingSubmissions = ref<string | null>(null)
const submissionsName = ref<string | null>(null)
// Students dropped before the solution: loaded as soon as the solution is in.
interface StudentsJob {
  label: string
  load: () => Promise<SubmissionsUploadResult>
}
const pendingStudents = shallowRef<StudentsJob | null>(null)
const continuing = ref(false)
const errorSolution = ref<string | null>(null)
const errorSubmissions = ref<string | null>(null)
// Page-level hint when a drop was ambiguous.
const notice = ref<string | null>(null)

// Totals reflect what will *actually* be graded (enabled questions only) so
// the "X points total" pill matches what students see at grading time.
const totalMax = computed(() =>
  session.enabledQuestions.reduce((acc, q) => acc + (Number(q.max_points) || 0), 0),
)
const enabledCount = computed(() => session.enabledQuestions.length)
const allEnabled = computed(
  () => session.questions.length > 0 && session.questions.every((q) => q.enabled),
)
const noneEnabled = computed(
  () => session.questions.length > 0 && session.questions.every((q) => !q.enabled),
)

// Nothing is still being read: going to grading mid-way would show stale
// or missing code.
const busy = computed(() => !!loadingSolution.value || !!loadingSubmissions.value || !!pendingStudents.value)
const canContinue = computed(
  () => !busy.value && session.enabledQuestions.length > 0 && session.students.length > 0,
)
const hasGrades = () => session.students.some((s) => s.total_grade > 0)

// --- what each drop zone shows ---------------------------------------------
const solutionZone = computed(() => {
  if (loadingSolution.value) return { status: 'busy' as const, title: `Analyzing ${loadingSolution.value}…`, detail: 'Detecting questions and points' }
  if (errorSolution.value) return { status: 'error' as const, title: "Couldn't use that file", detail: errorSolution.value, removeLabel: 'Dismiss' }
  if (session.solution) {
    const n = session.questions.length
    return {
      status: 'done' as const,
      title: session.solution.filename,
      detail: `${n} question${n === 1 ? '' : 's'} · ${totalMax.value} points — drop another file to replace it`,
      removeLabel: 'Remove',
    }
  }
  return { status: 'idle' as const, title: 'Drop the solution file here', detail: '.py or .ipynb — or click to choose' }
})

const submissionsZone = computed(() => {
  if (loadingSubmissions.value) return { status: 'busy' as const, title: `Reading ${loadingSubmissions.value}…`, detail: 'Matching each submission to the questions' }
  if (pendingStudents.value) return { status: 'pending' as const, title: pendingStudents.value.label, detail: 'Waiting for the solution file — loads as soon as the solution is in', removeLabel: 'Cancel' }
  if (errorSubmissions.value) return { status: 'error' as const, title: "Couldn't use that file", detail: errorSubmissions.value, removeLabel: 'Dismiss' }
  if (session.students.length) {
    const n = session.students.length
    return {
      status: 'done' as const,
      title: submissionsName.value ?? 'Submissions',
      detail: `${n} student${n === 1 ? '' : 's'} loaded — drop again to replace them`,
      removeLabel: 'Remove',
    }
  }
  return {
    status: 'idle' as const,
    title: "Drop the students' files here",
    detail: 'A .zip (e.g. from Moodle), or the .py / .ipynb files themselves — or click to choose',
  }
})

// --- handling files --------------------------------------------------------
const isZip = (f: File) => /\.zip$/i.test(f.name)
const isCode = (f: File) => /\.(py|ipynb)$/i.test(f.name)
const fromZip = (f: File): StudentsJob => ({ label: f.name, load: () => uploadSubmissions(f) })
const fromFiles = (fs: File[]): StudentsJob => ({
  label: fs.length === 1 ? fs[0].name : `${fs.length} student files`,
  load: () => uploadSubmissionFiles(fs),
})

/** Box 1 takes the solution, box 2 the students' work (a zip or loose
 *  files). Dropped elsewhere on the page, a .zip is the students and a
 *  single .py/.ipynb the solution — so both can go in one drop. */
async function handleFiles(files: File[], zone?: 'solution' | 'students') {
  dragging.value = false
  dragDepth = 0
  notice.value = null
  const zips = files.filter(isZip)
  const code = files.filter(isCode)
  if (!zips.length && !code.length) {
    const msg = `“${files[0].name}” isn't a .py, .ipynb or .zip file.`
    if (zone === 'students') errorSubmissions.value = msg
    else errorSolution.value = msg
    return
  }

  let solution: File | undefined
  let students: StudentsJob | null = zips.length ? fromZip(zips[0]) : null
  if (zone === 'students') {
    students ??= fromFiles(code)
  } else if (zone === 'solution' || code.length === 1) {
    solution = code[0]
    if (code.length > 1) notice.value = `Only one solution file is used (${code[0].name}). Drop the students' files on box 2.`
  } else if (code.length > 1) {
    notice.value = "Several .py / .ipynb files: drop the solution on box 1 and the students' files on box 2."
  }

  if (students) {
    if (hasGrades() && !window.confirm('Replacing the submissions clears the grades given so far. Continue?')) {
      students = null
    } else {
      errorSubmissions.value = null
      pendingStudents.value = students
    }
  }
  if (solution) await loadSolution(solution)
  else if (session.solution) await loadPendingStudents()
}

async function loadSolution(file: File) {
  loadingSolution.value = file.name
  errorSolution.value = null
  try {
    session.setSolution(await analyzeSolution(file))
    // Students already loaded and no new ones on the way: match them to the
    // new questions (their grades stay).
    if (session.students.length && !pendingStudents.value) await session.rematchStudents()
  } catch (e) {
    errorSolution.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingSolution.value = null
  }
  if (session.solution) await loadPendingStudents()
}

async function loadPendingStudents() {
  const job = pendingStudents.value
  if (!job) return
  pendingStudents.value = null
  loadingSubmissions.value = job.label
  errorSubmissions.value = null
  try {
    const result = await job.load()
    session.setStudents(result.students, result.warnings)
    submissionsName.value = job.label
  } catch (e) {
    errorSubmissions.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingSubmissions.value = null
  }
}

// --- removing ----------------------------------------------------------------
async function removeSolution() {
  if (errorSolution.value) {
    errorSolution.value = null
    return
  }
  await session.clearSolution()
}

async function removeStudents() {
  if (pendingStudents.value) {
    pendingStudents.value = null
    return
  }
  if (errorSubmissions.value) {
    errorSubmissions.value = null
    return
  }
  if (hasGrades() && !window.confirm('Removing the submissions also removes the grades given so far. Continue?')) return
  await session.clearStudents()
  submissionsName.value = null
}

// --- page-wide drag & drop ---------------------------------------------------
// A file dropped outside the zones would otherwise make the browser open it
// and leave the app; here it is loaded instead.
const dragging = ref(false)
let dragDepth = 0
const isFileDrag = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes('Files')

function onWindowDragEnter(e: DragEvent) {
  if (!isFileDrag(e)) return
  dragDepth++
  dragging.value = true
}
function onWindowDragLeave(e: DragEvent) {
  if (!isFileDrag(e)) return
  dragDepth = Math.max(0, dragDepth - 1)
  if (!dragDepth) dragging.value = false
}
function onWindowDragOver(e: DragEvent) {
  if (isFileDrag(e)) e.preventDefault()
}
function onWindowDrop(e: DragEvent) {
  if (!isFileDrag(e)) return
  e.preventDefault()
  void handleFiles(Array.from(e.dataTransfer?.files ?? []))
}

onMounted(() => {
  window.addEventListener('dragenter', onWindowDragEnter)
  window.addEventListener('dragleave', onWindowDragLeave)
  window.addEventListener('dragover', onWindowDragOver)
  window.addEventListener('drop', onWindowDrop)
})
onBeforeUnmount(() => {
  window.removeEventListener('dragenter', onWindowDragEnter)
  window.removeEventListener('dragleave', onWindowDragLeave)
  window.removeEventListener('dragover', onWindowDragOver)
  window.removeEventListener('drop', onWindowDrop)
})

async function onContinue() {
  continuing.value = true
  try {
    await session.commitQuestions()
    router.push('/grading')
  } finally {
    continuing.value = false
  }
}
</script>

<template>
  <div class="page">
    <AppHeader subtitle="Setup · load the solution and the submissions" />

    <main class="body">
      <ol class="stepper">
        <li :class="{ active: !session.solution, done: !!session.solution }">
          <span class="dot">1</span> Solution file
        </li>
        <li :class="{ active: !!session.solution && !session.students.length, done: session.students.length > 0 }">
          <span class="dot">2</span> Student submissions
        </li>
        <li :class="{ active: canContinue }">
          <span class="dot">3</span> Start grading
        </li>
      </ol>
      <p class="drop-tip">
        Drag your files onto this page — the solution and the students' .zip can go together, in one drop.
      </p>
      <p v-if="notice" class="notice" role="status">{{ notice }}</p>

      <!-- Step 1 -->
      <section class="card">
        <header class="card-head">
          <h2><span class="num">1</span> Solution file</h2>
          <span class="card-meta">.ipynb or .py — questions detected automatically</span>
        </header>
        <div class="card-body">
          <FileDrop
            class="zone-solution"
            accept=".ipynb,.py"
            v-bind="solutionZone"
            :highlight="dragging"
            @files="(f) => handleFiles(f, 'solution')"
            @remove="removeSolution"
          />

          <div v-if="session.solution" class="results">
            <div class="result-meta">
              <span class="pill type">{{ session.solution.file_type }}</span>
              <span class="pill">
                <strong>{{ enabledCount }}</strong> of {{ session.questions.length }} to grade
              </span>
              <span class="pill total">{{ totalMax }} points total</span>
            </div>
            <p v-if="session.solution.detection === 'whole_file'" class="note">
              No question markers found, so the whole file is graded as one question.
              Check its points below. To split a file into several questions, start each one with a
              comment such as <code># Q1 (2 points)</code> or a block like
              <code>"""ID: 1 · Label: … · Grade: 2 points"""</code>.
            </p>
            <p v-else-if="!session.questions.length" class="error">
              No questions found in this notebook. Start each question with a markdown cell such as
              <code>## Q1 (2 points)</code> or <code>ID: 1 / Label: … / Grade: 2 points</code>.
            </p>
            <div class="bulk-toggle">
              <button class="btn btn-link"
                      :disabled="allEnabled"
                      @click="session.setAllQuestionsEnabled(true)">
                Select all
              </button>
              <span class="sep">·</span>
              <button class="btn btn-link"
                      :disabled="noneEnabled"
                      @click="session.setAllQuestionsEnabled(false)">
                Select none
              </button>
              <span class="bulk-hint">
                Untick a row to skip that question — it won't appear in grading,
                CSV export or per-question plagiarism analysis.
              </span>
            </div>
            <div class="qtable-wrap">
              <table class="qtable">
                <thead>
                  <tr>
                    <th class="check-col">Grade</th>
                    <th>ID</th>
                    <th>Label</th>
                    <th class="num-col">Max points</th>
                    <th>Statement</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="q in session.questions"
                    :key="q.id"
                    :class="{ skipped: !q.enabled }"
                  >
                    <td class="check-col">
                      <input
                        type="checkbox"
                        class="grade-check"
                        :checked="q.enabled"
                        @change="(e) => session.toggleQuestion(q.id, (e.target as HTMLInputElement).checked)"
                        :aria-label="`Grade ${q.id}`"
                      />
                    </td>
                    <td><code class="qcode">{{ q.id }}</code></td>
                    <td>{{ q.label }}</td>
                    <td class="num-col">
                      <PointsInput
                        :model-value="q.max_points"
                        :step="0.5"
                        :min="0"
                        :disabled="!q.enabled"
                        @update:model-value="(v: number) => session.updateMaxPoints(q.id, v)"
                      />
                    </td>
                    <td class="statement">
                      {{ q.statement.slice(0, 130) }}{{ q.statement.length > 130 ? '…' : '' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- Step 2 -->
      <section class="card">
        <header class="card-head">
          <h2><span class="num">2</span> Student submissions</h2>
          <span class="card-meta">a .zip, or the students' .py / .ipynb files</span>
        </header>
        <div class="card-body">
          <FileDrop
            class="zone-zip"
            accept=".zip,.py,.ipynb"
            multiple
            v-bind="submissionsZone"
            :highlight="dragging"
            @files="(f) => handleFiles(f, 'students')"
            @remove="removeStudents"
          />

          <div v-if="session.students.length && session.warnings.length" class="results">
            <div class="result-meta">
              <span class="pill warn">{{ session.warnings.length }} warning(s)</span>
            </div>
            <details class="warn-details">
              <summary>Show warnings</summary>
              <ul>
                <li v-for="(w, i) in session.warnings" :key="i">{{ w }}</li>
              </ul>
            </details>
          </div>
        </div>
      </section>

      <!-- Continue -->
      <footer class="continue">
        <button class="btn btn-primary big" :disabled="!canContinue || continuing" @click="onContinue">
          <span v-if="continuing" class="spin" />
          {{ continuing ? 'Loading…' : 'Continue to grading →' }}
        </button>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; background: var(--bg-page); }


/* Body */
.body {
  max-width: 940px;
  margin: 0 auto;
  padding: 1.25rem 1.25rem 3rem;
  display: flex; flex-direction: column; gap: 1rem;
}

/* Stepper */
.stepper {
  display: flex; gap: 0; align-items: center;
  list-style: none; padding: 0; margin: 0 0 0.5rem;
}
.stepper li {
  flex: 1;
  position: relative;
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.55rem 0.85rem;
  font-size: 0.85rem; color: var(--text-muted);
}
.stepper li::after {
  content: ''; position: absolute; right: 0; top: 50%;
  width: 30%; height: 1px; background: var(--border);
}
.stepper li:last-child::after { display: none; }
.stepper li .dot {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  color: var(--text-muted);
  font-size: 0.78rem; font-weight: 600;
}
.stepper li.active .dot {
  background: var(--accent); border-color: var(--accent); color: white;
}
.stepper li.active { color: var(--text-strong); }
.stepper li.done .dot {
  background: var(--success); border-color: var(--success); color: white;
}
.stepper li.done { color: var(--success); }

/* Cards */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: opacity 0.2s;
}

.card-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.6rem 1rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
}
.card-head h2 {
  margin: 0; font-size: 0.95rem; font-weight: 600; color: var(--text-strong);
  display: flex; align-items: center; gap: 0.55rem;
}
.card-head .num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--accent); color: white; font-size: 0.78rem;
}
.card-head .card-meta { font-size: 0.78rem; color: var(--text-muted); }
.card-body { padding: 1rem 1.1rem; }

.drop-tip { margin: -0.4rem 0 0; font-size: 0.85rem; color: var(--text-muted); text-align: center; }
.notice {
  margin: 0;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  background: var(--warning-soft);
  color: var(--warning-tx);
  font-size: 0.85rem;
  text-align: center;
}

.error {
  margin-top: 0.7rem;
  color: var(--danger);
  background: var(--danger-soft);
  padding: 0.45rem 0.7rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.results { margin-top: 1rem; }
.note {
  margin: 0 0 0.6rem;
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
  border-left: 3px solid var(--warning);
  background: var(--warning-soft);
  color: var(--warning-tx);
  font-size: 0.84rem;
}
.note code, .error code { font-size: 0.8rem; }
.result-meta {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  margin-bottom: 0.6rem;
  font-size: 0.9rem; color: var(--text);
}
.pill {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.74rem;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  color: var(--text-muted);
}
.pill.type {
  background: var(--accent-soft);
  border-color: var(--accent-bd);
  color: var(--accent-tx);
  font-family: ui-monospace, monospace;
}
.pill.total {
  background: var(--success-soft);
  border-color: var(--success-bd);
  color: var(--success-tx);
  font-weight: 600;
}
.pill.warn {
  background: var(--warning-soft);
  border-color: var(--warning-bd);
  color: var(--warning-tx);
}

/* Question table */
.qtable-wrap {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.bulk-toggle {
  display: flex; align-items: center; gap: 0.4rem;
  margin: 0.4rem 0 0.5rem;
  font-size: 0.82rem;
  color: var(--text-muted);
  flex-wrap: wrap;
}
.btn-link {
  background: transparent;
  border: none;
  color: var(--accent);
  padding: 0.15rem 0.3rem;
  font-size: 0.82rem;
  cursor: pointer;
}
.btn-link:hover:not(:disabled) { text-decoration: underline; }
.btn-link:disabled { color: var(--text-muted); cursor: default; }
.bulk-toggle .sep { color: var(--text-muted); }
.bulk-hint { color: var(--text-muted); }

.qtable { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.qtable .check-col { width: 50px; text-align: center; }
.grade-check {
  width: 16px; height: 16px;
  cursor: pointer;
  accent-color: var(--accent);
}
.qtable tr.skipped {
  background: var(--bg-soft);
  opacity: 0.55;
}
.qtable tr.skipped .qcode {
  background: var(--bg-soft);
  border-color: var(--border);
  color: var(--text-muted);
}

.qtable th {
  background: var(--bg-soft);
  padding: 0.5rem 0.7rem;
  text-align: left;
  font-size: 0.74rem; font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border);
}
.qtable td {
  padding: 0.5rem 0.7rem;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.qtable tr:last-child td { border-bottom: none; }
.qtable tr:hover { background: var(--bg-soft); }
.num-col { width: 130px; }
.qcode {
  background: var(--accent-soft);
  color: var(--accent-tx);
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid var(--accent-bd);
}
.statement { color: var(--text-muted); font-size: 0.83rem; max-width: 400px; }

.warn-details { margin-top: 0.7rem; }
.warn-details summary {
  cursor: pointer; color: var(--warning);
  font-size: 0.85rem;
}
.warn-details ul {
  margin: 0.5rem 0 0;
  padding-left: 1.2rem;
  font-size: 0.83rem; color: var(--text-muted);
  max-height: 200px; overflow-y: auto;
}

/* Continue */
.continue { display: flex; justify-content: flex-end; }
.btn.big { padding: 0.7rem 1.5rem; font-size: 1rem; }

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
</style>
