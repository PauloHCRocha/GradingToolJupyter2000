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
  question_windows: Record<string, number[]>
}

export interface CellOut {
  cell_id: string
  cell_type: string
  source: string
  output: string
}

export interface SolutionDetail {
  filename: string
  file_type: 'ipynb' | 'py'
  cells: CellOut[]
  question_windows: Record<string, number[]>
}

export interface StudentInfo {
  id: string
  name: string
  filename: string
  file_type: 'ipynb' | 'py'
  has_error: boolean
  error: string | null
  total_grade: number
  invisible_count: number
}

export interface InvisibleFinding {
  line: number
  position: number
  name: string
  unicode: string
  cell_id: string
  category?: string
}

export interface StudentDetail {
  info: StudentInfo
  cells: CellOut[]
  question_windows: Record<string, number[]>
  invisible_findings: InvisibleFinding[]
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

export interface SuggestResponse {
  points: number | null
  score: number
  confidence: 'high' | 'medium' | 'low' | 'none'
  comment: string
  max_points: number
}

export interface RunCodeResponse {
  success: boolean
  output: string
  error: string
  duration_ms: number
}

export interface SuspiciousPair {
  student1_id: string
  student1_name: string
  student2_id: string
  student2_name: string
  similarity: number
}

export interface PlagiarismAnalyzeResponse {
  threshold: number
  matrix: number[][]
  student_ids: string[]
  student_names: string[]
  suspicious_pairs: SuspiciousPair[]
  stats: {
    total_comparisons: number
    suspicious_count: number
    high_similarity_count: number
    avg_similarity: number
  }
}

export interface QuestionSimilarity {
  question_id: string
  similarity: number
  tfidf: number
  ast: number
}

export interface PlagiarismCompareResponse {
  student1_id: string
  student1_name: string
  student2_id: string
  student2_name: string
  overall_similarity: number
  questions: QuestionSimilarity[]
  code1: string
  code2: string
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

export async function getSolutionCells(): Promise<SolutionDetail> {
  const res = await fetch('/api/solution/cells')
  return jsonOrThrow<SolutionDetail>(res)
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

export async function listSubmissions(sort: 'name' | 'number' = 'name'): Promise<StudentInfo[]> {
  const res = await fetch(`/api/submissions?sort=${sort}`)
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

export async function suggestGrade(
  studentId: string,
  questionId: string,
): Promise<SuggestResponse> {
  const res = await fetch(
    `/api/suggest/${encodeURIComponent(studentId)}/${encodeURIComponent(questionId)}`,
    { method: 'POST' },
  )
  return jsonOrThrow<SuggestResponse>(res)
}

export async function runCode(code: string, stdin = ''): Promise<RunCodeResponse> {
  const res = await fetch('/api/run_code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, stdin }),
  })
  return jsonOrThrow<RunCodeResponse>(res)
}

export async function plagiarismAnalyze(
  threshold: number,
  signal?: AbortSignal,
): Promise<PlagiarismAnalyzeResponse> {
  const res = await fetch('/api/plagiarism/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ threshold }),
    signal,
  })
  return jsonOrThrow<PlagiarismAnalyzeResponse>(res)
}

export async function plagiarismCompare(
  student1_id: string,
  student2_id: string,
  signal?: AbortSignal,
): Promise<PlagiarismCompareResponse> {
  const res = await fetch('/api/plagiarism/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student1_id, student2_id }),
    signal,
  })
  return jsonOrThrow<PlagiarismCompareResponse>(res)
}

export function exportGradesUrl(): string {
  return '/api/grades/export.csv'
}
