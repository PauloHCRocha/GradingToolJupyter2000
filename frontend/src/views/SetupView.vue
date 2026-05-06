<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { analyzeSolution, uploadSubmissions } from '../api/client'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const router = useRouter()

const solutionFile = ref<File | null>(null)
const submissionsFile = ref<File | null>(null)
const loadingSolution = ref(false)
const loadingSubmissions = ref(false)
const continuing = ref(false)
const errorSolution = ref<string | null>(null)
const errorSubmissions = ref<string | null>(null)

const totalMax = computed(() =>
  session.questions.reduce((acc, q) => acc + (Number(q.max_points) || 0), 0),
)

const canContinue = computed(
  () => session.questions.length > 0 && session.students.length > 0,
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
  <main class="setup">
    <header>
      <h1>GradingToolJupyter2000</h1>
      <p class="subtitle">Setup the grading session</p>
    </header>

    <section class="step">
      <header class="step-head">
        <span class="num">1</span>
        <h2>Upload solution file</h2>
      </header>
      <div class="step-body">
        <div class="upload">
          <label class="file-input">
            <input type="file" accept=".ipynb,.py" @change="pickSolution" />
            <span>{{ solutionFile?.name ?? 'Choose a .ipynb or .py file' }}</span>
          </label>
          <button :disabled="!solutionFile || loadingSolution" @click="onAnalyze">
            {{ loadingSolution ? 'Analyzing…' : 'Analyze' }}
          </button>
        </div>
        <p v-if="errorSolution" class="error">{{ errorSolution }}</p>

        <div v-if="session.solution" class="results">
          <p class="meta">
            <strong>{{ session.solution.filename }}</strong> ·
            type <code>{{ session.solution.file_type }}</code> ·
            {{ session.questions.length }} question(s) ·
            total <strong>{{ totalMax }}</strong> points
          </p>
          <table v-if="session.questions.length">
            <thead>
              <tr><th>ID</th><th>Label</th><th>Max points</th><th>Statement</th></tr>
            </thead>
            <tbody>
              <tr v-for="q in session.questions" :key="q.id">
                <td><code>{{ q.id }}</code></td>
                <td>{{ q.label }}</td>
                <td>
                  <input
                    type="number" step="0.5" min="0"
                    :value="q.max_points"
                    @input="(e) => session.updateMaxPoints(q.id, Number((e.target as HTMLInputElement).value))"
                  />
                </td>
                <td class="statement">{{ q.statement.slice(0, 140) }}{{ q.statement.length > 140 ? '…' : '' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="step" :class="{ disabled: !session.solution }">
      <header class="step-head">
        <span class="num">2</span>
        <h2>Upload student submissions (.zip)</h2>
      </header>
      <div class="step-body">
        <div class="upload">
          <label class="file-input">
            <input type="file" accept=".zip" :disabled="!session.solution" @change="pickSubmissions" />
            <span>{{ submissionsFile?.name ?? 'Choose a zip with submission folders' }}</span>
          </label>
          <button
            :disabled="!submissionsFile || !session.solution || loadingSubmissions"
            @click="onUploadSubmissions"
          >
            {{ loadingSubmissions ? 'Uploading…' : 'Upload' }}
          </button>
        </div>
        <p v-if="errorSubmissions" class="error">{{ errorSubmissions }}</p>

        <div v-if="session.students.length" class="results">
          <p class="meta">
            <strong>{{ session.students.length }}</strong> students loaded
            <span v-if="session.warnings.length" class="warn">
              · {{ session.warnings.length }} warning(s)
            </span>
          </p>
          <details v-if="session.warnings.length">
            <summary>Show warnings</summary>
            <ul>
              <li v-for="(w, i) in session.warnings" :key="i">{{ w }}</li>
            </ul>
          </details>
        </div>
      </div>
    </section>

    <footer class="continue">
      <button class="primary" :disabled="!canContinue || continuing" @click="onContinue">
        {{ continuing ? 'Loading…' : 'Continue to grading →' }}
      </button>
    </footer>
  </main>
</template>

<style scoped>
.setup {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  text-align: left;
}

header h1 { margin: 0; }
.subtitle { color: #6b7280; margin: 0.25rem 0 1.5rem; }

.step {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: white;
  margin-bottom: 1.25rem;
  overflow: hidden;
  transition: opacity 0.2s;
}
.step.disabled { opacity: 0.6; }
.step-head {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.step-head h2 { margin: 0; font-size: 1rem; }
.step-head .num {
  display: inline-flex;
  align-items: center; justify-content: center;
  width: 26px; height: 26px;
  border-radius: 50%;
  background: #2563eb; color: white; font-size: 0.85rem; font-weight: 600;
}
.step-body { padding: 1rem; }

.upload { display: flex; gap: 0.75rem; align-items: center; }
.file-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #475569;
}
.file-input input { display: none; }

button {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: white;
  cursor: pointer;
  font-size: 0.9rem;
}
button:disabled { opacity: 0.5; cursor: not-allowed; }

.error { color: #b91c1c; margin-top: 0.75rem; font-size: 0.9rem; }
.warn { color: #92400e; }

.results { margin-top: 1rem; }
.meta { color: #4b5563; font-size: 0.9rem; }

table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.88rem; }
th, td { text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid #f0f1f3; vertical-align: top; }
th { background: #fafafa; font-weight: 600; color: #374151; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.4px; }
.statement { color: #6b7280; font-size: 0.85rem; max-width: 360px; }
input[type="number"] {
  width: 70px; padding: 0.25rem 0.4rem; border: 1px solid #d1d5db; border-radius: 4px;
}

details summary { cursor: pointer; color: #4b5563; }
details ul { font-size: 0.85rem; color: #4b5563; max-height: 200px; overflow-y: auto; }

.continue {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
}
.continue .primary {
  padding: 0.7rem 1.5rem;
  font-size: 1rem;
}
</style>
