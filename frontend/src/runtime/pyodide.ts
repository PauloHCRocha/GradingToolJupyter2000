/**
 * In-browser Python runtime.
 *
 * Pyodide is fetched from the jsdelivr CDN at runtime — its ~6MB of WASM and
 * Python stdlib never enter our bundle. The .py source files of our app are
 * imported as raw strings at build time and written into Pyodide's virtual
 * filesystem, then `import api` makes them callable.
 */

import { ref } from 'vue'
import type { PyodideInterface } from 'pyodide'

type LoadPyodideFn = typeof import('pyodide').loadPyodide

import notebookParserPy from '../python/notebook_parser.py?raw'
import questionDetectorPy from '../python/question_detector.py?raw'
import questionWindowPy from '../python/question_window.py?raw'
import submissionLoaderPy from '../python/submission_loader.py?raw'
import aiDetectionPy from '../python/ai_detection.py?raw'
import gradeSuggesterPy from '../python/grade_suggester.py?raw'
import plagiarismPy from '../python/plagiarism.py?raw'
import statePy from '../python/state.py?raw'
import anonymizerPy from '../python/anonymizer.py?raw'
import apiPy from '../python/api.py?raw'

const PYODIDE_VERSION = '0.29.3'
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

export type RuntimeStage = 'idle' | 'loading-runtime' | 'loading-modules' | 'ready' | 'error'

export const runtimeStage = ref<RuntimeStage>('idle')
export const runtimeError = ref<string | null>(null)

let pyodidePromise: Promise<PyodideInterface> | null = null

async function loadFromCdn(): Promise<LoadPyodideFn> {
  const mod = await import(/* @vite-ignore */ PYODIDE_CDN + 'pyodide.mjs')
  return (mod as { loadPyodide: LoadPyodideFn }).loadPyodide
}

export function getPyodide(): Promise<PyodideInterface> {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      try {
        runtimeStage.value = 'loading-runtime'
        const loadPyodide = await loadFromCdn()
        const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN })

        runtimeStage.value = 'loading-modules'
        const files: Record<string, string> = {
          '/home/pyodide/notebook_parser.py': notebookParserPy,
          '/home/pyodide/question_detector.py': questionDetectorPy,
          '/home/pyodide/question_window.py': questionWindowPy,
          '/home/pyodide/submission_loader.py': submissionLoaderPy,
          '/home/pyodide/ai_detection.py': aiDetectionPy,
          '/home/pyodide/grade_suggester.py': gradeSuggesterPy,
          '/home/pyodide/plagiarism.py': plagiarismPy,
          '/home/pyodide/state.py': statePy,
          '/home/pyodide/anonymizer.py': anonymizerPy,
          '/home/pyodide/api.py': apiPy,
        }
        for (const [path, content] of Object.entries(files)) {
          pyodide.FS.writeFile(path, content)
        }
        pyodide.runPython(`
import sys
if '/home/pyodide' not in sys.path:
    sys.path.insert(0, '/home/pyodide')
import api
        `)
        runtimeStage.value = 'ready'
        return pyodide
      } catch (e) {
        runtimeStage.value = 'error'
        runtimeError.value = e instanceof Error ? e.message : String(e)
        throw e
      }
    })()
  }
  return pyodidePromise
}

/**
 * Call a Python function in `api.py` and return a plain JS value.
 *
 * - JS args are auto-converted by Pyodide (Uint8Array -> bytes, plain object
 *   -> dict, etc.).
 * - The Python return value (PyProxy) is converted with `dict_converter:
 *   Object.fromEntries` so dicts come back as plain JS objects all the way
 *   down.
 */
/**
 * Convert JS args to Python-friendly proxies before calling.
 *
 * Pyodide auto-converts primitives (string, number, bool) but TypedArrays
 * arrive on the Python side as a JsProxy unless we toPy() them first —
 * `json.loads` and `zipfile.ZipFile` choke on JsProxy. Plain JS objects/
 * arrays must also be converted explicitly so Python sees real dicts/lists.
 */
function convertArg(pyodide: PyodideInterface, arg: unknown): unknown {
  if (arg instanceof Uint8Array || arg instanceof ArrayBuffer) {
    return pyodide.toPy(arg)
  }
  if (Array.isArray(arg) || (arg !== null && typeof arg === 'object')) {
    return pyodide.toPy(arg)
  }
  return arg
}

export async function callApi<T = unknown>(funcName: string, ...args: unknown[]): Promise<T> {
  const pyodide = await getPyodide()
  const api = pyodide.pyimport('api')
  const fn = api[funcName] as ((...a: unknown[]) => unknown) | undefined
  if (typeof fn !== 'function') {
    api.destroy?.()
    throw new Error(`Unknown API function: ${funcName}`)
  }

  const converted = args.map((a) => convertArg(pyodide, a))
  const toDestroy: Array<{ destroy?: () => void }> = []
  for (const c of converted) {
    if (c && typeof (c as { destroy?: () => void }).destroy === 'function') {
      toDestroy.push(c as { destroy?: () => void })
    }
  }

  let result: unknown
  try {
    result = fn(...converted)
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    const lastLine = msg.split('\n').filter((l) => l.trim()).pop() ?? msg
    throw new Error(lastLine)
  } finally {
    api.destroy?.()
    for (const p of toDestroy) p.destroy?.()
  }

  if (result && typeof (result as { toJs?: () => unknown }).toJs === 'function') {
    const proxy = result as { toJs: (opts: object) => unknown; destroy: () => void }
    const js = proxy.toJs({ dict_converter: Object.fromEntries })
    proxy.destroy()
    return js as T
  }
  return result as T
}
