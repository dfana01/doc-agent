// Re-export all types from generated file
export type {
  JobStatus,
  JobProgress,
  ToolCall,
  Job,
  CreateJobRequest,
  CreateJobResponse,
  Message as TextMessage,
  ToolInfo,
  AppInfo,
  UploadConfig,
  MessagesConfig,
  AppConfig,
  UploadUrlRequest,
  UploadUrlResponse,
  ViewUrlRequest,
  ViewUrlResponse,
  DocumentReference,
  WebReference,
  SearchToolOutput,
  WebSearchToolOutput,
  CalculatorToolOutput,
  CodeOutput,
  CodeGenerationResult,
  ExecutionResult,
} from './types.generated'

// Additional types for frontend-only use
export interface AgentResponse {
  response: string
  tool_trace: import('./types.generated').ToolCall[]
  error: string | null
}

// Code execution types - must match pyodide.worker.ts ExecutionOutput
export interface CodeExecutionOutput {
  type: 'image' | 'file' | 'chart'
  format: string
  data: string
  filename?: string
}

export interface CodeExecutionResult {
  success: boolean
  result?: unknown
  stdout: string
  error?: string
  outputs: CodeExecutionOutput[]
  execution_time_ms: number
  htmlOutput?: string
  chartData?: string    // Plotly JSON for interactive charts
  tableData?: unknown[] // Array data for TanStack Table
}

// Chat message types
export interface ChatTextMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatCodeMessage {
  role: 'code_execution'
  code: string
  explanation: string
  result: CodeExecutionResult
}

export type Message = ChatTextMessage | ChatCodeMessage
