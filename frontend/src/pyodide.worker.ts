/**
 * Pyodide Web Worker - Sandboxed Python Execution
 * Uses Comlink for simplified RPC-style communication
 * Refs: https://pyodide.org, https://github.com/GoogleChromeLabs/comlink
 */

import * as Comlink from 'comlink'
import { loadPyodide, PyodideInterface } from 'pyodide'

const PYODIDE_CDN = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/'
const PRELOAD_PACKAGES = ['numpy', 'pandas', 'matplotlib']

let pyodide: PyodideInterface | null = null

export interface ExecutionOutput {
  type: 'image' | 'file' | 'chart'
  format: string
  data: string
  filename?: string
}

export interface ExecutionResult {
  success: boolean
  result?: unknown
  stdout: string
  error?: string
  outputs: ExecutionOutput[]
  execution_time_ms: number
  chartData?: string  // Plotly JSON for interactive charts
  tableData?: unknown[]  // Array data for TanStack Table
}

// Progress callback type for streaming updates
type ProgressCallback = (message: string) => void
type StdoutCallback = (content: string) => void

// Store callbacks for progress updates
let progressCallback: ProgressCallback | null = null
let stdoutCallback: StdoutCallback | null = null

const pyodideWorker = {
  // Set progress callback
  onProgress(callback: ProgressCallback) {
    progressCallback = callback
  },

  // Set stdout callback
  onStdout(callback: StdoutCallback) {
    stdoutCallback = callback
  },

  // Initialize Pyodide
  async init(): Promise<boolean> {
    if (pyodide) return true
    
    progressCallback?.('Loading Python environment...')
    pyodide = await loadPyodide({ indexURL: PYODIDE_CDN })
    
    progressCallback?.('Loading core packages...')
    await pyodide.loadPackage(PRELOAD_PACKAGES)
    
    // Configure matplotlib for non-interactive use
    pyodide.runPython(`
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()
    `)
    
    progressCallback?.('Python environment ready')
    return true
  },

  // Execute Python code
  async execute(code: string, data: Record<string, unknown>): Promise<ExecutionResult> {
    const startTime = Date.now()
    const outputs: ExecutionOutput[] = []
    
    try {
      progressCallback?.('Initializing...')
      if (!pyodide) await this.init()
      const py = pyodide!
      
      // Load additional packages if needed
      const packages = detectPackages(code)
      for (const pkg of packages.direct) {
        if (!PRELOAD_PACKAGES.includes(pkg)) {
          progressCallback?.(`Loading ${pkg}...`)
          await py.loadPackage(pkg)
        }
      }
      
      // Load micropip packages (like plotly)
      if (packages.micropip.length > 0) {
        progressCallback?.('Loading micropip...')
        await py.loadPackage('micropip')
        for (const pkg of packages.micropip) {
          progressCallback?.(`Installing ${pkg}...`)
          await py.runPythonAsync(`import micropip; await micropip.install('${pkg}')`)
        }
      }
      
      progressCallback?.('Preparing execution...')
      py.runPython(`
output_image = None
output_file = None
output_filename = None
output_chart = None  # Plotly JSON
output_table = None  # Table data
result = None

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()
plt.close('all')

import sys
from io import StringIO
_stdout_capture = StringIO()
_original_stdout = sys.stdout
sys.stdout = _stdout_capture
      `)
      
      py.globals.set('data', py.toPy(data))
      
      progressCallback?.('Running code...')
      await py.runPythonAsync(code)
      
      // Capture stdout
      const stdout = py.runPython('_stdout_capture.getvalue()') as string
      py.runPython('sys.stdout = _original_stdout')
      if (stdout) stdoutCallback?.(stdout)
      
      progressCallback?.('Collecting results...')
      
      const pyNone = py.globals.get('None')
      const resultValue = py.globals.get('result')
      const outputImage = py.globals.get('output_image')
      const outputFile = py.globals.get('output_file')
      const outputFilename = py.globals.get('output_filename')
      const outputChart = py.globals.get('output_chart')
      const outputTable = py.globals.get('output_table')
      
      let result: unknown = undefined
      let chartData: string | undefined = undefined
      let tableData: unknown[] | undefined = undefined
      
      // Helper to convert Pyodide objects to plain JS (serializable)
      const toSerializable = (val: unknown): unknown => {
        if (val === null || val === undefined) return val
        if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') return val
        // Convert via Python JSON for guaranteed serialization
        try {
          py.globals.set('_temp_val', val)
          const jsonStr = py.runPython(`import json; json.dumps(_temp_val)`) as string
          return JSON.parse(jsonStr)
        } catch {
          return String(val)
        }
      }
      
      // Handle result (might be DataFrame)
      if (resultValue && resultValue !== pyNone) {
        try {
          const isDataFrame = py.runPython(`
import pandas as pd
isinstance(result, pd.DataFrame) if result is not None else False
          `)
          if (isDataFrame) {
            // Convert DataFrame to JSON string then parse (ensures serializable)
            const jsonStr = py.runPython(`import json; json.dumps(result.to_dict('records'))`) as string
            tableData = JSON.parse(jsonStr)
            result = py.runPython(`f"DataFrame: {result.shape[0]} rows × {result.shape[1]} columns"`) as string
          } else {
            result = toSerializable(resultValue)
          }
        } catch {
          result = String(resultValue)
        }
      }
      
      // Handle Plotly chart JSON
      if (outputChart && outputChart !== pyNone) {
        chartData = String(outputChart)
      }
      
      // Handle table data
      if (outputTable && outputTable !== pyNone) {
        try {
          const jsonStr = py.runPython(`import json; json.dumps(output_table)`) as string
          tableData = JSON.parse(jsonStr)
        } catch {
          // Ignore if can't convert
        }
      }
      
      // Handle matplotlib image
      if (outputImage && outputImage !== pyNone) {
        const imgData = String(outputImage)
        if (imgData && imgData !== 'None') {
          outputs.push({ type: 'image', format: 'png', data: imgData })
        }
      }
      
      // Handle file output
      if (outputFile && outputFile !== pyNone) {
        const fileData = String(outputFile)
        if (fileData && fileData !== 'None') {
          const filename = outputFilename ? String(outputFilename) : 'output.bin'
          outputs.push({ type: 'file', format: filename.split('.').pop() || 'bin', data: fileData, filename })
        }
      }
      
      progressCallback?.('Complete!')
      return {
        success: true,
        result,
        stdout: stdout || '',
        outputs,
        execution_time_ms: Date.now() - startTime,
        chartData,
        tableData
      }
      
    } catch (error) {
      let stdout = ''
      try {
        if (pyodide) {
          stdout = pyodide.runPython(`try:\n    _stdout_capture.getvalue()\nexcept:\n    ''`) as string
          pyodide.runPython(`try:\n    sys.stdout = _original_stdout\nexcept:\n    pass`)
        }
      } catch { /* ignore */ }
      
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
        stdout,
        outputs: [],
        execution_time_ms: Date.now() - startTime
      }
    }
  }
}

// Packages that can be loaded directly via loadPackage
const DIRECT_PACKAGES = ['numpy', 'pandas', 'matplotlib', 'scipy', 'statsmodels', 'openpyxl']
// Packages that need micropip (pure Python)
const MICROPIP_PACKAGES = ['plotly']

function detectPackages(code: string): { direct: string[], micropip: string[] } {
  const direct: string[] = []
  const micropip: string[] = []
  const regex = /(?:import|from)\s+(\w+)/g
  let match
  while ((match = regex.exec(code)) !== null) {
    const pkg = match[1]
    if (DIRECT_PACKAGES.includes(pkg) && !direct.includes(pkg)) {
      direct.push(pkg)
    }
    if (MICROPIP_PACKAGES.includes(pkg) && !micropip.includes(pkg)) {
      micropip.push(pkg)
    }
  }
  return { direct, micropip }
}

// Expose worker API via Comlink
Comlink.expose(pyodideWorker)

export type PyodideWorkerAPI = typeof pyodideWorker
