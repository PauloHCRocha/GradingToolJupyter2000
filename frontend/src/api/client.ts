/**
 * Client API. All operations now run entirely in the browser via Pyodide.
 * No backend, no network calls for student data. The function signatures are
 * unchanged from the previous fetch-based version so callers don't notice.
 */

import { callApi } from '../runtime/pyodide'

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
  student1_index: number
  student2_id: string
  student2_name: string
  student2_index: number
  similarity: number
  cluster_id: number // -1 if not in same cluster
}

export interface ClusterInfo {
  id: number
  size: number
  avg_similarity: number
  members: number[]
  member_ids: string[]
  member_names: string[]
}

export interface PlagiarismAnalyzeResponse {
  threshold: number
  cluster_threshold: number
  matrix: number[][]
  student_ids: string[]
  student_names: string[]
  suspicious_pairs: SuspiciousPair[]
  cluster_assignments: number[]
  clusters: ClusterInfo[]
  outliers: number[]
  num_clusters: number
  stats: {
    total_comparisons: number
    suspicious_count: number
    high_similarity_count: number
    avg_similarity: number
    num_clusters: number
    largest_cluster: number
    outliers_count: number
  }
}

export interface MatchingBlock {
  id: string
  start1: number
  end1: number
  start2: number
  end2: number
  color: string
  type: 'exact' | 'similar' | 'invisible'
  size: number
}

export interface QuestionComparison {
  question_id: string
  similarity: number
  tfidf: number
  ast: number
  code1: string
  code2: string
  matching_blocks: MatchingBlock[]
}

export interface PlagiarismCompareResponse {
  student1_id: string
  student1_name: string
  student2_id: string
  student2_name: string
  overall_similarity: number
  questions: QuestionComparison[]
  code1: string
  code2: string
}

export interface ClusterPayload {
  cluster_assignments: number[]
  clusters: ClusterInfo[]
  outliers: number[]
  num_clusters: number
}

async function fileBytes(file: File): Promise<Uint8Array> {
  return new Uint8Array(await file.arrayBuffer())
}

export async function analyzeSolution(file: File): Promise<SolutionAnalysis> {
  const bytes = await fileBytes(file)
  return callApi<SolutionAnalysis>('analyze_solution', bytes, file.name)
}

export async function getSolutionCells(): Promise<SolutionDetail> {
  return callApi<SolutionDetail>('get_solution_cells')
}

export async function updateQuestions(questions: DetectedQuestion[]): Promise<DetectedQuestion[]> {
  // Strip Vue reactive proxies before sending — Pyodide expects plain objects.
  const plain = questions.map((q) => ({
    id: q.id,
    label: q.label,
    max_points: q.max_points,
    statement: q.statement,
    cell_indices: [...q.cell_indices],
  }))
  return callApi<DetectedQuestion[]>('update_questions', plain)
}

export async function uploadSubmissions(file: File): Promise<SubmissionsUploadResult> {
  const bytes = await fileBytes(file)
  return callApi<SubmissionsUploadResult>('upload_submissions', bytes)
}

export async function listSubmissions(sort: 'name' | 'number' = 'name'): Promise<StudentInfo[]> {
  return callApi<StudentInfo[]>('list_submissions', sort)
}

export async function getSubmission(studentId: string): Promise<StudentDetail> {
  return callApi<StudentDetail>('get_submission', studentId)
}

export async function getStudentGrades(studentId: string): Promise<StudentGrades> {
  return callApi<StudentGrades>('get_student_grades', studentId)
}

export async function setStudentGrade(
  studentId: string,
  questionId: string,
  payload: { points: number; comment: string },
): Promise<StudentGrades> {
  return callApi<StudentGrades>(
    'set_student_grade',
    studentId,
    questionId,
    payload.points,
    payload.comment,
  )
}

export async function suggestGrade(
  studentId: string,
  questionId: string,
): Promise<SuggestResponse> {
  return callApi<SuggestResponse>('suggest', studentId, questionId)
}

export async function runCode(code: string, stdin = ''): Promise<RunCodeResponse> {
  return callApi<RunCodeResponse>('run_code', code, stdin)
}

export async function plagiarismAnalyze(
  threshold: number,
  clusterThreshold = 0.7,
  _signal?: AbortSignal,
): Promise<PlagiarismAnalyzeResponse> {
  // Note: Pyodide work runs synchronously inside the wasm runtime; we cannot
  // truly abort once it's started. The signal is accepted so callers don't
  // need to change.
  return callApi<PlagiarismAnalyzeResponse>('plagiarism_analyze', threshold, clusterThreshold)
}

export async function plagiarismCluster(threshold: number): Promise<ClusterPayload> {
  return callApi<ClusterPayload>('plagiarism_cluster', threshold)
}

export async function plagiarismCompare(
  student1_id: string,
  student2_id: string,
  _signal?: AbortSignal,
): Promise<PlagiarismCompareResponse> {
  return callApi<PlagiarismCompareResponse>('plagiarism_compare', student1_id, student2_id)
}

export async function downloadGradesCsv(): Promise<void> {
  const csv = await callApi<string>('export_grades_csv')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'grades.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
