<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { analyzeSolution, uploadSubmissions } from '../api/client'
import { useSessionStore } from '../stores/session'
import ThemeToggle from '../components/ThemeToggle.vue'
import PointsInput from '../components/PointsInput.vue'

const session = useSessionStore()
const router = useRouter()

const solutionFile = ref<File | null>(null)
const submissionsFile = ref<File | null>(null)
const loadingSolution = ref(false)
const loadingSubmissions = ref(false)
const continuing = ref(false)
const errorSolution = ref<string | null>(null)
const errorSubmissions = ref<string | null>(null)

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

const canContinue = computed(
  () => session.enabledQuestions.length > 0 && session.students.length > 0,
)

function pickSolution(e: Event) {
  solutionFile.value = (e.target as HTMLInputElement).files?.[0] ?? null
  errorSolution.value = null
}

function pickSubmissions(e: Event) {
  submissionsFile.value = (e.target as HTMLInputElement).files?.[0] ?? null
  errorSubmissions.value = null
}

async function onAnalyze() {
  if (!solutionFile.value) return
  loadingSolution.value = true
  errorSolution.value = null
  try {
    const analysis = await analyzeSolution(solutionFile.value)
    session.setSolution(analysis)
  } catch (e) {
    errorSolution.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingSolution.value = false
  }
}

async function onUploadSubmissions() {
  if (!submissionsFile.value) return
  loadingSubmissions.value = true
  errorSubmissions.value = null
  try {
    const result = await uploadSubmissions(submissionsFile.value)
    session.setStudents(result.students, result.warnings)
  } catch (e) {
    errorSubmissions.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingSubmissions.value = false
  }
}

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
    <header class="appbar">
      <RouterLink to="/" class="title" title="Back to landing">
        <h1>Granymede</h1>
        <span class="meta">Setup · configure a new grading session</span>
      </RouterLink>
      <ThemeToggle />
    </header>

    <main class="body">
      <ol class="stepper">
        <li :class="{ active: !session.solution, done: !!session.solution }">
          <span class="dot">1</span> Solution file
        </li>
        <li :class="{ active: !!session.solution && !session.students.length, done: session.students.length > 0 }">
          <span class="dot">2</span> Submissions zip
        </li>
        <li :class="{ active: canContinue }">
          <span class="dot">3</span> Start grading
        </li>
      </ol>

      <!-- Step 1 -->
      <section class="card">
        <header class="card-head">
          <h2><span class="num">1</span> Upload solution file</h2>
          <span class="card-meta">.ipynb or .py — questions detected automatically</span>
        </header>
        <div class="card-body">
          <div class="upload">
            <label class="file-input" :class="{ filled: !!solutionFile }">
              <input type="file" accept=".ipynb,.py" @change="pickSolution" />
              <span class="icon">{{ solutionFile ? '📄' : '⬆' }}</span>
              <span class="text">{{ solutionFile?.name ?? 'Choose a .ipynb or .py file' }}</span>
            </label>
            <button class="btn btn-primary" :disabled="!solutionFile || loadingSolution" @click="onAnalyze">
              <span v-if="loadingSolution" class="spin" />
              {{ loadingSolution ? 'Analyzing…' : 'Analyze' }}
            </button>
          </div>
          <p v-if="errorSolution" class="error">{{ errorSolution }}</p>

          <div v-if="session.solution" class="results">
            <div class="result-meta">
              <span><strong>{{ session.solution.filename }}</strong></span>
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
      <section class="card" :class="{ dimmed: !session.solution }">
        <header class="card-head">
          <h2><span class="num">2</span> Upload student submissions</h2>
          <span class="card-meta">.zip with the Moodle-style folders inside</span>
        </header>
        <div class="card-body">
          <div class="upload">
            <label class="file-input" :class="{ filled: !!submissionsFile, disabled: !session.solution }">
              <input type="file" accept=".zip" :disabled="!session.solution" @change="pickSubmissions" />
              <span class="icon">{{ submissionsFile ? '📦' : '⬆' }}</span>
              <span class="text">{{ submissionsFile?.name ?? 'Choose a zip with submission folders' }}</span>
            </label>
            <button class="btn btn-primary"
              :disabled="!submissionsFile || !session.solution || loadingSubmissions"
              @click="onUploadSubmissions">
              <span v-if="loadingSubmissions" class="spin" />
              {{ loadingSubmissions ? 'Uploading…' : 'Upload' }}
            </button>
          </div>
          <p v-if="errorSubmissions" class="error">{{ errorSubmissions }}</p>

          <div v-if="session.students.length" class="results">
            <div class="result-meta">
              <span><strong>{{ session.students.length }}</strong> students loaded</span>
              <span v-if="session.warnings.length" class="pill warn">
                {{ session.warnings.length }} warning(s)
              </span>
            </div>
            <details v-if="session.warnings.length" class="warn-details">
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

/* Appbar */
.appbar {
  background: var(--header-bg);
  color: var(--header-text);
  padding: 0.7rem 1.25rem;
  display: flex; align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.appbar h1 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: -0.015em;
}
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
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: opacity 0.2s;
}
.card.dimmed { opacity: 0.55; }

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

/* Upload */
.upload { display: flex; gap: 0.65rem; align-items: center; }
.file-input {
  flex: 1;
  display: flex; align-items: center; gap: 0.55rem;
  padding: 0.65rem 0.85rem;
  background: var(--bg-soft);
  border: 2px dashed var(--border-strong);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.file-input:hover:not(.disabled) {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.file-input.filled { border-style: solid; border-color: var(--success); background: var(--success-soft); }
.file-input.disabled { cursor: not-allowed; opacity: 0.55; }
.file-input input { display: none; }
.file-input .icon { font-size: 1.05rem; }
.file-input .text { font-size: 0.9rem; color: var(--text); }

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
