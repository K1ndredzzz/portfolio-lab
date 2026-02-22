/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly PROD: boolean;
  readonly DEV: boolean;
  readonly MODE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'react-plotly.js' {
  import { Component } from 'react';
  import { PlotParams } from 'plotly.js';

  export interface PlotProps extends Partial<PlotParams> {
    data: Partial<PlotParams['data']>;
    layout?: Partial<PlotParams['layout']>;
    config?: Partial<PlotParams['config']>;
    frames?: Partial<PlotParams['frames']>;
    onInitialized?: (figure: Readonly<PlotParams>, graphDiv: Readonly<HTMLElement>) => void;
    onUpdate?: (figure: Readonly<PlotParams>, graphDiv: Readonly<HTMLElement>) => void;
    onPurge?: (figure: Readonly<PlotParams>, graphDiv: Readonly<HTMLElement>) => void;
    onError?: (err: Readonly<Error>) => void;
    onAfterExport?: () => void;
    onAfterPlot?: () => void;
    onAnimated?: () => void;
    onAnimatingFrame?: (event: Readonly<PlotParams>) => void;
    onAnimationInterrupted?: () => void;
    onAutoSize?: () => void;
    onBeforeExport?: () => void;
    onButtonClicked?: (event: Readonly<PlotParams>) => void;
    onClick?: (event: Readonly<PlotParams>) => void;
    onClickAnnotation?: (event: Readonly<PlotParams>) => void;
    onDeselect?: () => void;
    onDoubleClick?: () => void;
    onFramework?: () => void;
    onHover?: (event: Readonly<PlotParams>) => void;
    onLegendClick?: (event: Readonly<PlotParams>) => boolean;
    onLegendDoubleClick?: (event: Readonly<PlotParams>) => boolean;
    onRelayout?: (event: Readonly<PlotParams>) => void;
    onRestyle?: (event: Readonly<PlotParams>) => void;
    onRedraw?: () => void;
    onSelected?: (event: Readonly<PlotParams>) => void;
    onSelecting?: (event: Readonly<PlotParams>) => void;
    onSliderChange?: (event: Readonly<PlotParams>) => void;
    onSliderEnd?: (event: Readonly<PlotParams>) => void;
    onSliderStart?: (event: Readonly<PlotParams>) => void;
    onSunburstClick?: (event: Readonly<PlotParams>) => void;
    onTransitioning?: () => void;
    onTransitionInterrupted?: () => void;
    onUnhover?: (event: Readonly<PlotParams>) => void;
    onWebGlContextLost?: () => void;
    divId?: string;
    className?: string;
    style?: React.CSSProperties;
    useResizeHandler?: boolean;
    debug?: boolean;
    onClickAnnotation?: (event: Readonly<PlotParams>) => void;
  }

  export default class Plot extends Component<PlotProps> {}
}
