const TERMINAL_STATUSES = new Set(['completed', 'failed', 'stopped'])

export function mergeAgentTeamsStatus(current, incoming) {
  if (!incoming) return current || 'created'
  if (TERMINAL_STATUSES.has(current) && !TERMINAL_STATUSES.has(incoming)) {
    return current
  }
  return incoming
}
