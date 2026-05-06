<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { exportGradesUrl } from '../api/client'
import NotebookViewer from '../components/NotebookViewer.vue'

const session = useSessionStore()
const router = useRouter()

const draft = reactive<Record<string, { points: number; comment: string }>>({})
const saving = ref<Record<string, boolean>>({})
const error = ref<string | null>(null)

const totalMax = computed(() =>
  session.questions.reduce((acc, q) => acc + (Number(q.max_points) || 0), 0),
)

const totalCurrent = computed(() =>
  Object.values(session.studentGrades).reduce((acc, g) => acc + (g?.points ?? 0), 0),
)

const gradedCount = computed(
  () => session.students.filter((s) => s.total_grade > 0).length,
)

onMounted(() => {
  if (!session.questions.length || !session.students.length) {
    router.replace('/setup')
    return
  }
  if (session.students.length && !session.selectedStudentId) {
    void selectFirst()
  }
})

async function selectFirst() {
  const first = session.students.find((s) => !s.has_error)
  if (first) await selectStudent(first.id)
}

async function selectStudent(id: string) {
  error.value = null
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
    draft[q.id] = {
      points: g ? Number(g.points) : 0,
      comment: g ? g.comment : '',
    }
  }
}

watch(
  () => session.selectedStudentId,
  () => syncDraft(),
)

async function save(qid: string) {
  if (!draft[qid]) return
  saving.value[qid] = true
  error.value = null
  try {
    await session.saveGrade(qid, Number(draft[qid].points) || 0, draft[qid].comment)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value[qid] = false
  }
}

function clamp(qid: string) {
  const q = session.questions.find((x) => x.id === qid)
  if (!q) return
  const max = Number(q.max_points) || 0
  if (draft[qid].points < 0) draft[qid].points = 0
  if (draft[qid].points > max) draft[qid].points = max
}

function statusClass(s: { total_grade: number; has_error: boolean }) {
  if (s.has_error) return 'err'
  if (s.total_grade > 0) return 'graded'
  return 'pending'
}
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <div class="brand">
        <h1>GradingToolJupyter2000</h1>
        <span class="meta">
          {{ session.students.length }} students ·
          {{ gradedCount }} graded ·
          {{ session.questions.length }} questions / {{ totalMax }} pts
        </span>
      </div>
      <div class="actions">
        <button class="ghost" @click="router.push('/setup')">← Back to setup</button>
        <a class="primary" :href="exportGradesUrl()" download>Export grades.csv</a>
      </div>
    </header>

    <aside class="sidebar">
      <h2>Students</h2>
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
          <div v-if="s.has_error" class="err-msg">{{ s.error }}</div>
        </li>
      </ul>
    </aside>

    <main class="main">
      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="!session.studentDetail" class="placeholder">
        Select a student from the list to start grading.
      </div>

      <template v-else>
        <header class="student-head">
          <div>
            <h2>{{ session.studentDetail.info.name }}</h2>
            <span class="meta">
              #{{ session.studentDetail.info.id }} ·
              <code>{{ session.studentDetail.info.filename }}</code>
            </span>
          </div>
          <div class="total">
            <span class="label">Current grade</span>
            <strong>{{ totalCurrent.toFixed(1) }} / {{ totalMax }}</strong>
          </div>
        </header>

        <div v-if="session.studentDetail.info.has_error" class="warn">
          {{ session.studentDetail.info.error }}
        </div>

        <NotebookViewer :cells="session.studentDetail.cells" />
      </template>
    </main>

    <section class="grading">
      <h2>Grading</h2>
      <div v-if="!session.selectedStudentId" class="placeholder">No student selected.</div>
      <ul v-else class="questions">
        <li v-for="q in session.questions" :key="q.id">
          <div class="qhead">
            <strong>{{ q.label }}</strong>
            <span class="qmax">/ {{ q.max_points }}</span>
          </div>
          <div class="qrow">
            <input
              type="number"
              step="0.25"
              :max="q.max_points"
              min="0"
              v-model.number="draft[q.id].points"
              @blur="clamp(q.id)"
            />
            <button :disabled="saving[q.id]" @click="save(q.id)">
              {{ saving[q.id] ? '…' : 'Save' }}
            </button>
          </div>
          <textarea
            v-model="draft[q.id].comment"
            placeholder="Comment (optional)"
            rows="2"
          />
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    'topbar topbar topbar'
    'sidebar main grading';
  height: 100vh;
}

.topbar {
  grid-area: topbar;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}
.brand h1 { margin: 0; font-size: 1.05rem; }
.brand .meta { font-size: 0.8rem; color: #6b7280; }

.actions { display: flex; gap: 0.5rem; }
.actions button, .actions a {
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.875rem;
  border: 1px solid transparent;
  cursor: pointer;
  text-decoration: none;
}
.ghost { background: white; border-color: #d1d5db; color: #1f2937; }
.primary { background: #2563eb; color: white; border-color: #2563eb; }

.sidebar {
  grid-area: sidebar;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
  background: #fafafa;
}
.sidebar h2 { margin: 0; padding: 0.75rem 1rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; }
.sidebar ul { list-style: none; margin: 0; padding: 0; }
.sidebar li {
  padding: 0.6rem 1rem;
  border-bottom: 1px solid #f0f1f3;
  cursor: pointer;
  transition: background 0.1s;
}
.sidebar li:hover { background: #eef2ff; }
.sidebar li.active { background: #dbeafe; border-left: 3px solid #2563eb; padding-left: calc(1rem - 3px); }
.row1 { display: flex; align-items: center; gap: 0.4rem; }
.row1 strong { font-size: 0.9rem; }
.row2 { display: flex; justify-content: space-between; font-size: 0.78rem; color: #6b7280; margin-top: 2px; }
.num { font-family: ui-monospace, monospace; }
.grade { font-weight: 600; color: #1f2937; }
.err-msg { color: #b91c1c; font-size: 0.75rem; margin-top: 4px; }
.dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: #d1d5db;
}
.graded .dot { background: #10b981; }
.err .dot { background: #ef4444; }

.main {
  grid-area: main;
  overflow-y: auto;
  padding: 1rem 1.25rem 2rem;
  background: #f9fafb;
}
.student-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}
.student-head h2 { margin: 0 0 0.2rem; }
.student-head .meta { font-size: 0.85rem; color: #6b7280; }
.total { text-align: right; }
.total .label { display: block; font-size: 0.7rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }
.total strong { font-size: 1.4rem; color: #2563eb; }
.placeholder { color: #9ca3af; padding: 2rem; text-align: center; }
.error { color: #b91c1c; padding: 0.5rem; background: #fee2e2; border-radius: 4px; }
.warn { color: #92400e; padding: 0.5rem 0.75rem; background: #fef3c7; border-left: 3px solid #f59e0b; border-radius: 4px; margin-bottom: 1rem; font-size: 0.85rem; }

.grading {
  grid-area: grading;
  border-left: 1px solid #e5e7eb;
  background: white;
  overflow-y: auto;
  padding: 0;
}
.grading h2 { margin: 0; padding: 0.75rem 1rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; border-bottom: 1px solid #e5e7eb; }
.questions { list-style: none; margin: 0; padding: 0.5rem 0.75rem; }
.questions li {
  padding: 0.6rem;
  border-bottom: 1px solid #f0f1f3;
}
.qhead { display: flex; justify-content: space-between; font-size: 0.9rem; }
.qmax { color: #6b7280; font-size: 0.85rem; }
.qrow { display: flex; gap: 0.4rem; align-items: center; margin: 0.4rem 0; }
.qrow input {
  flex: 1; padding: 0.3rem 0.5rem; border: 1px solid #d1d5db; border-radius: 4px;
  font-family: ui-monospace, monospace;
}
.qrow button {
  padding: 0.3rem 0.7rem;
  background: #2563eb; color: white; border: none; border-radius: 4px;
  cursor: pointer; font-size: 0.85rem;
}
.qrow button:disabled { opacity: 0.5; }
.questions textarea {
  width: 100%; padding: 0.3rem 0.5rem; border: 1px solid #d1d5db; border-radius: 4px;
  font-family: inherit; font-size: 0.82rem; resize: vertical;
}

@media (max-width: 1100px) {
  .layout { grid-template-columns: 240px 1fr 280px; }
}
</style>
