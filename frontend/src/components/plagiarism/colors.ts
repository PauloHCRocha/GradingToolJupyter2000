// 15-colour palette for cluster-coded UI (matrix borders, network nodes,
// cluster card accents). Indexed by cluster_id; -1 means "no cluster".
export const CLUSTER_PALETTE = [
  '#ef4444', '#f59e0b', '#eab308', '#22c55e', '#10b981',
  '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7',
  '#d946ef', '#ec4899', '#f43f5e', '#84cc16', '#14b8a6',
] as const

export const NO_CLUSTER_COLOR = '#94a3b8'

export function clusterColor(clusterId: number): string {
  if (clusterId < 0) return NO_CLUSTER_COLOR
  return CLUSTER_PALETTE[clusterId % CLUSTER_PALETTE.length]
}

// Heatmap gradient: green (0) → yellow (midpoint) → red (1).
// `midpoint` shifts where yellow sits — moving it down makes more of the
// scale orange/red (high contrast for low-similarity datasets), moving
// it up keeps colours green for longer (only the very high values pop).
export function heatmapColor(value: number, midpoint = 0.5): string {
  const v = Math.max(0, Math.min(1, value))
  const m = Math.max(0.05, Math.min(0.95, midpoint))
  if (v < m) {
    const t = v / m
    const r = Math.round(46 + (243 - 46) * t)
    const g = Math.round(204 + (156 - 204) * t)
    const b = Math.round(113 + (18 - 113) * t)
    return `rgb(${r}, ${g}, ${b})`
  }
  const t = (v - m) / (1 - m)
  const r = Math.round(243 + (231 - 243) * t)
  const g = Math.round(156 + (76 - 156) * t)
  const b = Math.round(18 + (60 - 18) * t)
  return `rgb(${r}, ${g}, ${b})`
}

export function severityClass(sim: number): 'low' | 'med' | 'high' {
  if (sim >= 0.95) return 'high'
  if (sim >= 0.85) return 'med'
  return 'low'
}
