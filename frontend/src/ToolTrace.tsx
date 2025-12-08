import { ToolCall, ToolInfo } from './types'

interface ToolTraceProps {
  trace: ToolCall[]
  tools: ToolInfo[]
  noToolsMessage: string
  isLoading?: boolean
  onClear?: () => void
}

function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function ToolInput({ input }: { input?: Record<string, unknown> }) {
  if (!input || Object.keys(input).length === 0) {
    return <span className="text-slate-500 text-xs">No parameters</span>
  }
  
  return (
    <div className="space-y-1">
      {Object.entries(input).map(([key, value]) => (
        <div key={key} className="flex gap-2 text-xs">
          <span className="text-slate-500 font-mono">{key}:</span>
          <span className="text-slate-300 truncate">
            {typeof value === 'string' ? value : JSON.stringify(value)}
          </span>
        </div>
      ))}
    </div>
  )
}

function ToolOutput({ output }: { output?: Record<string, unknown> | null }) {
  if (!output) return null
  
  // Handle code generation output - show summary and collapsible code
  if (output.requires_execution && output.code) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-slate-300">{String(output.explanation || 'Code generated')}</p>
        <p className="text-xs text-cyan-400">📊 Output shown in chat →</p>
        <details className="text-xs">
          <summary className="text-slate-500 cursor-pointer hover:text-slate-400">
            View generated code
          </summary>
          <pre className="mt-2 p-2 bg-slate-900 rounded text-slate-400 overflow-x-auto max-h-40 overflow-y-auto">
            {String(output.code)}
          </pre>
        </details>
      </div>
    )
  }
  
  if (output.message) {
    return <p className="text-sm text-slate-300">{String(output.message)}</p>
  }
  
  if (output.result !== undefined) {
    return (
      <p className="text-sm">
        <span className="text-slate-400">Result: </span>
        <span className="text-emerald-400 font-semibold">{String(output.result)}</span>
      </p>
    )
  }
  
  if (output.documents && Array.isArray(output.documents)) {
    const docs = output.documents as Array<{ filename?: string }>
    return (
      <div className="text-sm">
        <p className="text-slate-400 mb-1">{docs.length} document{docs.length !== 1 ? 's' : ''}</p>
        {docs.slice(0, 2).map((doc, i) => (
          <div key={i} className="text-xs text-slate-500 truncate">
            📄 {doc.filename}
          </div>
        ))}
      </div>
    )
  }
  
  if (output.results && Array.isArray(output.results)) {
    const results = output.results as Array<{ title?: string }>
    return (
      <div className="text-sm">
        <p className="text-slate-400 mb-1">{results.length} result{results.length !== 1 ? 's' : ''}</p>
        {results.slice(0, 2).map((r, i) => (
          <div key={i} className="text-xs text-slate-500 truncate">
            🌐 {r.title}
          </div>
        ))}
      </div>
    )
  }
  
  return (
    <pre className="text-xs text-slate-500 overflow-hidden text-ellipsis max-h-16">
      {JSON.stringify(output, null, 2)}
    </pre>
  )
}

export function ToolTrace({ trace, tools, noToolsMessage, isLoading, onClear }: ToolTraceProps) {
  const toolIcons: Record<string, string> = {}
  for (const tool of tools) {
    toolIcons[tool.name] = tool.icon
  }

  return (
    <>
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800 shrink-0 flex items-center justify-between">
        <h2 className="font-semibold text-white flex items-center gap-2">
          <span className="text-lg">🔧</span>
          Tool Execution
          {trace.length > 0 && (
            <span className="text-xs text-slate-500 font-normal">({trace.length})</span>
          )}
        </h2>
        {trace.length > 0 && onClear && (
          <button
            onClick={onClear}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4">
        {trace.length === 0 && !isLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm">
            <span className="text-3xl mb-2 opacity-50">⚙️</span>
            <p>{noToolsMessage}</p>
          </div>
        ) : trace.length === 0 && isLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm">
            <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-2" />
            <p>Waiting for tool calls...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {trace.map((call, i) => {
              const isPending = !call.output && call.success !== false
              const isSuccess = call.success === true
              const isError = call.success === false
              
              return (
                <div 
                  key={i} 
                  className={`
                    rounded-xl border p-3 animate-fade-in
                    ${isPending ? 'border-slate-700 bg-slate-800/30' : ''}
                    ${isSuccess ? 'border-emerald-500/30 bg-emerald-500/5' : ''}
                    ${isError ? 'border-red-500/30 bg-red-500/5' : ''}
                  `}
                >
                  {/* Tool Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-base">{toolIcons[call.tool] || '🔧'}</span>
                    <span className="font-medium text-white text-sm">
                      {formatToolName(call.tool)}
                    </span>
                    <span className="ml-auto">
                      {isPending && (
                        <div className="w-3.5 h-3.5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                      )}
                      {isSuccess && <span className="text-emerald-400 text-sm">✓</span>}
                      {isError && <span className="text-red-400 text-sm">✗</span>}
                    </span>
                  </div>
                  
                  {/* Tool Input */}
                  <div className="mb-2 pl-6">
                    <ToolInput input={call.input} />
                  </div>
                  
                  {/* Tool Output */}
                  {call.output && (
                    <div className="pl-6 pt-2 border-t border-slate-700/50">
                      <ToolOutput output={call.output} />
                    </div>
                  )}
                  
                  {/* Running indicator */}
                  {isPending && (
                    <div className="pl-6 text-xs text-cyan-400">
                      Running...
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
