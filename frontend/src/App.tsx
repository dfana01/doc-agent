import { useState, useEffect, useRef, useCallback } from 'react'
import { Chat } from './Chat'
import { ToolTrace } from './ToolTrace'
import { References } from './References'
import { useConfig, useChat } from './api'
import { Message, ToolCall, CodeExecutionResult, ChatTextMessage } from './types'
import { usePyodide } from './usePyodide'

interface PendingExecution {
  code: string
  explanation?: string
}

export default function App() {
  const { data: config, error: configError, isLoading: configLoading } = useConfig()
  const [messages, setMessages] = useState<Message[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pendingExecution, setPendingExecution] = useState<PendingExecution | null>(null)
  const chat = useChat()
  const pyodide = usePyodide()
  
  const executedCallsRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (config && messages.length === 0) {
      setMessages([{ role: 'assistant', content: config.welcome_message }])
    }
  }, [config, messages.length])

  const executeCode = useCallback(async (code: string, data: Record<string, unknown>) => {
    return pyodide.execute(code, data)
  }, [pyodide.execute])

  useEffect(() => {
    const generateCodeCall = chat.toolTrace.find(
      (call: ToolCall) => call.tool === 'generate_code' && call.output?.requires_execution && call.output?.code
    )

    if (generateCodeCall && generateCodeCall.output) {
      const code = String(generateCodeCall.output.code)
      const callKey = code // Use the code itself as the unique identifier
      
      if (executedCallsRef.current.has(callKey)) {
        return
      }
      
      executedCallsRef.current.add(callKey)
      
      const data = (generateCodeCall.output.data as Record<string, unknown>) || {}
      const explanation = String(generateCodeCall.output.explanation || '')

      setPendingExecution({ code, explanation })

      executeCode(code, data).then(result => {
        setMessages(prev => [...prev, {
          role: 'code_execution' as const,
          code,
          explanation,
          result: result as CodeExecutionResult
        }])
        setPendingExecution(null)
      })
    }
  }, [chat.toolTrace, executeCode])

  useEffect(() => {
    if (chat.toolTrace.length === 0) {
      executedCallsRef.current.clear()
      setPendingExecution(null)
      pyodide.clearOutputs()
    }
  }, [chat.toolTrace.length, pyodide.clearOutputs])

  useEffect(() => {
    if (chat.isComplete && chat.response) {
      setMessages(prev => [...prev, { role: 'assistant', content: chat.response! }])
      chat.reset()
    }
  }, [chat.isComplete, chat.response, chat.reset])

  useEffect(() => {
    if (chat.error) {
      setError(chat.error)
      chat.reset()
    }
  }, [chat.error, chat.reset])

  const handleSend = (query: string) => {
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setError(null)
    const textMessages = messages.filter((m): m is ChatTextMessage => m.role !== 'code_execution')
    chat.submit(query, textMessages)
  }

  if (configLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          Loading...
        </div>
      </div>
    )
  }

  if (configError || !config) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-6 py-4 rounded-xl max-w-md text-center">
          <span className="text-2xl mb-2 block">⚠️</span>
          Failed to load: {configError?.message || 'Unknown error'}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 p-4 lg:p-6">
      <div className="max-w-[1400px] mx-auto h-[calc(100vh-48px)] flex flex-col gap-4 lg:gap-6">
        <header className="shrink-0">
          <h1 className="text-2xl font-bold text-white">{config.app.title}</h1>
          <p className="text-slate-400 mt-1">{config.app.subtitle}</p>
        </header>

        <div className="flex-1 flex flex-col lg:grid lg:grid-cols-[1fr_380px] gap-4 lg:gap-6 min-h-0">
          <div className="order-1 lg:order-2 flex flex-row lg:flex-col gap-4 lg:gap-6 min-h-0 lg:min-h-0">
            <div className="flex-1 bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden flex flex-col min-h-[150px] lg:min-h-[200px]">
              <References 
                toolTrace={chat.toolTrace} 
                onClear={chat.clearHistory}
              />
            </div>

            <div className="flex-1 bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden flex flex-col min-h-[150px] lg:min-h-[200px]">
              <ToolTrace 
                trace={chat.toolTrace} 
                tools={config.tools} 
                noToolsMessage={config.messages.no_tools}
                isLoading={chat.isLoading}
                onClear={chat.clearHistory}
              />
            </div>
          </div>

          <div className="order-2 lg:order-1 flex-1 bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden flex flex-col min-h-[300px] lg:min-h-[400px]">
            <Chat 
              messages={messages} 
              onSend={handleSend} 
              isLoading={chat.isLoading}
              progress={chat.progress}
              config={config}
              pendingExecution={pendingExecution}
              pyodideExecuting={pyodide.isExecuting}
              pyodideLoading={pyodide.isLoading}
              pyodideProgress={pyodide.progress}
              pyodideConsole={pyodide.consoleOutput}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 animate-slide-up z-50">
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-5 py-3 rounded-xl flex items-center gap-4 shadow-2xl backdrop-blur-sm">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 text-xl leading-none">
              &times;
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
