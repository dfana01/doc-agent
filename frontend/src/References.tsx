import { useState } from 'react'
import { ToolCall, DocumentReference, WebReference } from './types'
import { useViewUrl } from './api'
import { DocumentPreview } from './DocumentPreview'

interface ReferencesProps {
  toolTrace: ToolCall[]
  onClear?: () => void
}

interface PreviewState {
  url: string
  filename: string
}

type Reference = 
  | { type: 'document'; data: DocumentReference }
  | { type: 'web'; data: WebReference }

export function References({ toolTrace, onClear }: ReferencesProps) {
  const [preview, setPreview] = useState<PreviewState | null>(null)
  const viewUrl = useViewUrl()

  const references: Reference[] = []
  const seenDocIds = new Set<string>()
  const seenUrls = new Set<string>()

  for (const call of toolTrace) {
    if (!call.success || !call.output) continue
    const output = call.output as Record<string, unknown>

    if (call.tool === 'search' && Array.isArray(output.documents)) {
      for (const doc of output.documents as DocumentReference[]) {
        if (!seenDocIds.has(doc.document_id)) {
          seenDocIds.add(doc.document_id)
          references.push({ type: 'document', data: doc })
        }
      }
    }

    if (call.tool === 'web_search' && Array.isArray(output.results)) {
      for (const ref of output.results as WebReference[]) {
        if (!seenUrls.has(ref.url)) {
          seenUrls.add(ref.url)
          references.push({ type: 'web', data: ref })
        }
      }
    }
  }

  const handleViewDocument = (s3Path: string, filename: string) => {
    viewUrl.mutate(s3Path, {
      onSuccess: (data) => setPreview({ url: data.url, filename }),
    })
  }

  return (
    <>
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800 shrink-0 flex items-center justify-between">
        <h2 className="font-semibold text-white flex items-center gap-2">
          <span className="text-lg">📚</span>
          References
          {references.length > 0 && (
            <span className="text-xs text-slate-500 font-normal">({references.length})</span>
          )}
        </h2>
        {references.length > 0 && onClear && (
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
        {references.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm">
            <span className="text-3xl mb-2 opacity-50">📄</span>
            <p>No references yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {references.map((ref, i) => {
              if (ref.type === 'document') {
                const doc = ref.data
                return (
                  <div 
                    key={`doc-${doc.document_id || i}`}
                    className="p-3 rounded-xl bg-slate-800/50 hover:bg-slate-800 transition-colors group"
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-lg shrink-0">📄</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 uppercase">
                            Doc
                          </span>
                          <span className="text-xs text-slate-500">
                            {(doc.score * 100).toFixed(0)}% match
                          </span>
                        </div>
                        <p className="text-sm text-white font-medium truncate" title={doc.filename}>
                          {doc.filename}
                        </p>
                      </div>
                      <button
                        onClick={() => handleViewDocument(doc.s3_path, doc.filename)}
                        disabled={viewUrl.isPending}
                        className="px-2.5 py-1 text-xs font-medium text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50"
                      >
                        {viewUrl.isPending ? '...' : 'View'}
                      </button>
                    </div>
                  </div>
                )
              } else {
                const web = ref.data
                return (
                  <a 
                    key={`web-${web.url || i}`}
                    href={web.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="block p-3 rounded-xl bg-slate-800/50 hover:bg-slate-800 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-lg shrink-0">🌐</span>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 uppercase">
                            Web
                          </span>
                        </div>
                        <p className="text-sm text-cyan-400 hover:text-cyan-300 font-medium truncate">
                          {web.title}
                        </p>
                        <p className="text-xs text-slate-500 line-clamp-2 mt-0.5">
                          {web.snippet}
                        </p>
                      </div>
                    </div>
                  </a>
                )
              }
            })}
          </div>
        )}
      </div>

      {preview && (
        <DocumentPreview
          url={preview.url}
          filename={preview.filename}
          onClose={() => setPreview(null)}
        />
      )}
    </>
  )
}
