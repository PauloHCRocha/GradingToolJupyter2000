import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SolutionAnalysis, DetectedQuestion } from '../api/client'

export const useSessionStore = defineStore('session', () => {
  const solution = ref<SolutionAnalysis | null>(null)
  const questions = ref<DetectedQuestion[]>([])

  function setSolution(analysis: SolutionAnalysis) {
    solution.value = analysis
    questions.value = analysis.questions.map((q) => ({ ...q }))
  }

  function updateMaxPoints(id: string, max_points: number) {
    const q = questions.value.find((x) => x.id === id)
    if (q) q.max_points = max_points
  }

  function reset() {
    solution.value = null
    questions.value = []
  }

  return { solution, questions, setSolution, updateMaxPoints, reset }
})
