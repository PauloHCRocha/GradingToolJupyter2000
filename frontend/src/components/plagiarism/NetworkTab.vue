<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Network, type Options } from 'vis-network'
import { DataSet } from 'vis-data'
import type { ClusterInfo, SuspiciousPair } from '../../api/client'
import { heatmapColor, NO_CLUSTER_COLOR } from './colors'
import { theme } from '../../runtime/theme'

const props = defineProps<{
  studentIds: string[]
  studentNames: string[]
  pairs: SuspiciousPair[]
  clusterAssignments: number[]
  clusters: ClusterInfo[]
}>()

// cluster_id → severity colour (same scale as the heatmap).
const clusterColorMap = computed<Record<number, string>>(() => {
  const map: Record<number, string> = {}
  for (const c of props.clusters) map[c.id] = heatmapColor(c.avg_similarity)
  return map
})
const emit = defineEmits<{
  compare: [s1: string, s2: string]
}>()

const containerEl = ref<HTMLDivElement | null>(null)
const empty = ref(false)

let network: Network | null = null
let nodes: DataSet<{ id: string; label: string; color: { background: string; border: string }; font: object }> | null = null
let edges: DataSet<{ id: string; from: string; to: string; color: string; width: number; title: string }> | null = null

function build() {
  // Free any prior instance before building a fresh one.
  destroyNetwork()
  if (!containerEl.value) return

  const { studentIds, studentNames, pairs, clusterAssignments } = props
  if (!pairs.length) {
    empty.value = true
    return
  }
  empty.value = false

  // Only include students who appear in at least one suspicious pair.
  const involved = new Set<string>()
  for (const p of pairs) {
    involved.add(p.student1_id)
    involved.add(p.student2_id)
  }
  const indexById: Record<string, number> = {}
  studentIds.forEach((id, i) => (indexById[id] = i))

  // vis-network draws labels next to (or under) the node, so the colour
  // has to read against the *page* background, not the node — and an
  // outline ("stroke") keeps it legible against any cluster colour.
  const dark = theme.value === 'dark'
  const labelFont = {
    color: dark ? '#f3f4f6' : '#111827',
    size: 13,
    face: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    strokeWidth: 3,
    strokeColor: dark ? '#0f1419' : '#ffffff',
  }

  const nodeData = Array.from(involved).map((id) => {
    const i = indexById[id]
    const cId = clusterAssignments[i] ?? -1
    const c = cId >= 0 ? clusterColorMap.value[cId] ?? NO_CLUSTER_COLOR : NO_CLUSTER_COLOR
    return {
      id,
      label: studentNames[i] ?? id,
      color: { background: c, border: shade(c, -0.18) },
      font: labelFont,
    }
  })
  const edgeData = pairs.map((p, idx) => ({
    id: `e${idx}`,
    from: p.student1_id,
    to: p.student2_id,
    color: p.similarity >= 0.95 ? '#dc2626' : '#f59e0b',
    width: Math.max(1.2, Math.min(6, p.similarity * 6)),
    title: `${p.student1_name} ↔ ${p.student2_name}: ${(p.similarity * 100).toFixed(1)}%`,
  }))

  nodes = new DataSet(nodeData)
  edges = new DataSet(edgeData)

  const options: Options = {
    autoResize: true,
    nodes: {
      shape: 'dot',
      size: 18,
      borderWidth: 2,
      shadow: false,
    },
    edges: {
      smooth: { enabled: true, type: 'continuous', roundness: 0.4 },
      selectionWidth: 1.5,
    },
    physics: {
      enabled: true,
      barnesHut: {
        gravitationalConstant: -2400,
        centralGravity: 0.3,
        springLength: 110,
        springConstant: 0.04,
        damping: 0.5,
      },
      stabilization: { iterations: 200 },
    },
    interaction: { hover: true, tooltipDelay: 120 },
  }

  network = new Network(containerEl.value, { nodes, edges }, options)
  network.on('doubleClick', (params) => {
    if (params.nodes.length === 2) {
      emit('compare', params.nodes[0] as string, params.nodes[1] as string)
    } else if (params.edges.length === 1) {
      const eId = params.edges[0] as string
      const e = edges?.get(eId)
      if (e && !Array.isArray(e)) emit('compare', e.from, e.to)
    }
  })
  network.on('selectEdge', (params) => {
    if (params.edges.length === 1) {
      const e = edges?.get(params.edges[0] as string)
      if (e && !Array.isArray(e)) emit('compare', e.from, e.to)
    }
  })
}

function destroyNetwork() {
  if (network) {
    network.destroy()
    network = null
  }
  if (nodes) {
    nodes.clear()
    nodes = null
  }
  if (edges) {
    edges.clear()
    edges = null
  }
}

// Rebuild whenever the inputs change. Theme changes also force a
// rebuild so the label colour / stroke updates without a manual refresh.
watch(
  () => [props.pairs, props.studentIds, props.clusterAssignments, props.clusters, theme.value] as const,
  build,
  { deep: true },
)

onMounted(build)
onBeforeUnmount(destroyNetwork)

// Tiny helper: shade a colour toward black/white by a -1..1 amount.
// Accepts both #rrggbb and rgb(r, g, b).
function shade(input: string, percent: number): string {
  let r = 0, g = 0, b = 0
  const hex = input.startsWith('#') ? input.slice(1).match(/.{2}/g) : null
  if (hex) {
    [r, g, b] = hex.map((s) => parseInt(s, 16))
  } else {
    const m = input.match(/^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/)
    if (m) { r = +m[1]; g = +m[2]; b = +m[3] }
    else return input
  }
  const adj = (c: number) => {
    const t = percent < 0 ? 0 : 255
    const p = Math.abs(percent)
    return Math.round((t - c) * p + c)
  }
  return `rgb(${adj(r)}, ${adj(g)}, ${adj(b)})`
}
</script>

<template>
  <div class="network-tab">
    <p class="hint">
      Nodes are coloured by cluster, edges by severity (orange ≥ threshold,
      red ≥ 95%). <strong>Double-click an edge or two nodes</strong> to compare.
    </p>
    <div v-if="empty" class="placeholder">
      No suspicious pairs above the threshold to graph.
    </div>
    <div v-show="!empty" ref="containerEl" class="network-container" />
  </div>
</template>

<style scoped>
.network-tab { padding: 1rem 1.25rem 1.5rem; }
.hint { color: var(--text-muted); font-size: 0.85rem; margin: 0 0 0.6rem; }
.network-container {
  height: 70vh;
  min-height: 480px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.placeholder {
  padding: 4rem 1rem;
  text-align: center;
  color: var(--text-muted);
  font-style: italic;
  background: var(--bg-card);
  border: 1px dashed var(--border-strong);
  border-radius: 8px;
}
</style>
