<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SuspiciousPair } from '../../api/client'
import { clusterColor, severityClass } from './colors'

const props = defineProps<{
  pairs: SuspiciousPair[]
  threshold: number
}>()
const emit = defineEmits<{
  compare: [s1: string, s2: string]
  exportPdf: [pair: SuspiciousPair]
}>()

type SortMode = 'similarity' | 'cluster'
const sortMode = ref<SortMode>('similarity')

const sorted = computed(() => {
  const arr = [...props.pairs]
  if (sortMode.value === 'cluster') {
    arr.sort((a, b) => {
      // Pairs with the same cluster come first, grouped by cluster_id, then
      // ordered by similarity within. Outliers (-1) go last.
      const ca = a.cluster_id < 0 ? 1 : 0
      const cb = b.cluster_id < 0 ? 1 : 0
      if (ca !== cb) return ca - cb
      if (a.cluster_id !== b.cluster_id) return a.cluster_id - b.cluster_id
      return b.similarity - a.similarity
    })
  } else {
    arr.sort((a, b) => b.similarity - a.similarity)
  }
  return arr
})

function rgba(hex: string, alpha: number): string {
  const m = hex.replace('#', '').match(/.{2}/g)
  if (!m) return hex
  const [r, g, b] = m.map((s) => parseInt(s, 16))
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
</script>

<template>
  <div class="pairs-tab">
    <header class="bar">
      <p class="meta">
        <strong>{{ pairs.length }}</strong> pair(s) above
        <strong>{{ threshold.toFixed(2) }}</strong>
      </p>
      <label class="sort">
        Sort by
        <select v-model="sortMode">
          <option value="similarity">Similarity (descending)</option>
          <option value="cluster">Cluster grouping</option>
        </select>
      </label>
    </header>

    <p v-if="!pairs.length" class="placeholder">
      No pairs above threshold. Lower the threshold to see less-suspicious pairs.
    </p>

    <ul v-else class="list">
      <li
        v-for="p in sorted"
        :key="p.student1_id + '-' + p.student2_id"
        :class="severityClass(p.similarity)"
        :style="p.cluster_id >= 0 ? {
          background: `linear-gradient(90deg, ${rgba(clusterColor(p.cluster_id), 0.18)}, ${rgba(clusterColor(p.cluster_id), 0.05)})`,
          borderLeftColor: clusterColor(p.cluster_id),
        } : {}"
      >
        <div class="names" @click="emit('compare', p.student1_id, p.student2_id)">
          <strong>{{ p.student1_name }}</strong>
          <span class="sep">↔</span>
          <strong>{{ p.student2_name }}</strong>
          <span v-if="p.cluster_id >= 0" class="cluster-badge"
                :style="{ background: clusterColor(p.cluster_id), color: 'white' }">
            cluster #{{ p.cluster_id + 1 }}
          </span>
        </div>
        <div class="meta-line">
          <code>#{{ p.student1_id }}</code> · <code>#{{ p.student2_id }}</code>
        </div>
        <div class="score" :class="severityClass(p.similarity)">
          {{ Math.round(p.similarity * 100) }}%
        </div>
        <div class="actions">
          <button class="btn btn-small"
                  @click.stop="emit('compare', p.student1_id, p.student2_id)">
            Compare
          </button>
          <button class="btn btn-small btn-pdf"
                  @click.stop="emit('exportPdf', p)">
            PDF
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.pairs-tab { padding: 1rem 1.25rem 1.5rem; }
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
  gap: 0.6rem;
}
.bar .meta { margin: 0; color: var(--text-muted); font-size: 0.9rem; }
.bar .meta strong { color: var(--text-strong); }
.sort { display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text-muted); }
.sort select { padding: 0.3rem 0.5rem; font-size: 0.85rem; }

.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.4rem; }
.list li {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.85rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 4px solid var(--text-muted);
  border-radius: 6px;
  transition: transform 0.1s;
}
.list li:hover { transform: translateY(-1px); }
.list li.low { border-left-color: var(--success); }
.list li.med { border-left-color: var(--warning); }
.list li.high { border-left-color: var(--danger); }

.names { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; cursor: pointer; }
.names strong { color: var(--text-strong); font-size: 0.95rem; }
.names .sep { color: var(--text-muted); }
.cluster-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  letter-spacing: 0.4px;
  font-weight: 600;
}
.meta-line { color: var(--text-muted); font-size: 0.8rem; }
.meta-line code { background: var(--bg-soft); padding: 1px 5px; border-radius: 3px; }

.score { font-weight: 700; font-size: 1.05rem; min-width: 60px; text-align: right; }
.score.low { color: var(--success); }
.score.med { color: var(--warning); }
.score.high { color: var(--danger); }

.actions { display: flex; gap: 0.4rem; }
.btn-small { padding: 0.3rem 0.55rem; font-size: 0.78rem; }
.btn-pdf {
  background: var(--danger);
  color: white;
  border-color: var(--danger);
}
.btn-pdf:hover:not(:disabled) {
  background: #b91c1c;
  border-color: #b91c1c;
}

.placeholder {
  padding: 2.5rem 1rem;
  text-align: center;
  color: var(--text-muted);
  font-style: italic;
  background: var(--bg-card);
  border: 1px dashed var(--border-strong);
  border-radius: 8px;
}

@media (max-width: 700px) {
  .list li { grid-template-columns: 1fr auto; }
  .actions { grid-column: 1 / -1; justify-content: flex-end; }
}
</style>
