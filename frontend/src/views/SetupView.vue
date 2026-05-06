<script setup lang="ts">
import { ref, computed } from 'vue'
import { analyzeSolution } from '../api/client'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const file = ref<File | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const totalMax = computed(() =>
  session.questions.reduce((acc, q) => acc + (Number(q.max_points) || 0), 0),
)

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  file.value = target.files?.[0] ?? null
  error.value = null
}

async function onAnalyze() {
  if (!file.value) return
  loading.value = true
  error.value = null
  try {
    const analysis = await analyzeSolution(file.value)
    session.setSolution(analysis)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="setup">
    <header>
      <h1>GraderAssistant2000</h1>
      <p class="subtitle">Step 1 — Upload solution file</p>
    </header>

    <section class="upload-card">
      <label class="file-input">
        <input type="file" accept=".ipynb,.py" @change="onFileChange" />
        <span>{{ file?.name ?? 'Choose a .ipynb or .py file' }}</span>
      </label>
      <button :disabled="!file || loading" @click="onAnalyze">
        {{ loading ? 'Analyzing…' : 'Analyze' }}
      </button>
    </section>

    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="session.solution" class="results">
      <h2>Detected questions</h2>
      <p class="meta">
        <strong>{{ session.solution.filename }}</strong> ·
        type <code>{{ session.solution.file_type }}</code> ·
        {{ session.questions.length }} question(s) ·
        total <strong>{{ totalMax }}</strong> points
      </p>

      <table v-if="session.questions.length">
        <thead>
          <tr>
            <th>ID</th>
            <th>Label</th>
            <th>Max points</th>
            <th>Statement</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="q in session.questions" :key="q.id">
            <td><code>{{ q.id }}</code></td>
            <td>{{ q.label }}</td>
            <td>
              <input
                type="number"
                step="0.5"
                min="0"
                :value="q.max_points"
                @input="(e) => session.updateMaxPoints(q.id, Number((e.target as HTMLInputElement).value))"
              />
            </td>
            <td class="statement">{{ q.statement.slice(0, 160) }}{{ q.statement.length > 160 ? '…' : '' }}</td>
          </tr>
        </tbody>
      </table>

      <p v-else class="warn">
        No questions detected. The file does not seem to follow the
        <code>Question N</code> / <code>QN-M</code> convention.
      </p>
    </section>
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
.subtitle { color: #666; margin: 0.25rem 0 1.5rem; }

.upload-card {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.file-input {
  flex: 1;
  display: inline-block;
  padding: 0.5rem 0.75rem;
  border: 1px dashed #bbb;
  border-radius: 6px;
  cursor: pointer;
}
.file-input input { display: none; }

button {
  padding: 0.55rem 1rem;
  border-radius: 6px;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: white;
  cursor: pointer;
}
button:disabled { opacity: 0.5; cursor: not-allowed; }

.error { color: #b91c1c; margin-top: 1rem; }
.warn { color: #92400e; }

.results { margin-top: 2rem; }
.meta { color: #555; font-size: 0.95rem; }

table { width: 100%; border-collapse: collapse; margin-top: 0.75rem; }
th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #eee; vertical-align: top; }
th { background: #fafafa; font-weight: 600; }
.statement { color: #555; font-size: 0.9rem; max-width: 360px; }

input[type="number"] {
  width: 80px;
  padding: 0.25rem 0.4rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}
</style>
