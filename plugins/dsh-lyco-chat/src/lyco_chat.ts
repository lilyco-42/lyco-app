import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { askArgs, askCore, shopsArgs, validateShops } from './runner.js'

/**
 * lyco-chat as a DeepSeek Harness plugin: two tools over the repo's own Python
 * loop (`python -m core.cli`), so the host model gets lyco's grounded answer
 * and the "which shop nearby is actually good" chain without a second
 * implementation.
 *
 * Contract taken from the upstream cookbooks (docs/cookbook/adding-a-tool.zh.md
 * and docs/user/develop/basic/tool.zh.md): export `name`, `inject`, and
 * `apply(ctx)`; register typed tools on `ctx.tools`.
 */

export const name = 'lyco-chat'
export const inject = ['tools']

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'lyco_ask',
    description: 'Ask lyco: runs retrieval over the local knowledge base, RustCC RSS and DeepWiki, then a local small model summarizes. The reply carries a `verify` field: whether the answer is backed by the evidence it retrieved.',
    parameters: {
      question: { type: 'string', required: true, description: 'The question, in Chinese or English' },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          answer: { type: 'string' },
          grounded: { type: 'boolean' },
          verify_reason: { type: 'string' },
          evidence_count: { type: 'number' },
          elapsed_s: { type: 'number' },
          error: { type: 'string' },
        },
        additionalProperties: false,
      },
      render: (_args, value) => {
        if (value.error) return [{ type: 'text', text: `lyco_ask failed: ${value.error}` }]
        const head = value.grounded ? '' : '\n(未被检索证据支持，慎信)'
        return [{
          type: 'text',
          text: `${value.answer}${head}\n[evidence=${value.evidence_count}, verify=${value.verify_reason}, ${value.elapsed_s}s]`,
        }]
      },
    },
    async execute(args) {
      const r = await askCore(askArgs(args))
      if (r.mode === 'error') {
        return { answer: '', grounded: false, verify_reason: 'error', evidence_count: 0, elapsed_s: 0, error: r.error }
      }
      const rest: Record<string, unknown> = (r.rest ?? {}) as Record<string, unknown>
      const verify = (rest.verify ?? {}) as { pass?: boolean, reason?: string }
      return {
        answer: r.answer,
        grounded: verify.pass === true,
        verify_reason: verify.reason ?? 'unknown',
        evidence_count: Array.isArray(rest.evidence) ? rest.evidence.length : 0,
        elapsed_s: typeof rest.elapsed_s === 'number' ? rest.elapsed_s : 0,
      }
    },
  }))

  ctx.tools.register(defineTool({
    name: 'lyco_nearby_shops',
    description: 'Rank the shops of one kind around a location: Amap around-search, then per-shop review evidence through the same lyco loop. Needs AMAP_WEBSERVICE_KEY in the host environment.',
    parameters: {
      kind: { type: 'string', required: true, description: 'Shop kind in Chinese, e.g. 理发' },
      lat: { type: 'number', required: true, description: 'Latitude of the caller' },
      lng: { type: 'number', required: true, description: 'Longitude of the caller' },
      radius: { type: 'number', description: 'Search radius in metres, default 1000' },
      question: { type: 'string', description: 'What to judge the shops by; defaults to a general "is it good" question' },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          kind: { type: 'string' },
          found: { type: 'number' },
          ranking: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                name: { type: 'string' },
                address: { type: 'string' },
                reason: { type: 'string' },
                verify_pass: { type: 'boolean' },
              },
              additionalProperties: false,
            },
          },
          error: { type: 'string' },
        },
        additionalProperties: false,
      },
      render: (_args, value) => {
        if (value.error) return [{ type: 'text', text: `lyco_nearby_shops failed: ${value.error}` }]
        const lines = (value.ranking ?? []).map((s, i) =>
          `${i + 1}. ${s.name} — ${s.reason ?? ''}${s.verify_pass ? '' : '（证据不足）'}`)
        return [{ type: 'text', text: `${value.found} 家 ${value.kind}：\n${lines.join('\n') || '（没有结果）'}` }]
      },
    },
    async execute(args) {
      const bad = validateShops(args)
      if (bad) return { kind: args.kind ?? '', found: 0, ranking: [], error: bad }
      const r = await askCore(shopsArgs(args))
      if (r.mode === 'error') {
        return { kind: args.kind ?? '', found: 0, ranking: [], error: r.error }
      }
      const rest = (r.rest ?? {}) as { kind?: string, found?: number, ranking?: unknown[] }
      return {
        kind: rest.kind ?? args.kind,
        found: typeof rest.found === 'number' ? rest.found : 0,
        ranking: Array.isArray(rest.ranking) ? rest.ranking : [],
      }
    },
  }))
}
