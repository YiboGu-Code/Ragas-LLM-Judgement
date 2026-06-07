import { describe, expect, it } from 'vitest'
import { DEMO_DATASETS } from './demoDatasets.ts'

describe('DEMO_DATASETS', () => {
  it('contains 4 eval types with jsonl href + download filename', () => {
    expect(DEMO_DATASETS.map((x) => x.key)).toEqual(['prompt', 'rag', 'workflow', 'agent'])
    for (const x of DEMO_DATASETS) {
      expect(x.href.startsWith('/demo-datasets/')).toBe(true)
      expect(x.href.endsWith('.jsonl')).toBe(true)
      expect(x.filename.endsWith('.jsonl')).toBe(true)
    }
  })
})
