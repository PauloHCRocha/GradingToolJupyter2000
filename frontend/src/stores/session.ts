import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type {
  DetectedQuestion,
  GradeOut,
  SolutionAnalysis,
  StudentDetail,
  StudentInfo,
} from '../api/client'
import {
  getStudentGrades,
  getSubmission,
  setStudentGrade,
  updateQuestions,
} from '../api/client'

export const useSessionStore = defineStore('session', () => {
  const solution = ref<SolutionAnalysis | null>(null)
  const questions = ref<DetectedQuestion[]>([])
  const students = ref<StudentInfo[]>([])
  const warnings = ref<string[]>([])
  const selectedStudentId = ref<string | null>(null)
  const studentDetail = ref<StudentDetail | null>(null)
  const studentGrades = ref<Record<string, GradeOut>>({})

  const ready = computed(() => questions.value.length > 0 && students.value.length > 0)

  function setSolution(analysis: SolutionAnalysis) {
    solution.value = analysis
    questions.value = analysis.questions.map((q) => ({ ...q }))
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

  function patchStudentTotal(studentId: string, total: number) {
    const s = students.value.find((x) => x.id === studentId)
    if (s) s.total_grade = total
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
    questions,
    students,
    warnings,
    selectedStudentId,
    studentDetail,
    studentGrades,
    ready,
    setSolution,
    updateMaxPoints,
    commitQuestions,
    setStudents,
    selectStudent,
    saveGrade,
  }
})
