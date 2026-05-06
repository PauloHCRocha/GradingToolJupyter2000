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

export interface StudentInfo {
  id: string
  name: string
  filename: string
  file_type: 'ipynb' | 'py'
  has_error: boolean
  error: string | null
  total_grade: number
}

export interface CellOut {
  cell_id: string
  cell_type: string
  source: string
  output: string
}

export interface StudentDetail {
  info: StudentInfo
  cells: CellOut[]
}

export interface SubmissionsUploadResult {
  students: StudentInfo[]
  warnings: string[]
}

export interface GradeOut {
  question_id: string
  points: number
  comment: string
}

export interface StudentGrades {
  student_id: string
  entries: GradeOut[]
  total: number
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export async function analyzeSolution(file: File): Promise<SolutionAnalysis> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/solution/analyze', { method: 'POST', body: form })
  return jsonOrThrow<SolutionAnalysis>(res)
}

export async function updateQuestions(questions: DetectedQuestion[]): Promise<DetectedQuestion[]> {
  const res = await fetch('/api/solution/questions', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(questions),
  })
  return jsonOrThrow<DetectedQuestion[]>(res)
}

export async function uploadSubmissions(file: File): Promise<SubmissionsUploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/submissions/upload', { method: 'POST', body: form })
  return jsonOrThrow<SubmissionsUploadResult>(res)
}

export async function listSubmissions(): Promise<StudentInfo[]> {
  const res = await fetch('/api/submissions')
  return jsonOrThrow<StudentInfo[]>(res)
}

export async function getSubmission(studentId: string): Promise<StudentDetail> {
  const res = await fetch(`/api/submissions/${encodeURIComponent(studentId)}`)
  return jsonOrThrow<StudentDetail>(res)
}

export async function getStudentGrades(studentId: string): Promise<StudentGrades> {
  const res = await fetch(`/api/grades/${encodeURIComponent(studentId)}`)
  return jsonOrThrow<StudentGrades>(res)
}

export async function setStudentGrade(
  studentId: string,
  questionId: string,
  payload: { points: number; comment: string },
): Promise<StudentGrades> {
  const res = await fetch(
    `/api/grades/${encodeURIComponent(studentId)}/${encodeURIComponent(questionId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
  return jsonOrThrow<StudentGrades>(res)
}

export function exportGradesUrl(): string {
  return '/api/grades/export.csv'
}
