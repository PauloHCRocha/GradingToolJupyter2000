/**
 * Model ids, usage and the cost hint for auto-grading. Kept apart from
 * `claude.ts` so the views can use them without pulling the Anthropic SDK
 * into the main bundle — the SDK is only loaded when Claude is first called.
 */

export type ClaudeModel = 'claude-opus-5-5' | 'claude-sonnet-5-5'
export type Effort = 'low' | 'medium' | 'high'

export interface Usage {
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens: number
  cache_creation_input_tokens: number
}

// USD per million tokens (input, output, cache read). Cache writes are
// billed at 1.25x input. Used only for the "≈ cost" hint in the UI.
const PRICES: Record<ClaudeModel, [number, number, number]> = {
  'claude-opus-5-5': [4, 20, 0.2],
  'claude-sonnet-5-5': [2, 10, 0.2],
}

export function estimateCost(model: ClaudeModel, u: Usage): number {
  const [inp, out, read] = PRICES[model]
  return (
    (u.input_tokens * inp +
      u.cache_creation_input_tokens * inp * 1.25 +
      u.cache_read_input_tokens * read +
      u.output_tokens * out) /
    1_000_000
  )
}
