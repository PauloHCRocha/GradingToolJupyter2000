<script setup lang="ts">
import { computed } from 'vue'
import type { ClusterInfo } from '../../api/client'
import { heatmapColor } from './colors'

const props = defineProps<{
  clusters: ClusterInfo[]
  outliersCount: number
  totalStudents: number
}>()
const emit = defineEmits<{
  compare: [s1: string, s2: string]
  compareAll: [memberIds: string[]]
}>()

// Sort by severity (most-similar clusters first) — same colour ramp as the
// heatmap, so a cluster with avg_similarity 0.95 is red and 0.55 is yellow.
const sortedClusters = computed(() =>
  [...props.clusters].sort((a, b) => b.avg_similarity - a.avg_similarity || b.size - a.size),
)

function severityFor(c: ClusterInfo): string {
  return heatmapColor(c.avg_similarity)
}

function rgba(rgb: string, alpha: number): string {
  // Accept either #rrggbb or rgb(r, g, b).
  const hex = rgb.startsWith('#') ? rgb.slice(1).match(/.{2}/g) : null
  if (hex) {
    const [r, g, b] = hex.map((s) => parseInt(s, 16))
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }
  const m = rgb.match(/^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/)
  if (m) return `rgba(${m[1]}, ${m[2]}, ${m[3]}, ${alpha})`
  return rgb
}

function pickPair(cluster: ClusterInfo, idx: number) {
  // Click a member pill → compare with the next member in the cluster.
  const ids = cluster.member_ids
  if (ids.length < 2) return
  const next = (idx + 1) % ids.length
  emit('compare', ids[idx], ids[next])
}
</script>

<template>
  <div class="clusters-tab">
    <p class="hint">
      Density-based clustering on the similarity matrix. Click any member to
      compare with the next in the cluster, or "Compare all" to walk through.
    </p>

    <div v-if="!clusters.length" class="placeholder">
      No clusters detected at this threshold — try lowering it.
    </div>

    <div v-else class="grid">
      <article
        v-for="c in sortedClusters"
        :key="c.id"
        class="cluster"
        :style="{
          borderLeftColor: severityFor(c),
          background: `linear-gradient(135deg, ${rgba(severityFor(c), 0.08)}, ${rgba(severityFor(c), 0.02)})`,
        }"
      >
        <header>
          <div>
            <h3>Cluster #{{ c.id + 1 }}</h3>
            <p class="meta">
              <strong>{{ c.size }}</strong> students ·
              avg similarity
              <strong :style="{ color: severityFor(c) }">{{ Math.round(c.avg_similarity * 100) }}%</strong>
            </p>
          </div>
          <button
            class="btn btn-primary"
            :disabled="c.size < 2"
            @click="emit('compareAll', c.member_ids)"
          >Compare all</button>
        </header>
        <ul class="members">
          <li
            v-for="(name, i) in c.member_names"
            :key="c.member_ids[i]"
            :style="{ borderColor: severityFor(c) }"
            tabindex="0"
            @click="pickPair(c, i)"
            @keydown.enter="pickPair(c, i)"
          >
            <strong>{{ name }}</strong>
            <span class="num">#{{ c.member_ids[i] }}</span>
          </li>
        </ul>
      </article>
    </div>

    <p class="footer">
      <strong>{{ outliersCount }}</strong> independent students (no cluster) ·
      total {{ totalStudents }}
    </p>
  </div>
</template>

<style scoped>
.clusters-tab { padding: 1rem 1.25rem 1.5rem; }
.hint { color: var(--text-muted); font-size: 0.85rem; margin: 0 0 0.8rem; }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 0.85rem;
}
.cluster {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 4px solid;
  border-radius: 10px;
  padding: 0.85rem 1rem 0.95rem;
}
.cluster header {
  display: flex; justify-content: space-between; align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.7rem;
}
.cluster h3 { margin: 0 0 0.15rem; font-size: 1rem; color: var(--text-strong); }
.cluster .meta { margin: 0; color: var(--text-muted); font-size: 0.85rem; }

.members {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.members li {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.6rem;
  border: 1px solid;
  border-radius: 999px;
  background: var(--bg-card);
  font-size: 0.85rem;
  cursor: pointer;
  transition: transform 0.1s, background 0.1s;
}
.members li:hover, .members li:focus {
  background: var(--bg-soft);
  transform: translateY(-1px);
  outline: none;
}
.members li .num {
  color: var(--text-muted);
  font-family: ui-monospace, monospace;
  font-size: 0.78rem;
}

.placeholder {
  padding: 3rem 1rem;
  text-align: center;
  color: var(--text-muted);
  font-style: italic;
  background: var(--bg-card);
  border: 1px dashed var(--border-strong);
  border-radius: 8px;
}
.footer { margin-top: 1rem; color: var(--text-muted); font-size: 0.85rem; }
.btn-primary { padding: 0.35rem 0.7rem; font-size: 0.82rem; }
</style>
