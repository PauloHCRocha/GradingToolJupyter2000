import { defineStore } from 'pinia'
import { computed, reactive, ref, watch } from 'vue'
import { anonymizedSubmissions, anonymizeReference } from '../api/client'
import type { AnonymizedSubmission } from '../api/client'
import type { ClaudeSettings, GradingOutput, RubricQuestion } from '../runtime/claude'
import { estimateCost } from '../runtime/claudePricing'
import type { ClaudeModel, Effort, Usage } from '../runtime/claudePricing'
import { useSessionStore } from './session'

export interface RubricCriterion {
  id: string
  description: string
  points: number
}

export interface Proposal {
  solution: string
  criteria: RubricCriterion[]
  notes: string
}

/** pending → the teacher hasn't looked yet; accepted → saved as Claude
 *  proposed; overridden → saved with the teacher's own points; rejected →
 *  dismissed, nothing saved. */
export type ReviewStatus = 'pending' | 'accepted' | 'overridden' | 'rejected'

export interface AiCriterion {
  id: string
  description: string
  max: number
  points: number
  justification: string
}

export interface AiQuestionResult {
  questionId: string
  criteria: AiCriterion[]
  points: number
  maxPoints: number
  feedback: string
  confidence: 'high' | 'medium' | 'low'
  review: ReviewStatus
}

export interface AiStudentResult {
  status: 'queued' | 'running' | 'done' | 'error'
  /** Random label shown in the UI; never sent to the API. */
  pseudonym: string
  error?: string
  questions: Record<string, AiQuestionResult>
  flags: string[]
  /** The rubric this result was graded against — see `rubricKey`. */
  rubricKey: string
}

interface Settings {
  model: ClaudeModel
  effort: Effort
  language: string
  stripComments: boolean
  includeOutputs: boolean
  concurrency: number
}

const KEY_STORAGE = 'granymede.claudeApiKey'
const SETTINGS_STORAGE = 'granymede.autogradeSettings'

// Browser storage can be missing or throw (private mode, blocked site data).
function readStorage(storage: () => Storage, key: string): string | null {
  try {
    return storage().getItem(key)
  } catch {
    return null
  }
}
function writeStorage(storage: () => Storage, key: string, value: string | null) {
  try {
    if (value === null) storage().removeItem(key)
    else storage().setItem(key, value)
  } catch {
    /* ignore */
  }
}

// The SDK is only downloaded the first time Claude is actually called.
const loadClaude = () => import('../runtime/claude')

async function errorText(e: unknown): Promise<string> {
  try {
    return (await loadClaude()).describeError(e)
  } catch {
    return e instanceof Error ? e.message : String(e)
  }
}

const round025 = (x: number) => Math.round(x * 4) / 4
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0)

export const useAutogradeStore = defineStore('autograde', () => {
  const session = useSessionStore()

  // --- connection & settings -------------------------------------------
  // The key lives in sessionStorage (gone when the tab closes) unless the
  // teacher ticks "remember on this device".
  const rememberKey = ref(readStorage(() => localStorage, KEY_STORAGE) !== null)
  const apiKey = ref(
    readStorage(() => localStorage, KEY_STORAGE) ?? readStorage(() => sessionStorage, KEY_STORAGE) ?? '',
  )
  watch([apiKey, rememberKey], ([key, remember]) => {
    writeStorage(() => sessionStorage, KEY_STORAGE, key || null)
    writeStorage(() => localStorage, KEY_STORAGE, remember && key ? key : null)
  })

  const defaults: Settings = {
    model: 'claude-opus-5-5',
    effort: 'high',
    language: 'Português (Portugal)',
    stripComments: false,
    includeOutputs: false,
    concurrency: 3,
  }
  let saved: Partial<Settings> = {}
  try {
    saved = JSON.parse(readStorage(() => localStorage, SETTINGS_STORAGE) ?? '{}')
  } catch {
    saved = {}
  }
  const settings = reactive<Settings>({ ...defaults, ...saved })
  watch(settings, (s) => writeStorage(() => localStorage, SETTINGS_STORAGE, JSON.stringify(s)), { deep: true })

  const claudeSettings = computed<ClaudeSettings>(() => ({
    apiKey: apiKey.value.trim(),
    model: settings.model,
    effort: settings.effort,
    language: settings.language.trim() || defaults.language,
  }))

  // --- usage -------------------------------------------------------------
  const usage = reactive<Usage>({
    input_tokens: 0,
    output_tokens: 0,
    cache_read_input_tokens: 0,
    cache_creation_input_tokens: 0,
  })
  function addUsage(u: Usage) {
    usage.input_tokens += u.input_tokens
    usage.output_tokens += u.output_tokens
    usage.cache_read_input_tokens += u.cache_read_input_tokens
    usage.cache_creation_input_tokens += u.cache_creation_input_tokens
  }
  const estimatedCost = computed(() => estimateCost(settings.model, usage))

  // --- proposals (solution + rubric per question) -------------------------
  const proposals = ref<Record<string, Proposal>>({})
  const proposalLoading = ref<Record<string, boolean>>({})
  const proposalErrors = ref<Record<string, string>>({})

  function questionById(qid: string) {
    return session.questions.find((q) => q.id === qid)
  }

  function referenceCode(qid: string): string {
    const sd = session.solutionDetail
    if (!sd) return ''
    return (sd.question_windows[qid] ?? [])
      .map((i) => sd.cells[i])
      .filter((c) => c && c.cell_type === 'code')
      .map((c) => c.source)
      .join('\n\n')
  }

  function nextCriterionId(qid: string): string {
    const used = (proposals.value[qid]?.criteria ?? []).map((c) => Number(c.id.split('.c')[1]) || 0)
    return `${qid}.c${Math.max(0, ...used) + 1}`
  }

  function ensureProposal(qid: string): Proposal {
    if (!proposals.value[qid]) proposals.value[qid] = { solution: referenceCode(qid), criteria: [], notes: '' }
    return proposals.value[qid]
  }

  function addCriterion(qid: string) {
    const p = ensureProposal(qid)
    p.criteria.push({ id: nextCriterionId(qid), description: '', points: 0 })
  }

  function removeCriterion(qid: string, id: string) {
    const p = proposals.value[qid]
    if (p) p.criteria = p.criteria.filter((c) => c.id !== id)
  }

  /** Why this question can't be auto-graded yet, or null when it can. */
  function proposalIssue(qid: string): string | null {
    const q = questionById(qid)
    const p = proposals.value[qid]
    if (!q) return 'Unknown question'
    if (!p || !p.criteria.length) return 'No rubric yet'
    if (p.criteria.some((c) => !c.description.trim())) return 'A criterion has no description'
    const total = Math.round(sum(p.criteria.map((c) => Number(c.points) || 0)) * 100) / 100
    const max = Number(q.max_points) || 0
    if (Math.abs(total - max) > 1e-6) return `Criteria add up to ${total}, the question is worth ${max}`
    return null
  }

  const allProposalsReady = computed(
    () => session.enabledQuestions.length > 0 && session.enabledQuestions.every((q) => !proposalIssue(q.id)),
  )

  async function generateProposal(qid: string) {
    const q = questionById(qid)
    if (!q) return
    proposalLoading.value[qid] = true
    delete proposalErrors.value[qid]
    try {
      const { proposeSolutionAndRubric } = await loadClaude()
      await session.ensureSolutionDetail()
      const others = session.enabledQuestions.filter((x) => x.id !== qid)
      // Teacher material goes through the same scrubber as student work.
      const [statement, code, ...otherStatements] = await Promise.all([
        anonymizeReference(q.statement, 'text'),
        anonymizeReference(referenceCode(qid), 'code'),
        ...others.map((x) => anonymizeReference(x.statement, 'text')),
      ])
      const { data, usage: u } = await proposeSolutionAndRubric(claudeSettings.value, {
        questionId: qid,
        statement,
        maxPoints: Number(q.max_points) || 0,
        referenceCode: code,
        otherQuestions: others.map((x, i) => ({ id: x.id, statement: otherStatements[i] })),
      })
      addUsage(u)
      proposals.value[qid] = {
        solution: data.solution,
        criteria: data.criteria.map((c, i) => ({
          id: `${qid}.c${i + 1}`,
          description: c.description,
          points: round025(Number(c.points) || 0),
        })),
        notes: data.notes,
      }
    } catch (e) {
      proposalErrors.value[qid] = await errorText(e)
    } finally {
      proposalLoading.value[qid] = false
    }
  }

  async function generateMissingProposals() {
    const todo = session.enabledQuestions.filter((q) => !proposals.value[q.id]?.criteria.length)
    await Promise.all(todo.map((q) => generateProposal(q.id)))
  }

  /** Changes whenever anything the grader sees about the assignment changes,
   *  so results graded against an older rubric can be flagged as stale. */
  const rubricKey = computed(() =>
    JSON.stringify(
      session.enabledQuestions.map((q) => [q.id, q.max_points, proposals.value[q.id] ?? null]),
    ),
  )

  // --- grading -----------------------------------------------------------
  const results = ref<Record<string, AiStudentResult>>({})
  const running = ref(false)
  const runError = ref<string | null>(null)
  let abort: AbortController | null = null

  function mapResult(
    payload: AnonymizedSubmission,
    data: GradingOutput,
    key: string,
  ): AiStudentResult {
    const questions: Record<string, AiQuestionResult> = {}
    for (const q of session.enabledQuestions) {
      const rubric = proposals.value[q.id]?.criteria ?? []
      const out = data.questions.find((x) => x.question_id === q.id)
      // Points come from our rubric, clamped per criterion — the model's
      // arithmetic is never trusted for the total.
      const criteria = rubric.map((c) => {
        const r = out?.criteria.find((x) => x.criterion_id === c.id)
        return {
          id: c.id,
          description: c.description,
          max: c.points,
          points: Math.min(c.points, Math.max(0, round025(Number(r?.points) || 0))),
          justification: r?.justification ?? 'Not graded by Claude.',
        }
      })
      questions[q.id] = {
        questionId: q.id,
        criteria,
        points: round025(sum(criteria.map((c) => c.points))),
        maxPoints: Number(q.max_points) || 0,
        feedback: out?.feedback ?? '',
        confidence: out ? out.confidence : 'low',
        review: 'pending',
      }
    }
    return { status: 'done', pseudonym: payload.pseudonym, questions, flags: data.integrity_flags ?? [], rubricKey: key }
  }

  /** mode 'all' re-grades everyone; 'missing' skips students already graded
   *  against the current rubric. */
  async function runGrading(mode: 'all' | 'missing') {
    if (running.value) return
    runError.value = null
    if (!claudeSettings.value.apiKey) {
      runError.value = 'Add your Claude API key first.'
      return
    }
    if (!allProposalsReady.value) {
      runError.value = 'Every question needs a rubric that adds up to its points.'
      return
    }
    running.value = true
    abort = new AbortController()
    const signal = abort.signal
    const key = rubricKey.value
    try {
      const { describeError, gradeSubmission, gradingSchema, gradingSystem } = await loadClaude()
      const qs = session.enabledQuestions
      const scrubbed = await Promise.all(
        qs.flatMap((q) => [
          anonymizeReference(q.statement, 'text'),
          anonymizeReference(proposals.value[q.id].solution, 'code'),
        ]),
      )
      const rubric: RubricQuestion[] = qs.map((q, i) => ({
        id: q.id,
        statement: scrubbed[2 * i],
        maxPoints: Number(q.max_points) || 0,
        solution: scrubbed[2 * i + 1],
        criteria: proposals.value[q.id].criteria.map((c) => ({ ...c, points: Number(c.points) || 0 })),
      }))
      const system = gradingSystem(rubric, claudeSettings.value.language)
      const schema = gradingSchema(rubric)
      const qids = qs.map((q) => q.id)

      let payloads = await anonymizedSubmissions(settings.stripComments, settings.includeOutputs)
      if (mode === 'missing') {
        payloads = payloads.filter((p) => {
          const r = results.value[p.student_id]
          return !(r && r.status === 'done' && r.rubricKey === key)
        })
      }
      for (const p of payloads) {
        results.value[p.student_id] = { status: 'queued', pseudonym: p.pseudonym, questions: {}, flags: [], rubricKey: key }
      }

      const queue = [...payloads]
      const workers = Array.from({ length: Math.max(1, Math.min(8, settings.concurrency)) }, async () => {
        while (queue.length && !signal.aborted) {
          const p = queue.shift()!
          results.value[p.student_id].status = 'running'
          try {
            const { data, usage: u } = await gradeSubmission(
              claudeSettings.value,
              system,
              schema,
              qids,
              { text: p.text, file_type: p.file_type },
              signal,
            )
            addUsage(u)
            results.value[p.student_id] = mapResult(p, data, key)
          } catch (e) {
            results.value[p.student_id] = {
              ...results.value[p.student_id],
              status: 'error',
              error: describeError(e),
            }
          }
        }
      })
      await Promise.all(workers)
      // Stopped before their turn came: forget them rather than show "queued".
      for (const p of queue) delete results.value[p.student_id]
    } catch (e) {
      runError.value = await errorText(e)
    } finally {
      running.value = false
      abort = null
    }
  }

  function stop() {
    abort?.abort()
  }

  // --- review ------------------------------------------------------------
  function resultFor(studentId: string | null, qid: string | null): AiQuestionResult | null {
    if (!studentId || !qid) return null
    const r = results.value[studentId]
    return r?.status === 'done' ? (r.questions[qid] ?? null) : null
  }

  async function accept(studentId: string, qid: string, points?: number, comment?: string) {
    const r = resultFor(studentId, qid)
    if (!r) return
    const finalPoints = points ?? r.points
    await session.saveGradeFor(studentId, qid, finalPoints, comment ?? r.feedback)
    r.review = finalPoints === r.points ? 'accepted' : 'overridden'
  }

  function reject(studentId: string, qid: string) {
    const r = resultFor(studentId, qid)
    if (r) r.review = 'rejected'
  }

  /** The teacher saved a grade by hand — record it as their review. */
  function noteManualGrade(studentId: string, qid: string, points: number) {
    const r = resultFor(studentId, qid)
    if (r) r.review = points === r.points ? 'accepted' : 'overridden'
  }

  async function acceptAll(onlyHighConfidence: boolean) {
    for (const [studentId, r] of Object.entries(results.value)) {
      if (r.status !== 'done') continue
      for (const q of Object.values(r.questions)) {
        if (q.review !== 'pending') continue
        if (onlyHighConfidence && q.confidence !== 'high') continue
        if (!session.enabledQuestions.some((x) => x.id === q.questionId)) continue
        await accept(studentId, q.questionId)
      }
    }
  }

  const pendingCount = computed(() =>
    Object.values(results.value).reduce(
      (n, r) => n + Object.values(r.questions).filter((q) => q.review === 'pending').length,
      0,
    ),
  )

  // A new solution or a new set of students invalidates everything here.
  watch(
    () => session.solution,
    () => {
      proposals.value = {}
      results.value = {}
    },
  )
  watch(
    () => [...session.students.map((s) => s.id)].sort().join('|'),
    () => {
      results.value = {}
    },
  )

  return {
    apiKey,
    rememberKey,
    settings,
    usage,
    estimatedCost,
    proposals,
    proposalLoading,
    proposalErrors,
    referenceCode,
    ensureProposal,
    addCriterion,
    removeCriterion,
    proposalIssue,
    allProposalsReady,
    generateProposal,
    generateMissingProposals,
    rubricKey,
    results,
    running,
    runError,
    runGrading,
    stop,
    resultFor,
    accept,
    reject,
    noteManualGrade,
    acceptAll,
    pendingCount,
  }
})
