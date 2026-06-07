export type DemoDatasetKey = 'prompt' | 'rag' | 'workflow' | 'agent'

export const DEMO_DATASETS: ReadonlyArray<{
  key: DemoDatasetKey
  label: string
  href: string
  filename: string
}> = [
  {
    key: 'prompt',
    label: 'Prompt',
    href: '/demo-datasets/prompt.jsonl',
    filename: 'prompt-demo.jsonl',
  },
  { key: 'rag', label: 'RAG', href: '/demo-datasets/rag.jsonl', filename: 'rag-demo.jsonl' },
  {
    key: 'workflow',
    label: 'Workflow',
    href: '/demo-datasets/workflow.jsonl',
    filename: 'workflow-demo.jsonl',
  },
  { key: 'agent', label: 'Agent', href: '/demo-datasets/agent.jsonl', filename: 'agent-demo.jsonl' },
]
