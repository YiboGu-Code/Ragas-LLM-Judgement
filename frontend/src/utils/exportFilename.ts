export function buildExportFilename(runId: string, format: 'csv' | 'json' | 'jsonl'): string {
  const safeId = runId.trim() || 'run'
  return `run-${safeId}.${format}`
}

