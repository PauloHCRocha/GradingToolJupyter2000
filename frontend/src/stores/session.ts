import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type {
  DetectedQuestion,
  GradeOut,
  SolutionAnalysis,
  SolutionDetail,
  StudentDetail,
  StudentInfo,
} from '../api/client'
import {
  getSolutionCells,
  getStudentGrades,
  getSubmission,
  listSubmissions,
  setStudentGrade,
  updateQuestions,
} from '../api/client'

export type SortOrder = 'name' | 'number'

export const useSessionStore = defineStore('session', () => {
  const solution = ref<SolutionAnalysis | null>(null)
  const solutionDetail = ref<SolutionDetail | null>(null)
  const questions = ref<DetectedQuestion[]>([])
  const students = ref<StudentInfo[]>([])
  const warnings = ref<string[]>([])
  const sortOrder = ref<SortOrder>('name')

  const selectedStudentId = ref<string | null>(null)
  const selectedQuestionId = ref<string | null>(null)
  const studentDetail = ref<StudentDetail | null>(null)
  const studentGrades = ref<Record<string, GradeOut>>({})

  const ready = computed(() => questions.value.length > 0 && students.value.length > 0)

  // Only the questions the teacher chose to grade. Used everywhere the UI
  // displays question lists / chips / totals — the backend already filters
  // CSV export and per-question plagiarism similarity by the same flag.
  const enabledQuestions = computed(() =>
    questions.value.filter((q) => q.enabled !== false),
  )

  const currentStudent = computed(() =>
    selectedStudentId.value ? students.value.find((s) => s.id === selectedStudentId.value) : null,
  )

  const currentIndex = computed(() => {
    if (!selectedStudentId.value) return -1
    return students.value.findIndex((s) => s.id === selectedStudentId.value)
  })

  function setSolution(analysis: SolutionAnalysis) {
    solution.value = analysis
    // Default `enabled` to true if the backend ever sends a question without
    // it (defensive — avoids hiding all questions on schema mismatch).
    questions.value = analysis.questions.map((q) => ({ ...q, enabled: q.enabled !== false }))
    if (questions.value.length && !selectedQuestionId.value) {
      selectedQuestionId.value = questions.value[0].id
    }
  }

  function updateMaxPoints(id: string, max_points: number) {
    const q = questions.value.find((x) => x.id === id)
    if (q) q.max_points = max_points
  }

  function toggleQuestion(id: string, enabled: boolean) {
    const q = questions.value.find((x) => x.id === id)
    if (!q) return
    q.enabled = enabled
    // If the currently selected question got disabled, jump to the first
    // remaining enabled one (or null when none are left).
    if (!enabled && selectedQuestionId.value === id) {
      const next = enabledQuestions.value[0]
      selectedQuestionId.value = next ? next.id : null
    } else if (enabled && !selectedQuestionId.value) {
      selectedQuestionId.value = id
    }
  }

  function setAllQuestionsEnabled(enabled: boolean) {
    for (const q of questions.value) q.enabled = enabled
    if (!enabled) {
      selectedQuestionId.value = null
    } else if (!selectedQuestionId.value && questions.value.length) {
      selectedQuestionId.value = questions.value[0].id
    }
  }

  async function commitQuestions() {
    if (!questions.value.length) return
    await updateQuestions(questions.value)
  }

  function setStudents(list: StudentInfo[], warns: string[] = []) {
    students.value = list
    warnings.value = warns
    selectedStudentId.value = null
    studentDetail.value = null
    studentGrades.value = {}
  }

  async function refreshStudents() {
    students.value = await listSubmissions(sortOrder.value)
  }

  async function setSortOrder(order: SortOrder) {
    sortOrder.value = order
    await refreshStudents()
  }

  function patchStudentTotal(studentId: string, total: number) {
    const s = students.value.find((x) => x.id === studentId)
    if (s) s.total_grade = total
  }

  async function ensureSolutionDetail() {
    if (!solutionDetail.value) {
      try {
        solutionDetail.value = await getSolutionCells()
      } catch {
        solutionDetail.value = null
      }
    }
    return solutionDetail.value
  }

  async function selectStudent(studentId: string) {
    selectedStudentId.value = studentId
    studentDetail.value = null
    studentGrades.value = {}
    const [detail, grades] = await Promise.all([
      getSubmission(studentId),
      getStudentGrades(studentId),
    ])
    studentDetail.value = detail
    studentGrades.value = Object.fromEntries(grades.entries.map((e) => [e.question_id, e]))
    patchStudentTotal(studentId, grades.total)
    ensureValidSelectedQuestion()
  }

  function ensureValidSelectedQuestion() {
    const enabled = enabledQuestions.value
    const current = selectedQuestionId.value
    if (current && enabled.some((q) => q.id === current)) return
    selectedQuestionId.value = enabled[0]?.id ?? null
  }

  function selectQuestion(qid: string) {
    selectedQuestionId.value = qid
  }

  async function navigate(delta: number) {
    if (!students.value.length) return
    const valid = students.value.filter((s) => !s.has_error)
    if (!valid.length) return
    const ids = valid.map((s) => s.id)
    let pos = selectedStudentId.value ? ids.indexOf(selectedStudentId.value) : -1
    if (pos === -1) pos = 0
    else pos = (pos + delta + ids.length) % ids.length
    await selectStudent(ids[pos])
  }

  async function saveGrade(questionId: string, points: number, comment: string) {
    if (!selectedStudentId.value) return
    const result = await setStudentGrade(selectedStudentId.value, questionId, {
      points,
      comment,
    })
    studentGrades.value = Object.fromEntries(result.entries.map((e) => [e.question_id, e]))
    patchStudentTotal(selectedStudentId.value, result.total)
  }

  return {
    solution,
    solutionDetail,
    questions,
    students,
    warnings,
    sortOrder,
    selectedStudentId,
    selectedQuestionId,
    studentDetail,
    studentGrades,
    ready,
    enabledQuestions,
    currentStudent,
    currentIndex,
    setSolution,
    updateMaxPoints,
    toggleQuestion,
    setAllQuestionsEnabled,
    commitQuestions,
    setStudents,
    refreshStudents,
    setSortOrder,
    ensureSolutionDetail,
    ensureValidSelectedQuestion,
    selectStudent,
    selectQuestion,
    navigate,
    saveGrade,
  }
})
