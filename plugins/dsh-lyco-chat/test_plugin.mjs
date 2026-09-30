/**
 * Acceptance tests for the lyco-chat Harness plugin.
 *
 * The registered tools are built with the real `defineTool` from
 * @deepseek-ai/dsh-tools (installed as a devDependency), so schema-shape
 * mistakes fail here the same way the host would reject them. Execution is
 * driven against `test_support/core_cli_stub.py` (LYCO_CLI_MODULE) rather than
 * a model-backed run, so this needs no GGUF and no network.
 *
 * Run: npm test           (from plugins/dsh-lyco-chat)
 *      node --test test_plugin.mjs
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { askArgs, askCore, repoRoot, shopsArgs, validateShops } from './src/runner.js'
import { patchYaml, pluginEntry } from './write_patch.mjs'

const here = dirname(fileURLToPath(import.meta.url))

function fakeSpawn(stdout, opts = {}) {
  const seen = []
  const fn = async (cmd, args, runOpts) => {
    seen.push({ cmd, args, runOpts })
    if (opts.reject) {
      const err = new Error(opts.rejectMessage ?? 'exit 1')
      if (stdout !== undefined) err.stdout = stdout
      throw err
    }
    return { stdout }
  }
  fn.seen = seen
  return fn
}

test('runner: builds the CLI argv for both modes', () => {
  assert.deepEqual(askArgs({ question: '什么是 GGUF？' }), ['什么是 GGUF？'])
  assert.deepEqual(
    shopsArgs({ kind: '理发', lat: 31.23, lng: 121.47, radius: 800, question: '哪家好看' }),
    ['--shops', '理发', '--lat', '31.23', '--lng', '121.47', '--radius', '800',
      '--question', '哪家好看'])
  assert.deepEqual(
    shopsArgs({ kind: '理发', lat: 1, lng: 2 }),
    ['--shops', '理发', '--lat', '1', '--lng', '2'])
})

test('runner: validates shop arguments before spawning', () => {
  assert.equal(validateShops({ kind: '理发', lat: 31, lng: 121 }), null)
  assert.match(validateShops({ kind: '', lat: 0, lng: 0 }), /kind/)
  assert.match(validateShops({ kind: '理发', lat: 91, lng: 0 }), /lat/)
  assert.match(validateShops({ kind: '理发', lat: 0, lng: 181 }), /lng/)
  assert.match(validateShops({ kind: '理发', lat: 0, lng: 0, radius: 0 }), /radius/)
  assert.match(validateShops({ kind: '理发', lat: 0, lng: 0, radius: 99999 }), /radius/)
})

test('runner: parses the CLI JSON and keeps the verify block', async () => {
  const spawn = fakeSpawn(JSON.stringify({
    mode: 'ask', question: 'q', answer: 'a', routed_search: true,
    evidence: ['e1', 'e2'], verify: { pass: false, reason: 'invented-numbers' },
    elapsed_s: 1.5,
  }))
  const r = await askCore(['q'], { spawn, cwd: '/nowhere' })
  assert.equal(r.mode, 'ask')
  assert.equal(r.answer, 'a')
  assert.equal(r.rest.verify.reason, 'invented-numbers')
  assert.deepEqual(spawn.seen[0].args.slice(0, 2), ['-m', 'core.cli'])
})

test('runner: honors LYCO_CLI_MODULE (the test seam)', async () => {
  const spawn = fakeSpawn('{"mode":"ask","answer":"x"}')
  process.env.LYCO_CLI_MODULE = 'test_support.core_cli_stub'
  try {
    await askCore(['hi'], { spawn, cwd: '/nowhere' })
    assert.equal(spawn.seen[0].args[1], 'test_support.core_cli_stub')
  } finally {
    delete process.env.LYCO_CLI_MODULE
  }
})

test('runner: a non-zero exit that still carries JSON becomes that error', async () => {
  const spawn = fakeSpawn(JSON.stringify({ error: 'AMAP_WEBSERVICE_KEY missing' }),
    { reject: true })
  const r = await askCore(['--shops', '理发'], { spawn, cwd: '/nowhere' })
  assert.equal(r.mode, 'error')
  assert.match(r.error, /AMAP_WEBSERVICE_KEY/)
})

test('runner: spawn failure and garbage stdout both report an error, never a guess', async () => {
  const r1 = await askCore(['q'], { spawn: fakeSpawn(undefined, { reject: true, rejectMessage: 'ENOENT python' }) })
  assert.equal(r1.mode, 'error')
  assert.match(r1.error, /ENOENT/)

  const r2 = await askCore(['q'], { spawn: fakeSpawn('Loading model...\nnot json') })
  assert.equal(r2.mode, 'error')
  assert.match(r2.error, /did not return JSON/)
})

test('repoRoot walks up to the directory holding core/loop.py', async () => {
  const root = repoRoot()
  const stat = await readFile(join(root, 'core', 'loop.py'), 'utf8')
  assert.match(stat, /def answer/)
})

test('patch file: absolute path with forward slashes, id lyco-chat', () => {
  const e = pluginEntry('/repo/plugins/dsh-lyco-chat')
  assert.equal(e.id, 'lyco-chat')
  const asPosix = e.name.replace(/\\/g, '/')
  // resolve() keeps the ambient drive on Windows, so assert the properties
  // the host actually requires: absolute, separator-normalized, right file.
  assert.match(asPosix, /(^[A-Za-z]:\/|^\/)/, 'must be absolute')
  assert.ok(asPosix.endsWith('/repo/plugins/dsh-lyco-chat/src/lyco_chat.ts'), asPosix)
  assert.ok(!asPosix.includes('\\'), 'no backslashes in the patch')
  const y = patchYaml('/repo/plugins/dsh-lyco-chat')
  assert.ok(y.startsWith('- insert:\n    - id: lyco-chat\n'))
  assert.ok(y.includes("name: '") && y.endsWith(".ts'\n"), y)
})

test('plugin registers both tools through the real defineTool', async () => {
  const mod = await import('./src/lyco_chat.ts')
  assert.equal(mod.name, 'lyco-chat')
  assert.deepEqual(mod.inject, ['tools'])
  const reg = []
  mod.apply({ tools: { register: (t) => reg.push(t) } })
  assert.deepEqual(reg.map(t => t.name), ['lyco_ask', 'lyco_nearby_shops'])
  assert.deepEqual(reg[0].parameters.required, ['question'])
  assert.deepEqual(reg[1].parameters.required, ['kind', 'lat', 'lng'])
  for (const t of reg) {
    assert.equal(typeof t.execute, 'function')
    assert.equal(typeof t.output.render, 'function')
    assert.equal(t.output.schema.additionalProperties, false,
      'object outputs must close additionalProperties')
  }
})

test('lyco_ask end to end through python, against the stub CLI', async () => {
  const mod = await import('./src/lyco_chat.ts')
  const reg = []
  mod.apply({ tools: { register: (t) => reg.push(t) } })
  const ask = reg[0]
  process.env.LYCO_CLI_MODULE = 'test_support.core_cli_stub'
  try {
    const r = await ask.execute({ question: '什么是 GGUF？' }, {})
    assert.equal(r.answer, 'stub 答案。')
    assert.equal(r.grounded, true)
    assert.equal(r.evidence_count, 1)
    const bad = await ask.execute({ question: 'BOOM' }, {})
    assert.equal(bad.error, 'simulated core failure')
    assert.equal(bad.grounded, false)
    const text = ask.output.render({}, bad)[0].text
    assert.match(text, /lyco_ask failed/)
  } finally {
    delete process.env.LYCO_CLI_MODULE
  }
})

test('lyco_nearby_shops end to end, and refuses bad coordinates', async () => {
  const mod = await import('./src/lyco_chat.ts')
  const reg = []
  mod.apply({ tools: { register: (t) => reg.push(t) } })
  const shops = reg[1]
  process.env.LYCO_CLI_MODULE = 'test_support.core_cli_stub'
  try {
    const r = await shops.execute({ kind: '理发', lat: 31.23, lng: 121.47 }, {})
    assert.equal(r.found, 2)
    assert.equal(r.ranking.length, 2)
    const text = shops.output.render({}, r)[0].text
    assert.match(text, /2 家 理发/)
    assert.match(text, /证据不足/)
    const nope = await shops.execute({ kind: '理发', lat: 120, lng: 0 }, {})
    assert.match(nope.error, /lat out of range/)
  } finally {
    delete process.env.LYCO_CLI_MODULE
  }
})

test('an ungrounded answer is labelled for the model, not silently passed on', async () => {
  const mod = await import('./src/lyco_chat.ts')
  const reg = []
  mod.apply({ tools: { register: (t) => reg.push(t) } })
  const text = reg[0].output.render({}, {
    answer: '量化能提速', grounded: false, verify_reason: 'invented-numbers',
    evidence_count: 0, elapsed_s: 1,
  })[0].text
  assert.match(text, /未被检索证据支持/)
  assert.match(text, /verify=invented-numbers/)
})

test('manifest and locale metadata follow the upstream recipe', async () => {
  const pkg = JSON.parse(await readFile(join(here, 'package.json'), 'utf8'))
  assert.equal(pkg.type, 'module')
  assert.ok(pkg.exports['./locale/*.json'], 'locale must be exported')
  assert.ok(pkg.exports['./package.json'], 'package.json must be exported for fallbacks')
  assert.ok(pkg.files.includes('locale/*.json'), 'locale must be published')
  assert.ok(pkg.peerDependencies['@deepseek-ai/cordis'], 'cordis is a peer dep')
  assert.ok(pkg.devDependencies['@deepseek-ai/cordis'], 'peer must be mirrored in devDependencies')
  for (const lang of ['en', 'zh']) {
    const l = JSON.parse(await readFile(join(here, 'locale', `${lang}.json`), 'utf8'))
    assert.ok(typeof l.meta?.title === 'string' && l.meta.title.trim(), `${lang} title`)
    assert.ok(typeof l.meta?.description === 'string' && l.meta.description.trim(), `${lang} description`)
  }
})
