/**
 * Main-thread side of the code runner. Runs are posted to a dedicated
 * worker one at a time; if one doesn't answer within its time limit the
 * worker is terminated (the only way to stop runaway Python in wasm) and a
 * fresh one is started for the next run.
 */

import { ref } from 'vue'
import type { RunRequest } from './runner.worker'

export interface ConsoleSegment {
  /** out: printed output · err: errors · prompt: input() prompt · in: typed answer */
  kind: 'out' | 'err' | 'prompt' | 'in'
  text: string
}

export interface RunResult {
  status: 'done' | 'error' | 'needs_input' | 'timeout' | 'stopped'
  segments: ConsoleSegment[]
  inputs_used: number
  duration_ms: number
}

/** True while the worker's Pyodide is booting for the first time. */
export const runnerWarmingUp = ref(false)

let worker: Worker | null = null
let warmed = false
let nextId = 1
let queue: Promise<unknown> = Promise.resolve()
let cancelCurrent: (() => void) | null = null

function getWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL('./runner.worker.ts', import.meta.url), { type: 'module' })
  }
  return worker
}

function killWorker() {
  worker?.terminate()
  worker = null
  warmed = false
}

function runOnce(code: string, inputs: string[], seed: number, timeoutMs: number): Promise<RunResult> {
  const w = getWorker()
  const id = nextId++
  const started = performance.now()
  // The first run also boots Pyodide in the worker — don't count that
  // against the student's code.
  const budget = warmed ? timeoutMs : timeoutMs + 60_000
  runnerWarmingUp.value = !warmed
  let partial: ConsoleSegment[] = []

  return new Promise((resolve) => {
    function finish(result: RunResult) {
      window.clearTimeout(timer)
      w.removeEventListener('message', onMessage)
      cancelCurrent = null
      runnerWarmingUp.value = false
      resolve(result)
    }
    function abandon(status: 'timeout' | 'stopped') {
      killWorker()
      finish({ status, segments: partial, inputs_used: 0, duration_ms: Math.round(performance.now() - started) })
    }
    const timer = window.setTimeout(() => abandon('timeout'), budget)
    cancelCurrent = () => abandon('stopped')

    function onMessage(e: MessageEvent<{ id: number; chunk?: string; result?: RunResult; error?: string }>) {
      if (e.data.id !== id) return
      if (e.data.chunk !== undefined) {
        partial = JSON.parse(e.data.chunk)
        return
      }
      warmed = true
      finish(
        e.data.result ?? {
          status: 'error',
          segments: [{ kind: 'err', text: e.data.error ?? 'Unknown error' }],
          inputs_used: 0,
          duration_ms: 0,
        },
      )
    }
    w.addEventListener('message', onMessage)
    w.postMessage({ id, code, inputs: [...inputs], seed } satisfies RunRequest)
  })
}

/** Runs one at a time, so each run's time limit only counts its own work. */
export function runInWorker(code: string, inputs: string[], seed: number, timeoutMs = 10_000): Promise<RunResult> {
  const result = queue.then(() => runOnce(code, inputs, seed, timeoutMs))
  queue = result.catch(() => undefined)
  return result
}

/** Kill the run in progress, if any. */
export function stopRunner() {
  cancelCurrent?.()
}
