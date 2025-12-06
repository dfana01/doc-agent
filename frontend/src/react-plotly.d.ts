declare module 'react-plotly.js' {
  import { Component } from 'react'
  import { PlotParams } from 'plotly.js'
  
  interface PlotProps {
    data: Plotly.Data[]
    layout?: Partial<Plotly.Layout>
    config?: Partial<Plotly.Config>
    style?: React.CSSProperties
    className?: string
    onInitialized?: (figure: Readonly<PlotParams>, graphDiv: HTMLElement) => void
    onUpdate?: (figure: Readonly<PlotParams>, graphDiv: HTMLElement) => void
    onPurge?: (figure: Readonly<PlotParams>, graphDiv: HTMLElement) => void
    onError?: (error: Error) => void
    useResizeHandler?: boolean
    frames?: Plotly.Frame[]
    revision?: number
  }
  
  export default class Plot extends Component<PlotProps> {}
}

declare module 'plotly.js' {
  export interface Data {
    type?: string
    x?: unknown[]
    y?: unknown[]
    z?: unknown[]
    name?: string
    mode?: string
    marker?: Record<string, unknown>
    line?: Record<string, unknown>
    text?: string | string[]
    hoverinfo?: string
    [key: string]: unknown
  }
  
  export interface Layout {
    title?: string | { text: string }
    xaxis?: Record<string, unknown>
    yaxis?: Record<string, unknown>
    width?: number
    height?: number
    autosize?: boolean
    margin?: { l?: number; r?: number; t?: number; b?: number }
    showlegend?: boolean
    [key: string]: unknown
  }
  
  export interface Config {
    responsive?: boolean
    displayModeBar?: boolean
    displaylogo?: boolean
    [key: string]: unknown
  }
  
  export interface Frame {
    name?: string
    data?: Data[]
    layout?: Partial<Layout>
  }
  
  export interface PlotParams {
    data: Data[]
    layout: Layout
    frames?: Frame[]
  }
}

