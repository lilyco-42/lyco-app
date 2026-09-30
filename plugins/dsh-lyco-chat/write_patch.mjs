/**
 * Emit `cordis.yml`, the patch file the Harness loads this plugin from.
 *
 * Upstream requires an absolute plugin path and says the patch file only
 * contributes configuration (docs/user/develop/basic/index.zh.md), so the
 * file is generated per checkout instead of committed with someone's path.
 *
 *   node write_patch.mjs            # writes cordis.yml next to this file
 *   pnpm dsh web --patch <repo>/plugins/dsh-lyco-chat/cordis.yml
 */
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve, sep } from 'node:path'
import { writeFile } from 'node:fs/promises'

const here = dirname(fileURLToPath(import.meta.url))

/** Absolute, POSIX-separated (YAML + the host loader both prefer forward slashes). */
export function pluginEntry(root = here) {
  const entry = join(root, 'src', 'lyco_chat.ts')
  return { id: 'lyco-chat', name: resolve(entry).split(sep).join('/') }
}

export function patchYaml(root = here) {
  const e = pluginEntry(root)
  return `- insert:\n    - id: ${e.id}\n      name: '${e.name}'\n`
}

if (process.argv[1] && process.argv[1].endsWith('write_patch.mjs')) {
  const target = join(here, 'cordis.yml')
  await writeFile(target, patchYaml(), 'utf8')
  console.log(`wrote ${target}`)
  console.log('load it with:  pnpm dsh web --patch ' + target)
}
