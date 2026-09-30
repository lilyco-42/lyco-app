// Talk to the lyco core (Python) from a DeepSeek Harness plugin.
//
// The loop and the POI ranking live in this repo's Python (`core.cli`), so the
// plugin shells out instead of reimplementing retrieval in TypeScript. Plain JS
// with JSDoc types on purpose: the plugin shell is a .ts file loaded by the
// host, and this module has to be importable from plain `node --test` too.

/**
 * @typedef {object} LycoResult
 * @property {string} mode            "ask" | "shops" | "error"
 * @property {string} [answer]
 * @property {string} [error]
 * @property {*} [rest]               everything else the CLI returned
 */

import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const run = promisify(execFile)

/**
 * Repo root: the directory holding core/loop.py, found by walking up from this
 * file, so the plugin works from any checkout location. LYCO_REPO_ROOT wins.
 */
export function repoRoot() {
  if (process.env.LYCO_REPO_ROOT) return process.env.LYCO_REPO_ROOT
  let dir = dirname(fileURLToPath(import.meta.url))
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, 'core', 'loop.py'))) return dir
    dir = resolve(dir, '..')
  }
  return process.cwd()
}

/** python interpreter: LYCO_PY, or the plain `python` on PATH. */
export const pythonBin = () => process.env.LYCO_PY ?? 'python'

export const DEFAULT_TIMEOUT_MS = 120000

/** The CLI entry point, overridable so the plugin can be tested against a
    stub instead of a model-backed run. */
export const cliModule = () => process.env.LYCO_CLI_MODULE ?? 'core.cli'

/**
 * @param {string[]} cliArgs     args after `-m core.cli`
 * @param {{spawn?: Function, timeoutMs?: number, py?: string, cwd?: string}} [deps]
 * @returns {Promise<LycoResult>}
 */
export async function askCore(cliArgs, deps = {}) {
  const py = deps.py ?? pythonBin()
  const spawn = deps.spawn ?? run
  const timeoutMs = deps.timeoutMs ?? DEFAULT_TIMEOUT_MS
  let stdout
  try {
    ({ stdout } = await spawn(py, ['-m', cliModule(), ...cliArgs], {
      cwd: deps.cwd ?? repoRoot(),
      timeout: timeoutMs,
      windowsHide: true,
      maxBuffer: 4 * 1024 * 1024,
    }))
  } catch (err) {
    // A non-zero exit still carries the CLI's JSON object on stdout; anything
    // else (spawn failure, timeout) is reported as text, never as a guess.
    const out = err && err.stdout ? String(err.stdout) : ''
    const parsed = parseJson(out)
    if (parsed) return normalize(parsed)
    return { mode: 'error', error: `${err && err.message ? err.message : String(err)}` }
  }
  const parsed = parseJson(stdout)
  if (!parsed) {
    return { mode: 'error', error: `core.cli did not return JSON: ${String(stdout).slice(0, 200)}` }
  }
  return normalize(parsed)
}

function parseJson(text) {
  if (!text) return null
  const t = String(text).trim()
  if (!t.startsWith('{')) return null
  try {
    return JSON.parse(t)
  } catch {
    return null
  }
}

function normalize(d) {
  if (d && typeof d.error === 'string') return { mode: 'error', error: d.error }
  const { mode, answer, question, ...rest } = d ?? {}
  return { mode: mode ?? 'ask', answer: answer ?? '', question: question ?? '', rest }
}

/**
 * `lyco_ask` arguments -> CLI arguments.
 * @param {{question: string}} args
 */
export function askArgs(args) {
  return [String(args.question ?? '')]
}

/**
 * `lyco_nearby_shops` arguments -> CLI arguments. Coordinates come from the
 * caller (the harness has no location of its own); radius is metres.
 * @param {{kind: string, lat: number, lng: number, radius?: number, question?: string}} args
 */
export function shopsArgs(args) {
  const out = ['--shops', String(args.kind), '--lat', String(args.lat), '--lng', String(args.lng)]
  if (args.radius) out.push('--radius', String(args.radius))
  if (args.question) out.push('--question', String(args.question))
  return out
}

/** Shape check used by the tools to refuse nonsense before spawning. */
export function validateShops(args) {
  if (!args || !String(args.kind ?? '').trim()) return 'kind is required'
  for (const k of ['lat', 'lng']) {
    const v = Number(args[k])
    if (!Number.isFinite(v)) return `${k} must be a number`
  }
  if (Math.abs(Number(args.lat)) > 90) return 'lat out of range'
  if (Math.abs(Number(args.lng)) > 180) return 'lng out of range'
  const r = args.radius === undefined || args.radius === null ? 1000 : Number(args.radius)
  if (!Number.isFinite(r) || r <= 0 || r > 50000) return 'radius must be 1..50000 metres'
  return null
}
