import { classNames } from '../../utils/format'

// Generic table (dark). `columns` = [{ key, header, render?, className?, align? }].
export default function DataTable({
  columns,
  rows = [],
  rowKey = (r, i) => r.id ?? i,
  selectedKey,
  onSelect,
  empty = 'No rows.',
  minWidth = 640,
}) {
  if (!rows.length) return <p className="text-sm text-slate-500">{empty}</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm" style={{ minWidth }}>
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500">
            {columns.map((c) => (
              <th
                key={c.key}
                className={classNames('py-2 pr-3 font-medium', c.align === 'right' && 'text-right', c.headClassName)}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const key = rowKey(r, i)
            const selected = selectedKey !== undefined && key === selectedKey
            return (
              <tr
                key={key}
                onClick={onSelect ? () => onSelect(key, r) : undefined}
                className={classNames(
                  'border-b border-white/5 text-slate-300',
                  onSelect && 'cursor-pointer transition-colors',
                  selected ? 'bg-brand/10' : onSelect && 'hover:bg-white/[0.04]'
                )}
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={classNames('py-2.5 pr-3 align-top', c.align === 'right' && 'text-right', c.className)}
                  >
                    {c.render ? c.render(r, i) : r[c.key] ?? '—'}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
