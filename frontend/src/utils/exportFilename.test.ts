import { describe, expect, it } from 'vitest'
import { buildExportFilename } from './exportFilename.ts'

describe('buildExportFilename', () => {
  it('names json export with .json', () => {
    expect(buildExportFilename('abc', 'json')).toBe('run-abc.json')
  })

  it('names jsonl export with .jsonl', () => {
    expect(buildExportFilename('abc', 'jsonl')).toBe('run-abc.jsonl')
  })

  it('names csv export with .csv', () => {
    expect(buildExportFilename('abc', 'csv')).toBe('run-abc.csv')
  })
})

