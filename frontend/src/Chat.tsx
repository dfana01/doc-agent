import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Message, JobProgress, AppConfig } from './types'
import { useUpload } from './api'
import { CodeOutput } from './CodeOutput'

interface PendingExecution {
  code: string
  explanation?: string
}

interface ChatProps {
  messages: Message[]
  onSend: (message: string) => void
  isLoading: boolean
  progress?: JobProgress | null
  config: AppConfig
  pendingExecution?: PendingExecution | null
  pyodideExecuting?: boolean
  pyodideLoading?: boolean
  pyodideProgress?: string
  pyodideConsole?: string
}

export function Chat({ 
  messages, onSend, isLoading, progress, config, 
  pendingExecution, pyodideExecuting, pyodideLoading, pyodideProgress, pyodideConsole 
}: ChatProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const upload = useUpload((s3Path) => {
    onSend(`Process document: ${s3Path}`)
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pendingExecution, pyodideProgress, pyodideConsole])

  useEffect(() => {
    if (upload.isSuccess) {
      const timer = setTimeout(() => upload.reset(), 2000)
      return () => clearTimeout(timer)
    }
  }, [upload.isSuccess])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) upload.mutate(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (input.trim() && !isLoading) {
        onSend(input.trim())
        setInput('')
      }
    }
  }

  return (
    <>
      <div className="px-5 py-4 border-b border-slate-800">
        <h2 className="font-semibold text-white flex items-center gap-2">
          <span className="text-lg">💬</span>
          Chat
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className="animate-fade-in">
            {msg.role === 'code_execution' ? (
              <div className="flex justify-start">
                <div className="max-w-[95%] w-full">
                  <CodeOutput
                    isExecuting={false}
                    outputs={msg.result.outputs}
                    result={msg.result.result}
                    stdout={msg.result.stdout}
                    error={msg.result.error}
                    code={msg.code}
                    explanation={msg.explanation}
                    chartData={msg.result.chartData}
                    tableData={msg.result.tableData}
                  />
                </div>
              </div>
            ) : (
              <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div 
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === 'user' 
                  ? 'bg-cyan-600 text-white' 
                  : 'bg-slate-800 text-slate-200'
              }`}
            >
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              </div>
            </div>
              </div>
            )}
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-slate-800 rounded-2xl px-4 py-3 max-w-[85%]">
              {progress ? (
                <div className="space-y-2">
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden w-40">
                    <div 
                      className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-300 ease-out"
                      style={{ width: `${progress.percent}%` }}
                    />
                  </div>
                  <p className="text-sm text-slate-400">{progress.message}</p>
                </div>
              ) : (
                <div className="flex gap-1.5">
                  {[0, 1, 2].map(i => (
                    <span 
                      key={i}
                      className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse-dot"
                      style={{ animationDelay: `${i * 0.16}s` }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Currently running execution */}
        {pendingExecution && (pyodideExecuting || pyodideLoading) && (
          <div className="flex justify-start animate-fade-in">
            <div className="max-w-[95%] w-full">
              <CodeOutput
                isExecuting={true}
                outputs={[]}
                code={pendingExecution.code}
                explanation={pendingExecution.explanation}
                progress={pyodideProgress}
                consoleOutput={pyodideConsole}
              />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {upload.error && (
        <div className="mx-5 mb-2 px-4 py-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg animate-fade-in">
          {upload.error.message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-800">
        <div className="flex items-end gap-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            className="hidden"
            accept={config.upload.accept}
          />
          
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || upload.isPending}
            className="w-10 h-10 flex items-center justify-center rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
            title="Upload document"
          >
            {upload.isPending ? (
              <div className="w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            ) : upload.isSuccess ? (
              <span className="text-emerald-400 text-sm">✓</span>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            )}
          </button>
          
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={config.messages.input_placeholder}
              disabled={isLoading}
              rows={1}
              className="w-full bg-slate-800 text-white placeholder-slate-500 rounded-xl px-4 py-2.5 resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50 transition-shadow text-sm"
              style={{ minHeight: '40px', maxHeight: '100px' }}
            />
          </div>
          
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()}
            className="w-10 h-10 flex items-center justify-center rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </form>
    </>
  )
}
