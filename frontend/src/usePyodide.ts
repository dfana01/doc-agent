import { useState, useEffect, useRef, useCallback } from 'react'
import * as Comlink from 'comlink'
import type { PyodideWorkerAPI, ExecutionResult, ExecutionOutput } from './pyodide.worker'

export type { ExecutionResult, ExecutionOutput }

export function usePyodide() {
  const [isReady, setIsReady] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [outputs, setOutputs] = useState<ExecutionOutput[]>([])
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState('')
  const [consoleOutput, setConsoleOutput] = useState('')
  
  const workerRef = useRef<Worker | null>(null)
  const apiRef = useRef<Comlink.Remote<PyodideWorkerAPI> | null>(null)

  useEffect(() => {
    const worker = new Worker(
      new URL('./pyodide.worker.ts', import.meta.url),
      { type: 'module' }
    )
    workerRef.current = worker
    apiRef.current = Comlink.wrap<PyodideWorkerAPI>(worker)
    
    apiRef.current.onProgress(Comlink.proxy((msg: string) => setProgress(msg)))
    apiRef.current.onStdout(Comlink.proxy((content: string) => setConsoleOutput(prev => prev + content)))
    
    return () => {
      worker.terminate()
      workerRef.current = null
      apiRef.current = null
    }
  }, [])

  const initialize = useCallback(async () => {
    if (isReady || isLoading || !apiRef.current) return
    setIsLoading(true)
    setError(null)
    
    try {
      await apiRef.current.init()
      setIsReady(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize')
    } finally {
      setIsLoading(false)
      setProgress('')
    }
  }, [isReady, isLoading])

  const execute = useCallback(async (
    code: string,
    data: Record<string, unknown>
  ): Promise<ExecutionResult> => {
    if (!apiRef.current) {
      return { success: false, error: 'Worker not initialized', stdout: '', outputs: [], execution_time_ms: 0 }
    }
    
    setConsoleOutput('')
    setProgress('')
    setIsExecuting(true)
    setError(null)
    
    try {
      // Auto-initialize if needed
      if (!isReady) {
        await initialize()
      }
      
      const result = await apiRef.current.execute(code, data)
      setOutputs(result.outputs)
      
      if (!result.success && result.error) {
        setError(result.error)
      }
      
      return result
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Execution failed'
      setError(errorMsg)
      return { success: false, error: errorMsg, stdout: '', outputs: [], execution_time_ms: 0 }
    } finally {
      setIsExecuting(false)
      setProgress('')
    }
  }, [isReady, initialize])

  const clearOutputs = useCallback(() => {
    setOutputs([])
    setError(null)
    setConsoleOutput('')
    setProgress('')
  }, [])

  return {
    isReady,
    isLoading,
    isExecuting,
    outputs,
    error,
    progress,
    consoleOutput,
    initialize,
    execute,
    clearOutputs
  }
}
