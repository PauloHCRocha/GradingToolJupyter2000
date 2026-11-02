<script setup lang="ts">
/**
 * One question's grading proposal: the solution and the rubric Claude will
 * grade against. Both are plain editable fields — whatever is here when
 * grading starts is exactly what the grader receives.
 */
import { computed } from 'vue'
import type { DetectedQuestion } from '../../api/client'
import { useAutogradeStore } from '../../stores/autograde'
import CodeEditor from '../CodeEditor.vue'
import PointsInput from '../PointsInput.vue'

const props = defineProps<{ question: DetectedQuestion; canGenerate: boolean }>()
const autograde = useAutogradeStore()

const qid = computed(() => props.question.id)
const proposal = computed(() => autograde.proposals[qid.value])
const issue = computed(() => autograde.proposalIssue(qid.value))
const loading = computed(() => !!autograde.proposalLoading[qid.value])
const error = computed(() => autograde.proposalErrors[qid.value])
const total = computed(
  () => Math.round((proposal.value?.criteria ?? []).reduce((a, c) => a + (Number(c.points) || 0), 0) * 100) / 100,
)

function writeManually() {
  autograde.ensureProposal(qid.value)
  autograde.addCriterion(qid.value)
}
</script>

<template>
  <article class="pcard" :class="{ ready: !issue }">
    <header class="phead">
      <code class="qcode">{{ question.id }}</code>
      <span class="pts">{{ question.max_points }} pts</span>
      <span class="status" :class="issue ? 'warn' : 'ok'">{{ issue ? issue : '✓ Ready' }}</span>
      <span class="grow" />
      <button v-if="!proposal" class="btn btn-small" @click="writeManually">Write it myself</button>
      <button
        class="btn btn-small btn-ai"
        :disabled="loading || !canGenerate"
        :title="canGenerate ? '' : 'Add your API key first'"
        @click="autograde.generateProposal(qid)"
      >
        <span v-if="loading" class="spin" />
        {{ loading ? 'Generating…' : proposal ? 'Regenerate' : 'Generate with Claude' }}
      </button>
    </header>

    <p class="statement">{{ question.statement }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="proposal" class="cols">
      <section>
        <h4>Solution</h4>
        <CodeEditor v-model="proposal.solution" :rows="12" placeholder="Reference solution for this question" />
      </section>
      <section>
        <h4>
          Rubric
          <span class="sum" :class="{ bad: total !== Number(question.max_points) }">
            {{ total }} / {{ question.max_points }} pts
          </span>
        </h4>
        <ol class="criteria">
          <li v-for="c in proposal.criteria" :key="c.id">
            <textarea v-model="c.description" rows="2" placeholder="What earns these points" />
            <PointsInput v-model="c.points" :step="0.25" :min="0" />
            <button class="remove" title="Remove criterion" @click="autograde.removeCriterion(qid, c.id)">✕</button>
          </li>
        </ol>
        <button class="btn btn-small" @click="autograde.addCriterion(qid)">+ Add criterion</button>
        <p v-if="proposal.notes" class="notes"><strong>Notes from Claude:</strong> {{ proposal.notes }}</p>
      </section>
    </div>
  </article>
</template>

<style scoped>
.pcard {
  border: 1px solid var(--border);
  border-left: 3px solid var(--warning);
  border-radius: 8px;
  background: var(--bg-card);
  padding: 0.75rem 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.pcard.ready { border-left-color: var(--success); }
.phead { display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap; }
.grow { flex: 1; }
.qcode {
  background: var(--accent-soft);
  color: var(--accent-tx);
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  border: 1px solid var(--accent-bd);
}
.pts { font-size: 0.8rem; color: var(--text-muted); }
.status { font-size: 0.78rem; }
.status.warn { color: var(--warning-tx); }
.status.ok { color: var(--success); font-weight: 600; }
.statement {
  margin: 0;
  font-size: 0.84rem;
  color: var(--text-muted);
  white-space: pre-wrap;
  max-height: 6.5em;
  overflow: auto;
}
.error {
  margin: 0;
  color: var(--danger-tx);
  background: var(--danger-soft);
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  font-size: 0.83rem;
}
.cols { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 0.9rem; }
h4 {
  margin: 0 0 0.4rem;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.sum { text-transform: none; letter-spacing: 0; font-weight: 600; color: var(--success); }
.sum.bad { color: var(--danger); }
.criteria { margin: 0 0 0.5rem; padding-left: 1.2rem; display: flex; flex-direction: column; gap: 0.4rem; }
.criteria li { display: flex; gap: 0.4rem; align-items: flex-start; }
.criteria textarea {
  flex: 1;
  min-width: 0;
  padding: 0.35rem 0.5rem;
  font-size: 0.84rem;
  resize: vertical;
}
.remove {
  border: none;
  background: transparent;
  color: var(--text-muted);
  padding: 0.3rem;
  font-size: 0.85rem;
}
.remove:hover { color: var(--danger); }
.notes {
  margin: 0.5rem 0 0;
  font-size: 0.82rem;
  color: var(--text);
  background: var(--bg-soft);
  padding: 0.45rem 0.6rem;
  border-radius: 6px;
}
.btn-ai { background: var(--ai); border-color: var(--ai); color: white; }
.btn-ai:hover:not(:disabled) { background: var(--ai-hover); border-color: var(--ai-hover); }
.btn-small { padding: 0.25rem 0.6rem; font-size: 0.8rem; }
.spin {
  display: inline-block;
  width: 11px; height: 11px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  margin-right: 0.35rem;
  animation: spin 0.7s linear infinite;
  vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .cols { grid-template-columns: 1fr; }
}
</style>
