// Re-export all types from generated file
export type {
  JobStatus,
  JobProgress,
  ToolCall,
  Job,
  CreateJobRequest,
  CreateJobResponse,
  Message,
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
} from './types.generated'

// Additional types for frontend-only use
export interface AgentResponse {
  response: string
  tool_trace: import('./types.generated').ToolCall[]
  error: string | null
}
