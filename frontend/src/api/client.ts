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
  enabled: boolean
}

export interface SolutionAnalysis {
  filename: string
  file_type: 'ipynb' | 'py'
  /** 'whole_file': a .py with no question markers, graded as one question. */
  detection: 'questions' | 'whole_file' | 'none'
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
  /** Whole file (.py) or all code cells joined (.ipynb) — runnable as-is. */
  source: string
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
  /** The original submission text. Never edited — see session.workingCopies. */
  source: string
}

export interface AnonymizedSubmission {
  student_id: string
  pseudonym: string
  file_type: 'ipynb' | 'py'
  text: string
  redactions: number
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
    enabled: q.enabled !== false,
  }))
  return callApi<DetectedQuestion[]>('update_questions', plain)
}

export async function uploadSubmissions(file: File): Promise<SubmissionsUploadResult> {
  const bytes = await fileBytes(file)
  return callApi<SubmissionsUploadResult>('upload_submissions', bytes)
}

/** Students' .py / .ipynb files dropped one by one instead of a zip. */
export async function uploadSubmissionFiles(files: File[]): Promise<SubmissionsUploadResult> {
  const payload = await Promise.all(files.map(async (f) => ({ name: f.name, content: await fileBytes(f) })))
  return callApi<SubmissionsUploadResult>('upload_submission_files', payload)
}

export async function clearSolution(): Promise<void> {
  await callApi('clear_solution')
}

export async function clearSubmissions(): Promise<void> {
  await callApi('clear_submissions')
}

/** Match the loaded submissions to a newly analyzed solution's questions,
 *  keeping the grades given so far. */
export async function rematchSubmissions(): Promise<StudentInfo[]> {
  return callApi<StudentInfo[]>('rematch_submissions')
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

export async function anonymizedSubmissions(
  stripComments: boolean,
  includeOutputs: boolean,
): Promise<AnonymizedSubmission[]> {
  return callApi<AnonymizedSubmission[]>('anonymized_submissions', stripComments, includeOutputs)
}

export async function anonymizedPreview(
  studentId: string,
  stripComments: boolean,
  includeOutputs: boolean,
): Promise<{ text: string; redactions: number }> {
  return callApi('anonymized_preview', studentId, stripComments, includeOutputs)
}

export async function anonymizeReference(text: string, kind: 'code' | 'text'): Promise<string> {
  return callApi<string>('anonymize_reference', text, kind)
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
  // The BOM makes Excel read the file as UTF-8 (accented names stay
  // readable); Moodle's importer strips it.
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'grades.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
