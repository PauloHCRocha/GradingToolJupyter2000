<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { heatmapColor } from './colors'

const props = defineProps<{
  matrix: number[][]
  studentIds: string[]
  studentNames: string[]
}>()
const emit = defineEmits<{
  compare: [s1: string, s2: string]
}>()

const canvasEl = ref<HTMLCanvasElement | null>(null)
const wrapperEl = ref<HTMLDivElement | null>(null)
const hover = ref<{ i: number; j: number; cell: number } | null>(null)
const tooltip = ref<{ x: number; y: number; html: string } | null>(null)

const n = computed(() => props.matrix.length)
// Cell size scales with viewport but with sensible bounds.
const cellSize = computed(() => {
  const N = n.value || 1
  const maxWidth = wrapperEl.value?.clientWidth ?? 800
  const cap = Math.max(8, Math.min(28, Math.floor((maxWidth - 80) / N)))
  return cap
})

function draw() {
  const cv = canvasEl.value
  if (!cv) return
  const N = n.value
  const cs = cellSize.value
  const labelW = 40
  const labelH = 18
  const W = labelW + cs * N
  const H = labelH + cs * N
  // Set both backing-store and CSS size (handle high-DPI).
  const dpr = window.devicePixelRatio || 1
  cv.width = Math.floor(W * dpr)
  cv.height = Math.floor(H * dpr)
  cv.style.width = `${W}px`
  cv.style.height = `${H}px`
  const ctx = cv.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, W, H)

  // Background
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, W, H)

  // Column labels (top)
  ctx.fillStyle = '#64748b'
  ctx.font = '9px ui-monospace, monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  for (let j = 0; j < N; j++) {
    if (cs >= 12 || j % 5 === 0) {
      ctx.fillText(props.studentIds[j] ?? `${j}`, labelW + j * cs + cs / 2, labelH / 2)
    }
  }
  // Row labels (left)
  ctx.textAlign = 'right'
  for (let i = 0; i < N; i++) {
    if (cs >= 12 || i % 5 === 0) {
      ctx.fillText(props.studentIds[i] ?? `${i}`, labelW - 4, labelH + i * cs + cs / 2)
    }
  }

  // Lower-triangular cells only.
  for (let i = 0; i < N; i++) {
    for (let j = 0; j <= i; j++) {
      const v = i === j ? 1 : props.matrix[i][j]
      ctx.fillStyle = i === j ? '#e2e8f0' : heatmapColor(v)
      ctx.fillRect(labelW + j * cs, labelH + i * cs, cs - 1, cs - 1)
    }
  }

  // Hover ring
  if (hover.value) {
    const { i, j } = hover.value
    ctx.strokeStyle = '#0ea5e9'
    ctx.lineWidth = 2
    ctx.strokeRect(labelW + j * cs - 1, labelH + i * cs - 1, cs + 1, cs + 1)
  }
}

function cellAt(ev: MouseEvent): { i: number; j: number } | null {
  const cv = canvasEl.value
  if (!cv) return null
  const rect = cv.getBoundingClientRect()
  const x = ev.clientX - rect.left
  const y = ev.clientY - rect.top
  const cs = cellSize.value
  const labelW = 40
  const labelH = 18
  if (x < labelW || y < labelH) return null
  const j = Math.floor((x - labelW) / cs)
  const i = Math.floor((y - labelH) / cs)
  if (i < 0 || j < 0 || i >= n.value || j >= n.value) return null
  // Lower triangular only
  if (j > i) return null
  return { i, j }
}

function onMouseMove(ev: MouseEvent) {
  const c = cellAt(ev)
  if (!c) {
    if (hover.value) {
      hover.value = null
      tooltip.value = null
      draw()
    }
    return
  }
  if (!hover.value || hover.value.i !== c.i || hover.value.j !== c.j) {
    hover.value = { ...c, cell: cellSize.value }
    const sim = c.i === c.j ? 1 : props.matrix[c.i][c.j]
    tooltip.value = {
      x: ev.clientX,
      y: ev.clientY,
      html: `<strong>${escapeHtml(props.studentNames[c.i])}</strong> ↔ <strong>${escapeHtml(props.studentNames[c.j])}</strong><br>${(sim * 100).toFixed(1)}%`,
    }
    draw()
  } else if (tooltip.value) {
    tooltip.value.x = ev.clientX
    tooltip.value.y = ev.clientY
  }
}

function onMouseLeave() {
  hover.value = null
  tooltip.value = null
  draw()
}

function onClick(ev: MouseEvent) {
  const c = cellAt(ev)
  if (!c || c.i === c.j) return
  emit('compare', props.studentIds[c.i], props.studentIds[c.j])
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]!))
}

let resizeObserver: ResizeObserver | null = null
onMounted(() => {
  draw()
  if (wrapperEl.value && 'ResizeObserver' in window) {
    resizeObserver = new ResizeObserver(() => draw())
    resizeObserver.observe(wrapperEl.value)
  }
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  // Free canvas backing store immediately to help GC.
  if (canvasEl.value) {
    canvasEl.value.width = 0
    canvasEl.value.height = 0
  }
})
watch(() => [props.matrix, props.studentIds] as const, draw, { deep: true })
</script>

<template>
  <div class="heatmap-tab" ref="wrapperEl">
    <p class="hint">
      Click any cell to open the side-by-side comparison. Lower-triangular only —
      duplicates and the diagonal are hidden.
    </p>
    <div class="canvas-wrap">
      <canvas
        ref="canvasEl"
        @mousemove="onMouseMove"
        @mouseleave="onMouseLeave"
        @click="onClick"
      />
    </div>
    <div class="legend">
      <span>0%</span>
      <span class="bar" />
      <span>50%</span>
      <span class="bar bar2" />
      <span>100%</span>
    </div>
    <div
      v-if="tooltip"
      class="tooltip"
      :style="{ left: tooltip.x + 14 + 'px', top: tooltip.y + 14 + 'px' }"
      v-html="tooltip.html"
    />
  </div>
</template>

<style scoped>
.heatmap-tab { padding: 1rem 1.25rem 1.5rem; }
.hint { color: var(--text-muted); font-size: 0.85rem; margin: 0 0 0.6rem; }
.canvas-wrap {
  overflow: auto;
  max-height: 70vh;
  padding: 0.6rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
}
canvas { display: block; cursor: pointer; }

.legend {
  display: flex; align-items: center; gap: 0.5rem;
  margin-top: 0.7rem;
  font-size: 0.78rem;
  color: var(--text-muted);
}
.legend .bar {
  flex: 0 0 100px;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, rgb(46, 204, 113), rgb(243, 156, 18));
}
.legend .bar.bar2 {
  background: linear-gradient(to right, rgb(243, 156, 18), rgb(231, 76, 60));
}

.tooltip {
  position: fixed;
  pointer-events: none;
  background: rgba(15, 23, 42, 0.92);
  color: white;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  font-size: 0.78rem;
  line-height: 1.3;
  z-index: 100;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  max-width: 240px;
}
</style>
