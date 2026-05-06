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

  const currentStudent = computed(() =>
    selectedStudentId.value ? students.value.find((s) => s.id === selectedStudentId.value) : null,
  )

  const currentIndex = computed(() => {
    if (!selectedStudentId.value) return -1
    return students.value.findIndex((s) => s.id === selectedStudentId.value)
  })

  function setSolution(analysis: SolutionAnalysis) {
    solution.value = analysis
    questions.value = analysis.questions.map((q) => ({ ...q }))
    if (questions.value.length && !selectedQuestionId.value) {
      selectedQuestionId.value = questions.value[0].id
    }
  }

  function updateMaxPoints(id: string, max_points: number) {
    const q = questions.value.find((x) => x.id === id)
    if (q) q.max_points = max_points
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
    if (!selectedQuestionId.value && questions.value.length) {
      selectedQuestionId.value = questions.value[0].id
    }
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
    currentStudent,
    currentIndex,
    setSolution,
    updateMaxPoints,
    commitQuestions,
    setStudents,
    refreshStudents,
    setSortOrder,
    ensureSolutionDetail,
    selectStudent,
    selectQuestion,
    navigate,
    saveGrade,
  }
})
