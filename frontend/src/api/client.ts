export interface DetectedQuestion {
  id: string
  label: string
  max_points: number
  statement: string
  cell_indices: number[]
}

export interface SolutionAnalysis {
  filename: string
  file_type: 'ipynb' | 'py'
  questions: DetectedQuestion[]
  total_max_points: number
}

export async function analyzeSolution(file: File): Promise<SolutionAnalysis> {
  const form = new FormData()
  form.append('file', file)

  const res = await fetch('/api/solution/analyze', {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? `Request failed (${res.status})`)
  }

  return res.json()
}
