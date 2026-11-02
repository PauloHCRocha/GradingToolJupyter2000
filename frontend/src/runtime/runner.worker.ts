/**
 * Dedicated Pyodide instance for running student (or solution) code.
 *
 * Kept apart from the app's own runtime on purpose: student code can't
 * reach session state (grades, the student list), and the main thread can
 * kill this worker when the code doesn't finish — an infinite loop no
 * longer freezes the tab.
 */

import type { PyodideInterface } from 'pyodide'
import runnerPy from '../python/runner.py?raw'

type LoadPyodideFn = typeof import('pyodide').loadPyodide

const PYODIDE_VERSION = '0.29.3'
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

export interface RunRequest {
  id: number
  code: string
  inputs: string[]
  seed: number
}

let pyodidePromise: Promise<PyodideInterface> | null = null

function getPyodide(): Promise<PyodideInterface> {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      const mod = (await import(/* @vite-ignore */ PYODIDE_CDN + 'pyodide.mjs')) as {
        loadPyodide: LoadPyodideFn
      }
      const pyodide = await mod.loadPyodide({ indexURL: PYODIDE_CDN })
      pyodide.FS.writeFile('/home/pyodide/runner.py', runnerPy)
      pyodide.runPython(`
import sys
if '/home/pyodide' not in sys.path:
    sys.path.insert(0, '/home/pyodide')
import runner
      `)
      return pyodide
    })()
  }
  return pyodidePromise
}

self.onmessage = async (e: MessageEvent<RunRequest>) => {
  const { id, code, inputs, seed } = e.data
  try {
    const pyodide = await getPyodide()
    // numpy / pandas / matplotlib… are fetched from the Pyodide CDN on first
    // import. Only package files are downloaded — no student data goes out.
    try {
      await pyodide.loadPackagesFromImports(code)
    } catch {
      /* unknown module: let the import fail inside the student's code */
    }
    const runner = pyodide.pyimport('runner')
    // Periodic snapshots of the output, so a run that gets killed for
    // taking too long can still show what it printed.
    const onChunk = (json: string) => self.postMessage({ id, chunk: json })
    const proxy = runner.run_code(code, pyodide.toPy(inputs), seed, onChunk)
    const result = proxy.toJs({ dict_converter: Object.fromEntries })
    proxy.destroy()
    runner.destroy()
    self.postMessage({ id, result })
  } catch (err) {
    self.postMessage({ id, error: err instanceof Error ? err.message : String(err) })
  }
}
