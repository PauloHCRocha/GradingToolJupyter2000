/**
 * State of one interactive console (student or solution).
 *
 * When the program asks for input, the console waits for the teacher to
 * type it; submitting re-runs the program from the start with every
 * answer typed so far (see runner.py). The transcript on screen is only
 * replaced when the new run finishes, so replays don't flicker.
 */

import { computed, reactive } from 'vue'
import { runInWorker, stopRunner } from './runner'
import type { ConsoleSegment } from './runner'

export type ConsoleStatus = 'idle' | 'running' | 'waiting' | 'done' | 'error' | 'timeout' | 'stopped'

export function useRunConsole() {
  const state = reactive({
    status: 'idle' as ConsoleStatus,
    segments: [] as ConsoleSegment[],
    inputs: [] as string[],
    code: '',
    seed: 0,
    timeoutMs: 10_000,
    durationMs: 0,
  })
  // Bumped by every new run/stop/clear so a superseded run's result is dropped.
  let token = 0

  async function exec() {
    const mine = ++token
    state.status = 'running'
    const res = await runInWorker(state.code, state.inputs, state.seed, state.timeoutMs)
    if (mine !== token) return
    state.segments = res.segments
    state.durationMs = res.duration_ms
    state.status = res.status === 'needs_input' ? 'waiting' : res.status
  }

  /** Run `code` from scratch. Pass `inputs`/`seed` to replay another
   *  console's session (e.g. the solution with the student's answers). */
  function start(code: string, timeoutMs: number, inputs: string[] = [], seed?: number) {
    state.code = code
    state.timeoutMs = timeoutMs
    state.inputs = [...inputs]
    state.seed = seed ?? Math.floor(Math.random() * 2 ** 31)
    state.segments = []
    return exec()
  }

  /** Answer the pending input() — several lines answer several calls. */
  function submit(lines: string[]) {
    if (state.status !== 'waiting' || !lines.length) return
    state.inputs.push(...lines)
    // Echo right away; the re-run's transcript replaces this when it lands.
    state.segments = [...state.segments, ...lines.map((l) => ({ kind: 'in' as const, text: l + '\n' }))]
    return exec()
  }

  function stop() {
    if (state.status === 'running') stopRunner()
    else if (state.status === 'waiting') {
      token++
      state.status = 'stopped'
    }
  }

  function clear() {
    if (state.status === 'running') stopRunner()
    token++
    Object.assign(state, { status: 'idle', segments: [], inputs: [], code: '', durationMs: 0 })
  }

  /** What the program printed — prompts and typed answers left out, so two
   *  programs can be compared even when their input() messages differ. */
  const printed = computed(() =>
    state.segments
      .filter((s) => s.kind === 'out' || s.kind === 'err')
      .map((s) => s.text)
      .join('')
      .trim(),
  )

  return { state, printed, start, submit, stop, clear }
}

export type RunConsole = ReturnType<typeof useRunConsole>
