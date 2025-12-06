import { useMemo, useState, ReactNode } from 'react'
import Plot from 'react-plotly.js'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  SortingState,
  ColumnDef
} from '@tanstack/react-table'
import type { ExecutionOutput } from './usePyodide'


interface CardProps {
  variant: 'executing' | 'error' | 'success'
  title: string
  subtitle?: string
  children: ReactNode
}

const cardStyles = {
  executing: 'from-purple-500/10 to-cyan-500/10 border-purple-500/30',
  error: 'from-red-500/10 to-red-500/10 border-red-500/30',
  success: 'from-emerald-500/10 to-cyan-500/10 border-emerald-500/30'
}

const headerStyles = {
  executing: 'bg-purple-500/10 border-purple-500/20 text-purple-300',
  error: 'bg-red-500/10 border-red-500/20 text-red-400',
  success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
}

const icons = { executing: '🐍', error: '⚠️', success: '🐍' }

function Card({ variant, title, subtitle, children }: CardProps) {
  return (
    <div className={`bg-gradient-to-r ${cardStyles[variant]} rounded-2xl border animate-fade-in overflow-hidden`}>
      <div className={`px-4 py-2 ${headerStyles[variant]} border-b flex items-center gap-2`}>
        <span>{icons[variant]}</span>
        <span className="text-sm font-medium">{title}</span>
        {subtitle && <span className="text-slate-400 text-xs ml-2">— {subtitle}</span>}
      </div>
      <div className="p-4 space-y-4">{children}</div>
    </div>
  )
}

function CodeBlock({ code, label = 'View code' }: { code: string; label?: string }) {
  return (
    <details className="text-xs">
      <summary className="text-slate-500 cursor-pointer hover:text-slate-400">{label}</summary>
      <pre className="mt-2 p-3 bg-slate-900/80 rounded-lg text-slate-400 overflow-x-auto text-xs max-h-60 overflow-y-auto">
        {code}
      </pre>
    </details>
  )
}

function ConsoleBlock({ output, live }: { output: string; live?: boolean }) {
  return (
    <div className={`p-3 rounded-lg ${live ? 'bg-slate-900/80 border border-slate-700' : 'bg-slate-800/80'}`}>
      <p className="text-xs text-slate-500 mb-1 font-mono">▶ Console{live ? '' : ' Output'}</p>
      <pre className={`text-xs font-mono whitespace-pre-wrap max-h-32 overflow-y-auto ${live ? 'text-green-400' : 'text-slate-300'}`}>
        {output}
      </pre>
    </div>
  )
}

function PlotlyChart({ data }: { data: string }) {
  try {
    const parsed = JSON.parse(data)
    return (
      <div className="bg-white rounded-lg p-2">
        <Plot
          data={parsed.data}
          layout={{ ...parsed.layout, autosize: true, margin: { l: 50, r: 30, t: 40, b: 50 } }}
          config={{ responsive: true, displayModeBar: true }}
          style={{ width: '100%', height: '400px' }}
        />
      </div>
    )
  } catch {
    return <div className="text-red-400 text-sm">Failed to render chart</div>
  }
}

function DataTable({ data }: { data: unknown[] }) {
  const [sorting, setSorting] = useState<SortingState>([])
  
  const columns = useMemo<ColumnDef<unknown>[]>(() => {
    if (!data.length) return []
    const firstRow = data[0] as Record<string, unknown>
    return Object.keys(firstRow).map(key => ({
      accessorKey: key,
      header: key,
      cell: info => {
        const v = info.getValue()
        return v == null ? '-' : typeof v === 'number' ? v.toLocaleString() : String(v)
      }
    }))
  }, [data])
  
  const table = useReactTable({
    data, columns, state: { sorting }, onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } }
  })
  
  if (!data.length) return null
  
  return (
    <div className="bg-white rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-100">
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id}>
                {hg.headers.map(h => (
                  <th key={h.id} onClick={h.column.getToggleSortingHandler()}
                    className="px-3 py-2 text-left font-medium text-slate-700 cursor-pointer hover:bg-slate-200">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: ' ↑', desc: ' ↓' }[h.column.getIsSorted() as string] ?? ''}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <tr key={row.id} className="border-t border-slate-200 hover:bg-slate-50">
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-3 py-2 text-slate-800">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-t border-slate-200 text-xs">
          <span className="text-slate-600">Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
          <div className="flex gap-1">
            <button onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}
              className="px-2 py-1 bg-slate-200 rounded disabled:opacity-50 hover:bg-slate-300">Prev</button>
            <button onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}
              className="px-2 py-1 bg-slate-200 rounded disabled:opacity-50 hover:bg-slate-300">Next</button>
          </div>
        </div>
      )}
    </div>
  )
}

function ImageOutput({ output }: { output: ExecutionOutput }) {
  return (
    <div className="rounded-lg overflow-hidden bg-white p-2">
      <img src={`data:image/${output.format};base64,${output.data}`} alt="Output" className="max-w-full h-auto" />
    </div>
  )
}

function FileOutput({ output }: { output: ExecutionOutput }) {
  const download = () => {
    const bytes = Uint8Array.from(atob(output.data), c => c.charCodeAt(0))
    const blob = new Blob([bytes], { type: `application/${output.format}` })
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: output.filename || `output.${output.format}` })
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const icons: Record<string, string> = { csv: '📊', xlsx: '📗', json: '📋', txt: '📄' }
  return (
    <button onClick={download} className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white">
      <span>{icons[output.format] || '📁'}</span> Download {output.filename || `output.${output.format}`}
    </button>
  )
}

const OutputRenderer: Record<string, (props: { output: ExecutionOutput }) => ReactNode> = {
  image: ImageOutput,
  file: FileOutput,
  chart: ({ output }) => <PlotlyChart data={output.data} />
}

function ResultBlock({ result }: { result: unknown }) {
  const formatted = result == null ? '' : typeof result === 'string' ? result : JSON.stringify(result, null, 2)
  return (
    <div className="p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/30">
      <p className="text-xs text-emerald-400 mb-1 font-medium">Result:</p>
      <pre className="text-sm text-emerald-300 font-mono whitespace-pre-wrap">{formatted}</pre>
    </div>
  )
}

export interface CodeOutputProps {
  outputs: ExecutionOutput[]
  isExecuting?: boolean
  error?: string | null
  stdout?: string
  result?: unknown
  code?: string
  explanation?: string
  progress?: string
  consoleOutput?: string
  chartData?: string
  tableData?: unknown[]
}

export function CodeOutput(props: CodeOutputProps) {
  const { outputs, isExecuting, error, stdout, result, code, explanation, progress, consoleOutput, chartData, tableData } = props

  if (isExecuting) {
    return (
      <Card variant="executing" title="Python Execution">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-300 text-sm">{progress || 'Executing...'}</span>
        </div>
        {consoleOutput && <ConsoleBlock output={consoleOutput} live />}
        {code && <CodeBlock code={code} label="View code..." />}
      </Card>
    )
  }

  if (error) {
    return (
      <Card variant="error" title="Execution Error">
        <pre className="text-red-300 text-sm font-mono whitespace-pre-wrap break-words">{error}</pre>
        {code && <CodeBlock code={code} label="View failed code" />}
      </Card>
    )
  }

  const hasContent = outputs.length > 0 || stdout || result != null || chartData || tableData?.length
  if (!hasContent) return null

  return (
    <Card variant="success" title="Python Output" subtitle={explanation}>
      {chartData && <PlotlyChart data={chartData} />}
      {tableData?.length && <DataTable data={tableData} />}
      {result != null && <ResultBlock result={result} />}
      {stdout && <ConsoleBlock output={stdout} />}
      {outputs.map((output, i) => {
        const Renderer = OutputRenderer[output.type]
        return Renderer ? <div key={i}><Renderer output={output} /></div> : null
      })}
      {code && <CodeBlock code={code} label="📝 View generated code" />}
    </Card>
  )
}
