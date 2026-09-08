import { Card } from './ui'

// Dense packing grid. Tiles pick a column span (1-6) on md+; on small screens
// everything is one column. Rows size to content (auto-rows-min) so the grid
// packs horizontally instead of stacking into one long scroll.
export function Bento({ children, className = '' }) {
  return <div className={`grid gap-3 md:auto-rows-min md:grid-cols-6 ${className}`}>{children}</div>
}

const COL = {
  1: 'md:col-span-1',
  2: 'md:col-span-2',
  3: 'md:col-span-3',
  4: 'md:col-span-4',
  5: 'md:col-span-5',
  6: 'md:col-span-6',
}
const ROW = {
  1: '',
  2: 'md:row-span-2',
  3: 'md:row-span-3',
  4: 'md:row-span-4',
}

// A bento cell. Pass Card props (title/subtitle/right) straight through, plus
// `col` / `row` spans. `scroll` caps height and scrolls internally (tables).
// `plain` skips the Card chrome (for a raw note / banner spanning the grid).
export function Tile({ col = 2, row = 1, scroll, plain, bodyClass = '', className = '', children, ...cardProps }) {
  const spanCls = `${COL[col] || COL[2]} ${ROW[row] || ''} min-w-0`
  if (plain) return <div className={spanCls}>{children}</div>
  return (
    <div className={spanCls}>
      <Card className={`flex h-full flex-col ${className}`} {...cardProps}>
        <div className={`min-w-0 flex-1 ${scroll ? 'max-h-72 overflow-auto' : ''} ${bodyClass}`}>{children}</div>
      </Card>
    </div>
  )
}
