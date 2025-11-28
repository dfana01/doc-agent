interface DocumentPreviewProps {
  url: string
  filename: string
  onClose: () => void
}

export function DocumentPreview({ url, filename, onClose }: DocumentPreviewProps) {
  const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(filename)
  const isPdf = /\.pdf$/i.test(filename)

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-fade-in"
      onClick={onClose}
    >
      <div 
        className="bg-slate-900 rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-700"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-xl">📄</span>
            <span className="font-medium text-white truncate">{filename}</span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <a 
              href={url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="px-4 py-2 text-sm font-medium text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-lg transition-colors flex items-center gap-2"
            >
              Open
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
            <button 
              onClick={onClose}
              className="w-10 h-10 flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors text-2xl"
            >
              &times;
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-auto bg-slate-950 min-h-0">
          {isImage && (
            <div className="p-4 flex items-center justify-center min-h-[400px]">
              <img 
                src={url} 
                alt={filename} 
                className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-lg"
              />
            </div>
          )}
          
          {isPdf && (
            <iframe 
              src={url} 
              title={filename}
              className="w-full h-[70vh] border-0"
            />
          )}
          
          {!isImage && !isPdf && (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <span className="text-5xl mb-4">📁</span>
              <p className="mb-4">Preview not available for this file type</p>
              <a 
                href={url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg transition-colors"
              >
                Download file
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
