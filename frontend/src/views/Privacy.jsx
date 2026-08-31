import { useState } from 'react'

import { api } from '../api/client'
import { useApi } from '../components/useApi'
import { Card, ErrorBox, Loading, PassFail, Stat } from '../components/ui'

const CLASS_STYLES = {
  DIRECT_IDENTIFIER: 'bg-red-100 text-red-800',
  LINKABLE_IDENTIFIER: 'bg-orange-100 text-orange-800',
  QUASI_IDENTIFIER: 'bg-yellow-100 text-yellow-800',
  SENSITIVE_CLINICAL: 'bg-blue-100 text-blue-800',
}

export default function Privacy() {
  const { data, error, loading } = useApi(api.privacy)
  const [filter, setFilter] = useState('')

  if (loading) return <Loading what="privacy status" />
  if (error) return <ErrorBox error={error} />

  const rows = filter
    ? data.audit.filter((r) => r.privacy_classification === filter)
    : data.audit

  const matrixCols = data.minimization_matrix.length
    ? Object.keys(data.minimization_matrix[0])
    : []

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <Stat label="Audited columns" value={data.audited_columns} />
        </Card>
        <Card>
          <Stat
            label="Verification"
            value={data.overall}
            tone={data.overall === 'PASS' ? 'good' : 'bad'}
          />
        </Card>
        <Card>
          <Stat label="Classifications" value={Object.keys(data.classification_counts).length} />
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Verification checks">
          <ul className="space-y-2">
            {data.verification.map((c) => (
              <li key={c.check} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-700">{c.check}</span>
                <PassFail status={c.status} />
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Scope" subtitle="What this prototype does and does not implement">
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-green-700">
                Implemented
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {data.implemented.map((x) => (
                  <span key={x} className="rounded bg-green-50 px-2 py-1 text-xs text-green-800">
                    {x}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-red-700">
                Not implemented
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {data.not_implemented.map((x) => (
                  <span key={x} className="rounded bg-red-50 px-2 py-1 text-xs text-red-800">
                    {x}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                These must not be presented as delivered.
              </p>
            </div>
          </div>
        </Card>
      </div>

      <Card title="Column privacy audit">
        <div className="mb-3 flex flex-wrap gap-2">
          <button
            onClick={() => setFilter('')}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              filter === '' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'
            }`}
          >
            All ({data.audited_columns})
          </button>
          {Object.entries(data.classification_counts).map(([k, v]) => (
            <button
              key={k}
              onClick={() => setFilter(k)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                filter === k ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'
              }`}
            >
              {k} ({v})
            </button>
          ))}
        </div>
        <div className="max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white">
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Table</th>
                <th className="py-2 pr-4">Column</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2">Classification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => (
                <tr key={`${r.table_name}.${r.column_name}`}>
                  <td className="py-1.5 pr-4 text-slate-500">{r.table_name}</td>
                  <td className="py-1.5 pr-4 font-mono text-xs">{r.column_name}</td>
                  <td className="py-1.5 pr-4 text-xs text-slate-400">{r.data_type}</td>
                  <td className="py-1.5">
                    <span
                      className={`rounded px-2 py-0.5 text-[11px] font-medium ${
                        CLASS_STYLES[r.privacy_classification] || 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {r.privacy_classification}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Data minimization matrix" subtitle="Field use per objective">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-left uppercase tracking-wide text-slate-500">
                {matrixCols.map((c) => (
                  <th key={c} className="py-2 pr-3">{c.replace(/_/g, ' ')}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.minimization_matrix.map((r, i) => (
                <tr key={i}>
                  {matrixCols.map((c) => (
                    <td key={c} className="py-1.5 pr-3 text-slate-700">{r[c]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
