import { useState } from 'react'
import { uploadDataset } from '../api/datasets'
import type { DatasetCreateResponse, EvalType } from '../api/types'
import { ApiError } from '../api/client'
import { addRecentDataset } from '../storage/recent'
import { useNavigate } from 'react-router-dom'
import { DEMO_DATASETS } from '../utils/demoDatasets'

const EVAL_TYPES: EvalType[] = ['prompt', 'rag', 'workflow', 'agent']

export default function DatasetsUploadPage() {
  const navigate = useNavigate()
  const [evalType, setEvalType] = useState<EvalType>('prompt')
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<DatasetCreateResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) {
      setError('请选择一个 JSONL 文件')
      return
    }
    setSubmitting(true)
    setError(null)
    setResult(null)
    try {
      const res = await uploadDataset({ evalType, file, name })
      setResult(res)
      addRecentDataset(res.dataset_id)
      navigate(`/datasets/${encodeURIComponent(res.dataset_id)}`)
    } catch (e2) {
      const message = e2 instanceof ApiError ? e2.message : 'upload failed'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Datasets</h1>
        <div className="muted">上传 JSONL 数据集（dataset-only 模式推荐每条包含 output 或 trace）</div>
      </div>

      <div className="card">
        <h2>上传</h2>
        <form onSubmit={onSubmit} className="form">
          <label className="field">
            <div className="label">eval_type</div>
            <select className="input" value={evalType} onChange={(e) => setEvalType(e.target.value as EvalType)}>
              {EVAL_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <div className="label">name（可选）</div>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="my dataset" />
          </label>

          <label className="field">
            <div className="label">file（.jsonl）</div>
            <input
              className="input"
              type="file"
              accept=".jsonl,application/jsonl,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>

          <div className="row">
            <button className="btn primary" type="submit" disabled={submitting}>
              {submitting ? 'Uploading...' : 'Upload'}
            </button>
            <div className="muted">接口：POST /datasets（multipart/form-data）</div>
          </div>
        </form>

        {error ? <pre className="error">{error}</pre> : null}
        {result ? <pre className="code">{JSON.stringify(result, null, 2)}</pre> : null}
      </div>

      <div className="card">
        <h2>Demo 数据集下载</h2>
        <div className="muted">下载后可直接上传试跑（.jsonl）</div>
        <div className="row" style={{ marginTop: 12 }}>
          {DEMO_DATASETS.map((x) => (
            <a key={x.key} className="btn" href={x.href} download={x.filename}>
              下载 {x.label}
            </a>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>提示</h2>
        <ul className="list">
          <li>每行必须是 JSON 对象；type 必须与 eval_type 一致</li>
          <li>dataset-only 模式：每条 record 至少包含 output 或 trace（否则该条会 failed）</li>
          <li>后端校验失败会返回 422，detail 通常包含行号信息</li>
        </ul>
      </div>
    </div>
  )
}
