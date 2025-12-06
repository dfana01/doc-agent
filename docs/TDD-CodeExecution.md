# Python Code Execution Technical Design

Sandboxed Python code generation and execution for dynamic analytics.

## Overview

The agent generates Python code using Claude on the backend. Code executes in a Pyodide (WebAssembly) sandbox on the frontend. Results are persisted to DynamoDB with binary outputs in S3.

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Sandbox | Pyodide (WASM) | Hardware-level isolation, no host access, supports data science libraries |
| Execution | Frontend browser | Zero server risk, infinite scalability, no Lambda timeouts |
| Code Generation | Claude | Consistent with agent, excellent at code, supports XML parsing |
| Worker Comms | Comlink | Simplifies postMessage to RPC-style async calls |
| Charts | react-plotly.js | Interactive (zoom, pan, hover), Python outputs JSON |
| Tables | @tanstack/react-table | Sort, filter, paginate - better than static HTML |
| Libraries | numpy, pandas, matplotlib, plotly, scipy, statsmodels, openpyxl | Pyodide-compatible |
| Persistence | DynamoDB + S3 | Metadata in Dynamo, binary outputs in S3 |

## Architecture

| Layer | File | Purpose |
|-------|------|---------|
| Backend Tool | `tools.py` | `generate_code` - LLM generates Python |
| Backend LLM | `llm.py` | Claude code generation with prompt security |
| Backend API | `app.py` | `POST /api/jobs/{id}/executions` - persist results |
| Frontend Hook | `usePyodide.ts` | Pyodide lifecycle via Comlink |
| Frontend Worker | `pyodide.worker.ts` | Pyodide execution with Comlink.expose() |
| Frontend UI | `CodeOutput.tsx` | Plotly charts, TanStack tables |

## Execution Flow

1. **User Request** - Query like "Create a bar chart of revenue"
2. **Data Retrieval** - Agent calls `search()` to find relevant data
3. **Code Generation** - Agent calls `generate_code()`, Claude generates Python in `<code>` tags
4. **Execution Trigger** - Frontend detects `requires_execution: true` flag
5. **Sandbox Execution** - `usePyodide.execute()` runs code via Comlink → Web Worker → Pyodide
6. **Rendering** - `CodeOutput` displays Plotly charts, TanStack tables, downloads
7. **Persistence** - Frontend calls API to save results (binaries → S3, metadata → DynamoDB)

## Security

### Backend
- **Input sanitization** - Remove injection patterns (`<system>`, `IGNORE PREVIOUS`, etc.)
- **XML tag parsing** - Extract code from `<code></code>` tags
- **AST validation** - Block dangerous imports (os, sys, subprocess) and builtins (exec, eval, open)
- **System prompt boundaries** - Clear rules that override any user instructions

### Frontend
- **Pyodide WASM isolation** - No filesystem, network, or process access
- **Execution timeout** - 30 seconds
- **Memory limit** - 256MB WASM heap
- **Package allowlist** - Only approved libraries

## Dependencies

**Frontend:** `comlink`, `plotly.js`, `react-plotly.js`, `@tanstack/react-table`, `pyodide`

**Backend:** `anthropic` (existing)

## File Changes

| File | Action |
|------|--------|
| frontend/package.json | Add comlink, plotly, tanstack |
| frontend/src/pyodide.worker.ts | Rewrite with Comlink.expose() |
| frontend/src/usePyodide.ts | Rewrite with Comlink.wrap() |
| frontend/src/CodeOutput.tsx | Add Plotly + TanStack Table |
| backend/models.py | Add CodeExecutionRecord |
| backend/jobs.py | Add save/get executions |
| backend/app.py | Add /executions endpoint |
| backend/llm.py | Claude + sanitization + XML parsing |
| backend/config.py | Add code_generation_model |
| backend/s3.py | Add upload_bytes |

## Risks

| Risk | Mitigation |
|------|------------|
| Pyodide load (~11MB) | Lazy loading, browser caching |
| Plotly bundle (~3MB) | Dynamic import |
| Prompt injection | Input sanitization, XML tags, system prompt |
| Code quality | Clear prompts, error retry, AST validation |
