/**
 * Main-thread side of the code runner. Each run is posted to a dedicated
 * worker; if it doesn't answer within the timeout the worker is terminated
 * (the only way to stop runaway Python in wasm) and a fresh one is started
 * on the next run.
 */

import { ref } from 'vue'
import type { RunCodeResponse } from '../api/client'
import type { RunRequest } from './runner.worker'

/** True until the worker's Pyodide has finished loading at least once. */
export const runnerWarmingUp = ref(false)

let worker: Worker | null = null
let warmed = false
let nextId = 1

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

export function runInWorker(code: string, stdin = '', timeoutMs = 10_000): Promise<RunCodeResponse> {
  const w = getWorker()
  const id = nextId++
  const started = performance.now()
  // The first run also downloads/boots Pyodide in the worker — don't count
  // that against the student's code.
  const budget = warmed ? timeoutMs : timeoutMs + 60_000
  runnerWarmingUp.value = !warmed

  return new Promise((resolve) => {
    const timer = window.setTimeout(() => {
      w.removeEventListener('message', onMessage)
      killWorker()
      runnerWarmingUp.value = false
      resolve({
        success: false,
        output: '',
        error: `Stopped after ${Math.round(timeoutMs / 1000)}s — the code did not finish (infinite loop, or waiting for more input than was given?).`,
        duration_ms: Math.round(performance.now() - started),
      })
    }, budget)

    function onMessage(e: MessageEvent<{ id: number; result?: RunCodeResponse; error?: string }>) {
      if (e.data.id !== id) return
      window.clearTimeout(timer)
      w.removeEventListener('message', onMessage)
      warmed = true
      runnerWarmingUp.value = false
      resolve(
        e.data.result ?? { success: false, output: '', error: e.data.error ?? 'Unknown error', duration_ms: 0 },
      )
    }
    w.addEventListener('message', onMessage)
    w.postMessage({ id, code, stdin } satisfies RunRequest)
  })
}
