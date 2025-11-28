/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export type JobStatus = "pending" | "processing" | "completed" | "failed";
export type JobStatus1 = "pending" | "processing" | "completed" | "failed";

export interface AppConfig {
  app: AppInfo;
  welcome_message: string;
  tools: ToolInfo[];
  upload: UploadConfig;
  messages: MessagesConfig;
}
export interface AppInfo {
  title: string;
  subtitle: string;
}
export interface ToolInfo {
  name: string;
  description: string;
  icon: string;
}
export interface UploadConfig {
  accept: string;
  max_size_mb: number;
}
export interface MessagesConfig {
  input_placeholder: string;
  loading: string;
  no_tools: string;
  upload_error: string;
}
export interface CalculatorToolOutput {
  result: number;
  expression: string;
}
export interface CreateJobRequest {
  query: string;
  history?: {
    [k: string]: unknown;
  }[];
}
export interface CreateJobResponse {
  job_id: string;
  status: JobStatus;
}
export interface DocumentReference {
  document_id: string;
  filename: string;
  s3_path: string;
  score: number;
  text: string;
  chunk_index?: number | null;
}
export interface HealthResponse {
  status: string;
  services: {
    [k: string]: unknown;
  }[];
  timestamp: string;
}
export interface Job {
  id: string;
  query: string;
  status?: JobStatus1;
  progress?: JobProgress;
  response?: string | null;
  tool_trace?: ToolCall[];
  error?: string | null;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  retry_count?: number;
}
export interface JobProgress {
  step?: string;
  message?: string;
  percent?: number;
}
export interface ToolCall {
  tool: string;
  input?: {
    [k: string]: unknown;
  };
  output?: {
    [k: string]: unknown;
  } | null;
  success?: boolean;
}
export interface Message {
  role: string;
  content: string;
}
export interface SearchToolOutput {
  query: string;
  documents?: DocumentReference[];
  document_count?: number;
  low_confidence?: boolean;
  message?: string;
  document_id?: string | null;
}
export interface UploadUrlRequest {
  filename: string;
  content_type?: string | null;
}
export interface UploadUrlResponse {
  url: string;
  s3_path: string;
  key: string;
  content_type: string;
  expires_in: number;
  original_filename: string;
}
export interface ViewUrlRequest {
  s3_path: string;
}
export interface ViewUrlResponse {
  url: string;
  s3_path: string;
  filename: string;
  expires_in: number;
}
export interface WebReference {
  title: string;
  url: string;
  snippet: string;
}
export interface WebSearchToolOutput {
  results?: WebReference[];
}
