<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { useAutogradeStore } from '../stores/autograde'
import type { AiQuestionResult } from '../stores/autograde'
import { anonymizedPreview, downloadGradesCsv } from '../api/client'
import ProposalCard from '../components/autograde/ProposalCard.vue'
import AppHeader from '../components/AppHeader.vue'

const session = useSessionStore()
const autograde = useAutogradeStore()
const router = useRouter()

const showKey = ref(false)
const hasKey = computed(() => autograde.apiKey.trim().length > 0)
const gradable = computed(() => session.students.filter((s) => !s.has_error))
const hasNotebooks = computed(() => gradable.value.some((s) => s.file_type === 'ipynb'))

onMounted(async () => {
  if (!session.enabledQuestions.length || !session.students.length) {
    router.replace('/setup')
    return
  }
  await session.ensureSolutionDetail()
  previewStudentId.value = gradable.value[0]?.id ?? null
})

// --- anonymization preview ----------------------------------------------
const previewStudentId = ref<string | null>(null)
const preview = ref<{ text: string; redactions: number } | null>(null)
const previewError = ref<string | null>(null)

async function loadPreview() {
  if (!previewStudentId.value) return
  previewError.value = null
  try {
    preview.value = await anonymizedPreview(
      previewStudentId.value,
      autograde.settings.stripComments,
      autograde.settings.includeOutputs,
    )
  } catch (e) {
    previewError.value = e instanceof Error ? e.message : String(e)
  }
}
watch(
  [previewStudentId, () => autograde.settings.stripComments, () => autograde.settings.includeOutputs],
  loadPreview,
)

// --- run & review -------------------------------------------------------
const counts = computed(() => {
  const all = Object.values(autograde.results)
  return {
    total: all.length,
    done: all.filter((r) => r.status === 'done').length,
    errors: all.filter((r) => r.status === 'error').length,
    active: all.filter((r) => r.status === 'queued' || r.status === 'running').length,
  }
})
const progressPct = computed(() =>
  counts.value.total ? Math.round(((counts.value.done + counts.value.errors) / counts.value.total) * 100) : 0,
)
const graded = computed(() => counts.value.done > 0)
const staleCount = computed(
  () =>
    Object.values(autograde.results).filter((r) => r.status === 'done' && r.rubricKey !== autograde.rubricKey)
      .length,
)
const totalMax = computed(() =>
  session.enabledQuestions.reduce((a, q) => a + (Number(q.max_points) || 0), 0),
)

function rowTotal(studentId: string): number | null {
  const r = autograde.results[studentId]
  if (r?.status !== 'done') return null
  return session.enabledQuestions.reduce((a, q) => a + (r.questions[q.id]?.points ?? 0), 0)
}

function cellFor(studentId: string, qid: string): AiQuestionResult | null {
  return autograde.resultFor(studentId, qid)
}

function openReview(studentId: string, qid: string) {
  router.push({ path: '/grading', query: { student: studentId, q: qid } })
}

async function acceptRow(studentId: string) {
  for (const q of session.enabledQuestions) {
    if (cellFor(studentId, q.id)?.review === 'pending') await autograde.accept(studentId, q.id)
  }
}

async function exportCsv() {
  const pending = autograde.pendingCount
  if (
    pending &&
    !window.confirm(
      `${pending} grade(s) proposed by Claude are not reviewed yet and won't be in the CSV. Export anyway?`,
    )
  ) {
    return
  }
  await downloadGradesCsv()
}

const tokens = computed(
  () =>
    autograde.usage.input_tokens +
    autograde.usage.cache_read_input_tokens +
    autograde.usage.cache_creation_input_tokens +
    autograde.usage.output_tokens,
)
</script>

<template>
  <div class="page">
    <AppHeader :subtitle="`Auto-grading with Claude · ${gradable.length} submissions`">
      <template #actions>
        <button class="btn btn-primary" @click="exportCsv">Export CSV</button>
      </template>
    </AppHeader>

    <main class="body">
      <!-- 1. Connection & privacy -->
      <section class="card">
        <header class="card-head">
          <h2><span class="num">1</span> Connect to Claude</h2>
          <span class="card-meta">Requests go from this browser straight to the Claude API</span>
        </header>
        <div class="card-body settings">
          <label class="field key">
            <span>Claude API key</span>
            <div class="key-row">
              <input :type="showKey ? 'text' : 'password'" v-model="autograde.apiKey"
                     placeholder="sk-ant-…" autocomplete="off" spellcheck="false" />
              <button class="btn btn-small" @click="showKey = !showKey">{{ showKey ? 'Hide' : 'Show' }}</button>
            </div>
            <label class="check">
              <input type="checkbox" v-model="autograde.rememberKey" />
              Remember on this device (otherwise it is forgotten when the tab closes)
            </label>
          </label>
          <label class="field">
            <span>Model</span>
            <select v-model="autograde.settings.model">
              <option value="claude-opus-5-5">Claude Opus 5.5 (most capable)</option>
              <option value="claude-sonnet-5-5">Claude Sonnet 5.5 (faster, cheaper)</option>
            </select>
          </label>
          <label class="field">
            <span>Effort</span>
            <select v-model="autograde.settings.effort">
              <option value="high">High — most careful</option>
              <option value="medium">Medium</option>
              <option value="low">Low — fastest</option>
            </select>
          </label>
          <label class="field">
            <span>Language for rubric and feedback</span>
            <input v-model="autograde.settings.language" />
          </label>
          <label class="field">
            <span>Parallel requests</span>
            <select v-model.number="autograde.settings.concurrency">
              <option v-for="n in [1, 2, 3, 4, 6, 8]" :key="n" :value="n">{{ n }}</option>
            </select>
          </label>
        </div>
        <div class="privacy">
          <div>
            <h4>Sent to Claude</h4>
            <ul>
              <li>Your question statements, solutions and rubrics.</li>
              <li>The code of each submission <strong>after anonymization</strong> — check it in step 3.</li>
              <li>One submission per request, in random order, with no identifier attached.</li>
            </ul>
          </div>
          <div>
            <h4>Never leaves this browser</h4>
            <ul>
              <li>Student names, numbers, e-mails, file and folder names.</li>
              <li>Grades, and which result belongs to which student.</li>
              <li>Anything at all until you click a Claude button below.</li>
            </ul>
          </div>
          <p class="fine">
            Anonymization removes identifying text, but code style can still be distinctive. Check your
            institution's data-protection rules and your organisation's agreement with Anthropic (data retention,
            DPA) before grading real submissions.
          </p>
        </div>
      </section>

      <!-- 2. Proposals -->
      <section class="card">
        <header class="card-head">
          <h2><span class="num">2</span> Solutions and rubrics</h2>
          <button class="btn btn-small btn-ai" :disabled="!hasKey" @click="autograde.generateMissingProposals()">
            Generate all missing
          </button>
        </header>
        <div class="card-body">
          <p class="lead">
            Claude proposes a solution and a rubric per question, starting from your reference file. Edit both —
            the grader uses exactly what is here, and each rubric must add up to the question's points.
          </p>
          <div class="proposals">
            <ProposalCard v-for="q in session.enabledQuestions" :key="q.id" :question="q" :can-generate="hasKey" />
          </div>
        </div>
      </section>

      <!-- 3. Anonymization -->
      <section class="card">
        <header class="card-head">
          <h2><span class="num">3</span> Check what will be sent</h2>
          <span class="card-meta">This preview is computed locally</span>
        </header>
        <div class="card-body">
          <div class="anon-options">
            <label class="check">
              <input type="checkbox" v-model="autograde.settings.stripComments" />
              Remove all comments (question headers are kept)
            </label>
            <label v-if="hasNotebooks" class="check">
              <input type="checkbox" v-model="autograde.settings.includeOutputs" />
              Include notebook cell outputs
            </label>
            <label class="field inline">
              <span>Preview</span>
              <select v-model="previewStudentId">
                <option v-for="s in gradable" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </label>
            <span v-if="preview" class="pill">{{ preview.redactions }} item(s) redacted</span>
          </div>
          <p v-if="previewError" class="error">{{ previewError }}</p>
          <pre v-if="preview" class="anon-preview">{{ preview.text }}</pre>
          <p class="fine">
            Names and numbers of every student in the zip, e-mails, ID-like numbers and lines such as
            “# Nome: …” are replaced by placeholders like <code>&lt;NAME&gt;</code> before anything is sent.
          </p>
        </div>
      </section>

      <!-- 4. Grade & review -->
      <section class="card">
        <header class="card-head">
          <h2><span class="num">4</span> Grade and review</h2>
          <span class="card-meta">
            {{ tokens.toLocaleString() }} tokens · ≈ ${{ autograde.estimatedCost.toFixed(2) }} this session
          </span>
        </header>
        <div class="card-body">
          <div class="run-row">
            <button class="btn btn-ai" :disabled="autograde.running || !hasKey || !autograde.allProposalsReady"
                    @click="autograde.runGrading(graded ? 'missing' : 'all')">
              <span v-if="autograde.running" class="spin" />
              {{ graded ? 'Grade remaining' : `Grade ${gradable.length} submissions` }}
            </button>
            <button v-if="graded && !autograde.running" class="btn" @click="autograde.runGrading('all')">
              Re-grade all
            </button>
            <button v-if="autograde.running" class="btn" @click="autograde.stop()">Stop</button>
            <span v-if="!autograde.allProposalsReady" class="hint">Every question needs a finished rubric (step 2).</span>
            <span v-else-if="!hasKey" class="hint">Add your API key (step 1).</span>
          </div>
          <p v-if="autograde.runError" class="error">{{ autograde.runError }}</p>

          <div v-if="counts.total" class="progress">
            <div class="bar"><div class="fill" :style="{ width: progressPct + '%' }" /></div>
            <span>
              {{ counts.done }} graded<template v-if="counts.errors"> · {{ counts.errors }} failed</template>
              <template v-if="counts.active"> · {{ counts.active }} in progress</template>
            </span>
          </div>
          <p v-if="staleCount" class="warn-line">
            {{ staleCount }} submission(s) were graded with an older rubric — “Grade remaining” re-grades them.
          </p>

          <template v-if="counts.total">
            <div class="bulk">
              <span><strong>{{ autograde.pendingCount }}</strong> grade(s) waiting for your review.</span>
              <button class="btn btn-small" :disabled="!autograde.pendingCount" @click="autograde.acceptAll(true)">
                Accept all high-confidence
              </button>
              <button class="btn btn-small" :disabled="!autograde.pendingCount" @click="autograde.acceptAll(false)">
                Accept all
              </button>
            </div>
            <div class="table-wrap">
              <table class="results">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th v-for="q in session.enabledQuestions" :key="q.id" class="num">{{ q.id }}</th>
                    <th class="num">Total</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in gradable" :key="s.id">
                    <td>
                      <div class="sname">{{ s.name }}</div>
                      <div v-if="autograde.results[s.id]" class="pseudo">
                        sent as {{ autograde.results[s.id].pseudonym }}
                        <span v-if="autograde.results[s.id].flags.length" class="flag"
                              :title="autograde.results[s.id].flags.join('\n')">⚠ integrity flag</span>
                      </div>
                    </td>
                    <template v-if="autograde.results[s.id]?.status === 'done'">
                      <td v-for="q in session.enabledQuestions" :key="q.id" class="num">
                        <button v-if="cellFor(s.id, q.id)" class="cell" :class="[cellFor(s.id, q.id)!.review, cellFor(s.id, q.id)!.confidence]"
                                :title="`${cellFor(s.id, q.id)!.review} · confidence ${cellFor(s.id, q.id)!.confidence} — click to review`"
                                @click="openReview(s.id, q.id)">
                          {{ cellFor(s.id, q.id)!.points }}
                        </button>
                      </td>
                      <td class="num total">{{ rowTotal(s.id) }} / {{ totalMax }}</td>
                      <td class="row-act">
                        <button class="btn btn-small" @click="acceptRow(s.id)">Accept row</button>
                      </td>
                    </template>
                    <td v-else :colspan="session.enabledQuestions.length + 2" class="status-cell"
                        :class="autograde.results[s.id]?.status">
                      <template v-if="!autograde.results[s.id]">not graded</template>
                      <template v-else-if="autograde.results[s.id].status === 'error'">✗ {{ autograde.results[s.id].error }}</template>
                      <template v-else-if="autograde.results[s.id].status === 'running'"><span class="spin" /> grading…</template>
                      <template v-else>queued</template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="legend">
              <span class="cell pending">pending</span>
              <span class="cell accepted">accepted</span>
              <span class="cell overridden">changed by you</span>
              <span class="cell rejected">rejected</span>
              <span>· a dashed border means low confidence · click a grade to review it next to the code</span>
            </p>
          </template>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; background: var(--bg-page); }


.body {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.25rem 1.25rem 3rem;
  display: flex; flex-direction: column; gap: 1rem;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
.card-head {
  display: flex; justify-content: space-between; align-items: center; gap: 0.75rem;
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
  background: var(--ai); color: white; font-size: 0.78rem;
}
.card-meta { font-size: 0.78rem; color: var(--text-muted); }
.card-body { padding: 1rem 1.1rem; }
.lead { margin: 0 0 0.8rem; font-size: 0.88rem; color: var(--text); }
.hint { font-size: 0.82rem; color: var(--text-muted); }
.fine { margin: 0.6rem 0 0; font-size: 0.78rem; color: var(--text-muted); }
.error {
  color: var(--danger-tx); background: var(--danger-soft);
  padding: 0.45rem 0.7rem; border-radius: 6px; font-size: 0.85rem;
}
.warn-line { font-size: 0.83rem; color: var(--warning-tx); margin: 0.4rem 0; }

/* settings */
.settings { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 0.8rem 1rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.85rem; }
.field > span { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 600; }
.field input, .field select { padding: 0.45rem 0.6rem; font-size: 0.88rem; }
.field.key { grid-row: span 2; }
.field.inline { flex-direction: row; align-items: center; gap: 0.5rem; }
.key-row { display: flex; gap: 0.4rem; }
.key-row input { flex: 1; font-family: ui-monospace, monospace; }
.check { display: flex; align-items: center; gap: 0.45rem; font-size: 0.83rem; color: var(--text); }
.check input { accent-color: var(--ai); }

.privacy {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0 1.2rem;
  padding: 0.8rem 1.1rem 1rem;
  border-top: 1px solid var(--border);
  background: var(--ai-soft);
}
.privacy h4 { margin: 0 0 0.3rem; font-size: 0.82rem; color: var(--text-strong); }
.privacy ul { margin: 0; padding-left: 1.1rem; font-size: 0.83rem; color: var(--text); }
.privacy .fine { grid-column: 1 / -1; }

.proposals { display: flex; flex-direction: column; gap: 0.75rem; }

/* anonymization */
.anon-options { display: flex; align-items: center; gap: 1.1rem; flex-wrap: wrap; margin-bottom: 0.6rem; }
.anon-options select { padding: 0.35rem 0.5rem; font-size: 0.85rem; }
.pill {
  padding: 2px 9px; border-radius: 999px; font-size: 0.74rem;
  background: var(--success-soft); color: var(--success-tx); border: 1px solid var(--success-bd);
}
.anon-preview {
  margin: 0;
  max-height: 340px; overflow: auto;
  padding: 0.6rem 0.8rem;
  background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.8rem; line-height: 1.5;
}

/* run */
.run-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.progress { display: flex; align-items: center; gap: 0.7rem; margin: 0.8rem 0 0.4rem; font-size: 0.83rem; color: var(--text-muted); }
.progress .bar { flex: 1; height: 8px; background: var(--bg-soft); border: 1px solid var(--border); border-radius: 999px; overflow: hidden; }
.progress .fill { height: 100%; background: var(--ai); }
.bulk { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; margin: 0.8rem 0 0.6rem; font-size: 0.86rem; }

.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
.results { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.results th {
  background: var(--bg-soft); padding: 0.45rem 0.6rem; text-align: left;
  font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted);
  border-bottom: 1px solid var(--border);
}
.results td { padding: 0.4rem 0.6rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.results tr:last-child td { border-bottom: none; }
.results .num { text-align: center; }
.results .total { font-weight: 600; white-space: nowrap; }
.sname { font-weight: 500; color: var(--text-strong); }
.pseudo { font-size: 0.72rem; color: var(--text-muted); font-family: ui-monospace, monospace; }
.flag { color: var(--danger); font-family: inherit; margin-left: 0.3rem; cursor: help; }
.status-cell { color: var(--text-muted); font-size: 0.82rem; }
.status-cell.error { color: var(--danger-tx); }
.row-act { text-align: right; white-space: nowrap; }

.cell {
  display: inline-block;
  min-width: 3rem;
  padding: 0.2rem 0.45rem;
  border-radius: 5px;
  border: 1.5px solid var(--ai);
  background: var(--ai-soft);
  color: var(--text-strong);
  font-family: ui-monospace, monospace;
  font-weight: 600;
  font-size: 0.84rem;
}
button.cell:hover { filter: brightness(0.95); }
.cell.low { border-style: dashed; }
.cell.accepted { border-color: var(--success); background: var(--success-soft); color: var(--success-tx); }
.cell.overridden { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-tx); }
.cell.rejected { border-color: var(--danger); background: var(--danger-soft); color: var(--danger-tx); text-decoration: line-through; }
.legend { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.76rem; color: var(--text-muted); margin: 0.6rem 0 0; }
.legend .cell { min-width: 0; font-family: inherit; font-weight: 500; font-size: 0.72rem; }

.btn-ai { background: var(--ai); border-color: var(--ai); color: white; }
.btn-ai:hover:not(:disabled) { background: var(--ai-hover); border-color: var(--ai-hover); }
.btn-small { padding: 0.25rem 0.6rem; font-size: 0.8rem; }

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

@media (max-width: 900px) {
  .settings { grid-template-columns: 1fr; }
  .field.key { grid-row: auto; }
  .privacy { grid-template-columns: 1fr; }
}
</style>
